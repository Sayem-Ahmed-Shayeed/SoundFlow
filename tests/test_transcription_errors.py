import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from soundflow.transcription import FasterWhisperTranscriber, ModelUnavailable


def _install_fake_whisper(failure: Exception) -> None:
    module = types.ModuleType("faster_whisper")

    class FakeModel:
        def __init__(self, *args, **kwargs) -> None:
            raise failure

    module.WhisperModel = FakeModel
    sys.modules["faster_whisper"] = module


class GpuErrorTests(unittest.TestCase):
    def test_missing_cublas_maps_to_actionable_message(self):
        with tempfile.TemporaryDirectory() as directory:
            transcriber = FasterWhisperTranscriber(
                Path(directory), language="bn", device="cuda"
            )
            _install_fake_whisper(
                RuntimeError("Library libcublas.so.12 is not found")
            )
            try:
                with self.assertRaises(ModelUnavailable) as raised:
                    transcriber.transcribe_pcm(bytes(3200), 16_000)
            finally:
                sys.modules.pop("faster_whisper", None)
            self.assertIn("CPU", str(raised.exception))

    def test_oom_maps_to_actionable_message(self):
        with tempfile.TemporaryDirectory() as directory:
            transcriber = FasterWhisperTranscriber(
                Path(directory), language="bn", device="cuda"
            )
            _install_fake_whisper(
                RuntimeError("CUDA failed with error out of memory")
            )
            try:
                with self.assertRaises(ModelUnavailable) as raised:
                    transcriber.transcribe_pcm(bytes(3200), 16_000)
            finally:
                sys.modules.pop("faster_whisper", None)
            self.assertIn("out of memory", str(raised.exception).lower())

    def test_cpu_errors_pass_through_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            transcriber = FasterWhisperTranscriber(
                Path(directory), language="bn", device="cpu"
            )
            _install_fake_whisper(RuntimeError("some odd failure"))
            try:
                with self.assertRaises(ModelUnavailable) as raised:
                    transcriber.transcribe_pcm(bytes(3200), 16_000)
            finally:
                sys.modules.pop("faster_whisper", None)
            self.assertIn("some odd failure", str(raised.exception))
            self.assertNotIn("GPU", str(raised.exception))

    def test_language_auto_still_maps_to_none(self):
        transcriber = FasterWhisperTranscriber(Path("/tmp"), language="auto")
        self.assertIsNone(transcriber.language)
        with patch.object(
            FasterWhisperTranscriber, "_load", side_effect=ModelUnavailable("x")
        ):
            with self.assertRaises(ModelUnavailable):
                transcriber.transcribe_pcm(bytes(3200), 16_000)


if __name__ == "__main__":
    unittest.main()
