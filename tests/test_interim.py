import os
import struct
import threading
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from soundflow.core.segmenter import EnergySegmenter, SegmenterConfig
from soundflow.transcription import (
    DemoTranscriber,
    DictationPipeline,
    _AudioCommand,
    _InferenceCommand,
)

try:
    from PySide6.QtWidgets import QApplication

    from soundflow.ui.pages import DictationPage

    HAS_QT = True
except ImportError:
    HAS_QT = False


def frame(value: int, samples: int = 480) -> bytes:
    return struct.pack(f"<{samples}h", *([value] * samples))


def speech_config() -> SegmenterConfig:
    return SegmenterConfig(
        threshold=0.01,
        silence_ms=900,
        min_speech_ms=60,
        pre_roll_ms=30,
    )


class SnapshotTests(unittest.TestCase):
    def test_snapshot_returns_growing_buffer_without_ending_phrase(self):
        segmenter = EnergySegmenter(speech_config())
        self.assertEqual(segmenter.snapshot(), b"")
        for _ in range(30):
            completed = segmenter.feed(frame(6000))
            self.assertEqual(completed, [])
        snap = segmenter.snapshot()
        self.assertGreaterEqual(len(snap), 30 * 960)
        for _ in range(20):
            self.assertEqual(segmenter.feed(frame(0)), [])
        grown = segmenter.snapshot()
        self.assertTrue(grown.startswith(snap))
        self.assertGreater(len(grown), len(snap))
        completed = []
        for _ in range(20):
            completed.extend(segmenter.feed(frame(0)))
        self.assertEqual(len(completed), 1)
        self.assertEqual(segmenter.snapshot(), b"")

    def test_snapshot_empty_before_min_speech(self):
        segmenter = EnergySegmenter(speech_config())
        segmenter.feed(frame(6000))
        self.assertEqual(segmenter.snapshot(), b"")


class InterimPipelineTests(unittest.TestCase):
    def test_live_interim_arrives_before_final(self):
        interims = []
        texts = []
        errors = []
        finished = threading.Event()
        pipeline = DictationPipeline(
            DemoTranscriber(),
            speech_config(),
            texts.append,
            finished.set,
            errors.append,
            lambda level: None,
            interims.append,
        )
        try:
            pipeline._session = 1
            pipeline._put_audio(_AudioCommand("start", 1))
            for _ in range(60):
                pipeline._receive_frame(frame(6000))
            for _ in range(40):
                pipeline._receive_frame(frame(0))
            pipeline._put_audio(_AudioCommand("stop", 1))
            self.assertTrue(finished.wait(5), "pipeline did not drain")
            self.assertEqual(errors, [])
            self.assertTrue(interims, "no interim text emitted while speaking")
            self.assertEqual(len(texts), 1)
            self.assertIn("Demo mode", texts[0])
        finally:
            pipeline.close()

    def test_stale_interim_dropped_after_new_session(self):
        interims = []
        pipeline = DictationPipeline(
            DemoTranscriber(),
            speech_config(),
            lambda text: None,
            lambda: None,
            lambda message: None,
            lambda level: None,
            interims.append,
        )
        try:
            pipeline._session = 2
            pipeline._inference_queue.put(
                _InferenceCommand("interim", 1, frame(6000, 4800))
            )
            for _ in range(50):
                if pipeline._inference_queue.empty():
                    break
                threading.Event().wait(0.05)
            threading.Event().wait(0.3)
            self.assertEqual(interims, [])
        finally:
            pipeline.close()

    def test_interim_uses_fast_path_when_available(self):
        calls = []
        interims = []

        class QuickTranscriber:
            def transcribe_pcm(self, pcm16: bytes, sample_rate: int) -> str:
                calls.append("full")
                return "full"

            def transcribe_interim(self, pcm16: bytes, sample_rate: int) -> str:
                calls.append("quick")
                return "quick"

        pipeline = DictationPipeline(
            QuickTranscriber(),
            speech_config(),
            lambda text: None,
            lambda: None,
            lambda message: None,
            lambda level: None,
            interims.append,
        )
        try:
            pipeline._session = 4
            pipeline._inference_queue.put(
                _InferenceCommand("interim", 4, frame(6000, 4800))
            )
            for _ in range(50):
                if interims:
                    break
                threading.Event().wait(0.05)
            self.assertEqual(interims, ["quick"])
            self.assertEqual(calls, ["quick"])
        finally:
            pipeline.close()


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class InterimLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_interim_label_shows_live_text_and_clears(self):
        page = DictationPage()
        self.assertEqual(page._interim.text(), "")
        page.set_interim("hello  world")
        self.assertEqual(page._interim.text(), "… hello world")
        page.set_interim("hello  world")
        self.assertEqual(page._interim.text(), "… hello world")
        page.clear_interim()
        self.assertEqual(page._interim.text(), "")
        page.set_interim("   ")
        self.assertEqual(page._interim.text(), "")


if __name__ == "__main__":
    unittest.main()
