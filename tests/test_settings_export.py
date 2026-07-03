import json
import tempfile
import unittest
from pathlib import Path

from soundflow.core.export import ExportError, export_transcript
from soundflow.core.settings import Settings, SettingsStore


class SettingsAndExportTests(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = SettingsStore(path)
            settings = Settings(language="bn", global_hotkeys=False)
            store.save(settings)
            loaded = store.load()
            self.assertEqual(loaded.language, "bn")
            self.assertFalse(loaded.global_hotkeys)
            json.loads(path.read_text(encoding="utf-8"))

    def test_legacy_shortcut_and_precision_are_migrated(self):
        settings = Settings(
            push_to_talk_hotkey="ctrl+alt+space",
            compute_type="float32",
        ).normalized()
        self.assertEqual(settings.push_to_talk_hotkey, "ctrl+space")
        self.assertEqual(settings.compute_type, "int8")

    def test_text_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.txt"
            export_transcript(path, "hello")
            self.assertEqual(path.read_text(encoding="utf-8"), "hello\n")

    def test_unknown_export(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ExportError):
                export_transcript(Path(directory) / "transcript.pdf", "hello")


if __name__ == "__main__":
    unittest.main()
