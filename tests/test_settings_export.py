import json
import tempfile
import unittest
from pathlib import Path

from soundflow.core.export import ExportError, export_transcript
from soundflow.core.settings import (
    SHORTCUT_SCHEMA_VERSION,
    Settings,
    SettingsStore,
)


class SettingsAndExportTests(unittest.TestCase):
    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = SettingsStore(path)
            settings = Settings(
                language="bn",
                global_hotkeys=False,
                appearance="dark",
            )
            store.save(settings)
            loaded = store.load()
            self.assertEqual(loaded.language, "bn")
            self.assertFalse(loaded.global_hotkeys)
            self.assertEqual(loaded.appearance, "dark")
            json.loads(path.read_text(encoding="utf-8"))

    def test_invalid_appearance_falls_back_to_system(self):
        settings = Settings(appearance="sepia").normalized()
        self.assertEqual(settings.appearance, "system")

    def test_three_key_shortcut_and_precision_are_normalized(self):
        settings = Settings(
            push_to_talk_hotkey="ctrl+alt+space",
            compute_type="float32",
        ).normalized()
        self.assertEqual(settings.push_to_talk_hotkey, "ctrl+alt+space")
        self.assertEqual(settings.compute_type, "int8")

    def test_legacy_shortcut_file_is_migrated_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "language": "bn",
                        "push_to_talk_hotkey": "shift+d",
                        "hotkey_authorized": True,
                    }
                ),
                encoding="utf-8",
            )
            settings = SettingsStore(path).load()
            self.assertEqual(settings.language, "bn")
            self.assertEqual(settings.push_to_talk_hotkey, "ctrl+alt+space")
            self.assertFalse(settings.hotkey_authorized)
            self.assertEqual(
                settings.shortcut_schema_version, SHORTCUT_SCHEMA_VERSION
            )
            persisted = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                persisted["shortcut_schema_version"], SHORTCUT_SCHEMA_VERSION
            )

    def test_current_custom_shortcut_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            settings = Settings(
                push_to_talk_hotkey="ctrl+shift+v",
                hotkey_authorized=True,
            )
            SettingsStore(path).save(settings)
            loaded = SettingsStore(path).load()
            self.assertEqual(loaded.push_to_talk_hotkey, "ctrl+shift+v")
            self.assertTrue(loaded.hotkey_authorized)

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
