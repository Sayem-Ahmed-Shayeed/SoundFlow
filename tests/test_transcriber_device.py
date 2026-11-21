import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from soundflow import transcription
from soundflow.transcription import FasterWhisperTranscriber, ModelUnavailable


class _Recorder:
    """Stands in for faster_whisper.WhisperModel and records each attempt."""

    def __init__(self, failing_devices=()):
        self.failing_devices = set(failing_devices)
        self.attempts: list[str] = []

    def module(self) -> types.ModuleType:
        recorder = self
        module = types.ModuleType("faster_whisper")

        class WhisperModel:
            def __init__(self, path, *, device, compute_type, local_files_only):
                recorder.attempts.append(device)
                if device in recorder.failing_devices:
                    raise RuntimeError(f"cannot use {device}")
                self.device = device

        module.WhisperModel = WhisperModel
        return module


class DeviceResolutionTests(unittest.TestCase):
    def setUp(self):
        self._modules = patch.dict(sys.modules)
        self._modules.start()
        transcription._MODEL_CACHE.clear()
        transcription._RESOLVED_DEVICES.clear()
        self._directory = tempfile.TemporaryDirectory()
        self.model_path = Path(self._directory.name)
        self._verify = patch.object(FasterWhisperTranscriber, "_verify_manifest")
        self._verify.start()

    def tearDown(self):
        self._verify.stop()
        transcription._MODEL_CACHE.clear()
        transcription._RESOLVED_DEVICES.clear()
        self._directory.cleanup()
        self._modules.stop()

    def _load(self, device, *, gpu_count, failing=()):
        recorder = _Recorder(failing)
        sys.modules["faster_whisper"] = recorder.module()
        with patch.object(transcription, "_cuda_device_count", return_value=gpu_count):
            transcriber = FasterWhisperTranscriber(self.model_path, device=device)
            transcriber._load()
        return transcriber, recorder

    def test_auto_uses_the_gpu_when_one_is_present_and_loads(self):
        transcriber, recorder = self._load("auto", gpu_count=1)
        self.assertEqual(recorder.attempts, ["cuda"])
        self.assertEqual(transcriber.active_device, "cuda")
        self.assertEqual(transcriber.device, "auto")

    def test_auto_falls_back_to_the_processor_when_the_gpu_fails(self):
        transcriber, recorder = self._load("auto", gpu_count=1, failing=("cuda",))
        self.assertEqual(recorder.attempts, ["cuda", "cpu"])
        self.assertEqual(transcriber.active_device, "cpu")

    def test_auto_without_a_gpu_loads_on_the_processor_only(self):
        transcriber, recorder = self._load("auto", gpu_count=0)
        self.assertEqual(recorder.attempts, ["cpu"])
        self.assertEqual(transcriber.active_device, "cpu")

    def test_explicit_cuda_does_not_silently_fall_back(self):
        recorder = _Recorder(("cuda",))
        sys.modules["faster_whisper"] = recorder.module()
        with patch.object(transcription, "_cuda_device_count", return_value=1):
            transcriber = FasterWhisperTranscriber(self.model_path, device="cuda")
            with self.assertRaises(ModelUnavailable):
                transcriber._load()
        self.assertEqual(recorder.attempts, ["cuda"])

    def test_explicit_cpu_never_touches_the_gpu(self):
        transcriber, recorder = self._load("cpu", gpu_count=1)
        self.assertEqual(recorder.attempts, ["cpu"])
        self.assertEqual(transcriber.active_device, "cpu")

    def test_cached_model_reports_the_device_it_was_loaded_on(self):
        self._load("auto", gpu_count=1, failing=("cuda",))
        recorder = _Recorder()
        sys.modules["faster_whisper"] = recorder.module()
        with patch.object(transcription, "_cuda_device_count", return_value=1):
            again = FasterWhisperTranscriber(self.model_path, device="auto")
            again._load()
        self.assertEqual(recorder.attempts, [])
        self.assertEqual(again.active_device, "cpu")


if __name__ == "__main__":
    unittest.main()
