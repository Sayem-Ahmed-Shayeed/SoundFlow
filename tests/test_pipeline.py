import struct
import threading
import unittest

from soundflow.core.segmenter import SegmenterConfig
from soundflow.transcription import DemoTranscriber, DictationPipeline, _AudioCommand


def frame(value: int, samples: int = 480) -> bytes:
    return struct.pack(f"<{samples}h", *([value] * samples))


class PipelineTests(unittest.TestCase):
    def test_phrase_crosses_both_worker_queues(self):
        texts = []
        errors = []
        finished = threading.Event()
        pipeline = DictationPipeline(
            DemoTranscriber(),
            SegmenterConfig(
                threshold=0.01,
                silence_ms=90,
                min_speech_ms=60,
                pre_roll_ms=30,
            ),
            texts.append,
            finished.set,
            errors.append,
            lambda level: None,
        )
        try:
            pipeline._session = 1
            pipeline._put_audio(_AudioCommand("start", 1))
            for _ in range(4):
                pipeline._receive_frame(frame(6000))
            for _ in range(3):
                pipeline._receive_frame(frame(0))
            pipeline._put_audio(_AudioCommand("stop", 1))
            self.assertTrue(finished.wait(2), "pipeline did not drain")
            self.assertEqual(errors, [])
            self.assertEqual(len(texts), 1)
            self.assertIn("Demo mode", texts[0])
        finally:
            pipeline.close()


if __name__ == "__main__":
    unittest.main()

