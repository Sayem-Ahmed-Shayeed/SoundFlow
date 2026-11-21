import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from soundflow.core.settings import Settings, SettingsStore
from soundflow.hotkeys import hotkey_from_trigger


class HotkeyFromTriggerTests(unittest.TestCase):
    def test_reads_desktop_descriptions(self):
        self.assertEqual(hotkey_from_trigger("Ctrl+Space"), "ctrl+space")
        self.assertEqual(hotkey_from_trigger("Ctrl+Z"), "ctrl+z")
        self.assertEqual(hotkey_from_trigger("Press Ctrl+Alt+Space"), "ctrl+alt+space")
        self.assertEqual(hotkey_from_trigger("<Control>z"), "ctrl+z")
        self.assertEqual(hotkey_from_trigger("<Control><Alt>space"), "ctrl+alt+space")
        self.assertEqual(hotkey_from_trigger("Super+Shift+D"), "shift+cmd+d")

    def test_rejects_what_it_cannot_read(self):
        for text in (None, "", "Space", "nonsense words", "Ctrl+Alt+Shift+Super+X"):
            self.assertIsNone(hotkey_from_trigger(text), text)


class AdoptBoundShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_home_and_preferences_follow_the_desktop_choice(self):
        from soundflow.ui.main_window import MainWindow

        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            window.hotkeys = MagicMock(shortcut_id="push_to_talk")
            window._adopt_bound_shortcut("Ctrl+Space")
            self.assertEqual(window.settings.push_to_talk_hotkey, "ctrl+space")
            self.assertEqual(window.dictation_page._shortcut_display, "Ctrl + Space")
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            caps = [
                label.text()
                for label in window.preferences_page.findChildren(QLabel)
                if label.objectName() == "keyCap"
            ]
            self.assertEqual(caps, ["Ctrl", "Space"])
            saved = store.load()
            self.assertEqual(saved.push_to_talk_hotkey, "ctrl+space")
            self.assertEqual(saved.portal_shortcut_id, "push_to_talk")
            self.assertEqual(saved.portal_bound_hotkey, "ctrl+space")
            window.hotkeys = None
            window.close()


if __name__ == "__main__":
    unittest.main()
