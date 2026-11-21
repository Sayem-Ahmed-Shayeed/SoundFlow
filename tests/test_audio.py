import unittest
from unittest.mock import patch

from soundflow.audio import AudioCapture, AudioCaptureError


def _broken_portaudio():
    raise OSError("PortAudio library not found")


class AudioCaptureTests(unittest.TestCase):
    def test_device_listing_tolerates_broken_native_library(self):
        with patch("soundflow.audio._import_sounddevice", side_effect=_broken_portaudio):
            self.assertEqual(AudioCapture.list_input_devices(), [])

    def test_start_reports_native_library_problem(self):
        capture = AudioCapture(lambda frame: None, lambda level: None, lambda error: None)
        with patch("soundflow.audio._import_sounddevice", side_effect=_broken_portaudio):
            with self.assertRaisesRegex(AudioCaptureError, "PortAudio"):
                capture.start()


if __name__ == "__main__":
    unittest.main()
