import builtins
import unittest
from unittest.mock import patch

from soundflow.audio import AudioCapture, AudioCaptureError


class AudioCaptureTests(unittest.TestCase):
    def test_device_listing_tolerates_broken_native_library(self):
        real_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "sounddevice":
                raise OSError("PortAudio library not found")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            self.assertEqual(AudioCapture.list_input_devices(), [])

    def test_start_reports_native_library_problem(self):
        capture = AudioCapture(lambda frame: None, lambda level: None, lambda error: None)
        real_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "sounddevice":
                raise OSError("PortAudio library not found")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            with self.assertRaisesRegex(AudioCaptureError, "PortAudio"):
                capture.start()


if __name__ == "__main__":
    unittest.main()
