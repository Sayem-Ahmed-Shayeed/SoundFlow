import os
import tempfile
import unittest
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication

    from soundflow.core.settings import Settings, SettingsStore
    from soundflow.ui import (
        MainWindow,
        RecordingOverlay,
        ShortcutPicker,
    )

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def test_shortcut_picker_round_trip(self):
        picker = ShortcutPicker("ctrl+alt+space")
        self.assertEqual(picker.shortcut(), "ctrl+alt+space")
        picker.set_shortcut("ctrl+shift+v")
        self.assertEqual(picker.shortcut(), "ctrl+shift+v")

    def test_overlay_displays_three_key_chord(self):
        overlay = RecordingOverlay()
        overlay.show_recording("ctrl+alt+space")
        self.assertEqual(overlay.keycap.text(), "CTRL + ALT + SPACE")
        overlay.hide()
        overlay.close()

    def test_authorization_indicator_and_persistence(self):
        class FakeInjector:
            def __init__(self):
                self.starts = 0

            def start(self):
                self.starts += 1

            def stop(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            settings = Settings(hotkey_authorized=False)
            window = MainWindow(
                settings,
                store,
                demo_mode=True,
                no_hotkeys=True,
            )
            window.apply_appearance("dark")
            self.assertTrue(window.property("darkAppearance"))
            window.apply_appearance("light")
            self.assertFalse(window.property("darkAppearance"))
            injector = FakeInjector()
            window.injector = injector
            window._set_hotkey_indicator(
                "error", "setup required", retry="hotkey"
            )
            self.assertFalse(window.hotkey_retry_button.isHidden())
            window.retry_setup()
            self.assertTrue(window._hotkey_setup_requested)
            window.no_hotkeys = False
            window._hotkey_ready("Ctrl + Alt + Space")
            self.assertTrue(settings.hotkey_authorized)
            self.assertEqual(injector.starts, 1)
            self.assertFalse(window._injector_is_ready)
            window._injector_ready()
            self.assertTrue(window._injector_is_ready)
            self.assertTrue(window.hotkey_retry_button.isHidden())
            self.assertTrue(store.load().hotkey_authorized)
            window.shutdown()
            window.close()


if __name__ == "__main__":
    unittest.main()
