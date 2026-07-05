import tempfile
import unittest
from pathlib import Path

from soundflow.core.settings import Settings
from soundflow.preferences.system_check import run_system_check


class SystemCheckTests(unittest.TestCase):
    def test_reports_model_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                model_path=directory,
                hotkey_authorized=True,
                remote_desktop_restore_token="token",
            )
            result = run_system_check(settings, list_inputs=lambda: [(0, "Mic")])
            self.assertTrue(result.model_ready)
            self.assertTrue(result.microphone_ready)
            self.assertTrue(result.hotkey_ready)
            self.assertTrue(result.paste_ready)

    def test_cuda_request_falls_back_when_unavailable(self):
        settings = Settings(inference_device="cuda")
        result = run_system_check(
            settings,
            list_inputs=lambda: [],
            cuda_devices=lambda: 0,
        )
        self.assertEqual(result.effective_device, "cpu")
        self.assertFalse(result.microphone_ready)


if __name__ == "__main__":
    unittest.main()
