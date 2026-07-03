import struct
import unittest

from soundflow.core.segmenter import EnergySegmenter, SegmenterConfig, pcm16_rms


def frame(value: int, samples: int = 480) -> bytes:
    return struct.pack(f"<{samples}h", *([value] * samples))


class SegmenterTests(unittest.TestCase):
    def test_rms(self):
        self.assertEqual(pcm16_rms(frame(0)), 0)
        self.assertGreater(pcm16_rms(frame(10_000)), 0.3)

    def test_phrase_ends_after_silence(self):
        segmenter = EnergySegmenter(
            SegmenterConfig(
                threshold=0.01,
                silence_ms=90,
                min_speech_ms=60,
                pre_roll_ms=30,
            )
        )
        completed = []
        for _ in range(4):
            completed.extend(segmenter.feed(frame(5000)))
        for _ in range(3):
            completed.extend(segmenter.feed(frame(0)))
        self.assertEqual(len(completed), 1)
        self.assertGreater(len(completed[0]), 0)

    def test_short_noise_is_discarded(self):
        segmenter = EnergySegmenter(
            SegmenterConfig(threshold=0.01, silence_ms=60, min_speech_ms=100)
        )
        completed = segmenter.feed(frame(5000))
        completed += segmenter.feed(frame(0))
        completed += segmenter.feed(frame(0))
        self.assertEqual(completed, [])


if __name__ == "__main__":
    unittest.main()

