import json
import tempfile
import unittest
from pathlib import Path

from soundflow.core.settings import Settings, SettingsStore


class SettingsDefaultsTests(unittest.TestCase):
    def test_defaults_for_the_redesigned_preferences(self):
        settings = Settings()
        self.assertEqual(settings.inference_device, "auto")
        self.assertTrue(settings.open_at_login)
        self.assertFalse(hasattr(settings, "toggle_hotkey"))
        self.assertFalse(hasattr(settings, "insert_hotkey"))
        self.assertFalse(hasattr(settings, "show_shortcut_hint"))

    def test_device_values_are_kept_and_anything_else_becomes_auto(self):
        for value in ("auto", "cuda", "cpu"):
            self.assertEqual(Settings(inference_device=value).normalized().inference_device, value)
        self.assertEqual(Settings(inference_device="tpu").normalized().inference_device, "auto")

    def test_old_file_with_removed_fields_still_loads_and_drops_them(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "toggle_hotkey": "ctrl+d",
                        "insert_hotkey": "ctrl+i",
                        "show_shortcut_hint": True,
                        "inference_device": "cpu",
                        "push_to_talk_hotkey": "ctrl+alt+space",
                        "shortcut_schema_version": 2,
                        "hotkey_authorized": True,
                    }
                ),
                encoding="utf-8",
            )
            store = SettingsStore(path)
            loaded = store.load()
            self.assertEqual(loaded.inference_device, "cpu")
            self.assertTrue(loaded.hotkey_authorized)
            self.assertTrue(loaded.open_at_login)

            store.save(loaded)
            saved = json.loads(path.read_text(encoding="utf-8"))
            for key in ("toggle_hotkey", "insert_hotkey", "show_shortcut_hint"):
                self.assertNotIn(key, saved)
            self.assertEqual(saved["inference_device"], "cpu")
            self.assertTrue(saved["open_at_login"])


if __name__ == "__main__":
    unittest.main()
