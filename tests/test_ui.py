import os
import tempfile
import unittest
from pathlib import Path

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLabel, QWidget

    from soundflow.core.settings import Settings, SettingsStore
    from soundflow.ui import (
        AppearanceSelector,
        MainWindow,
        RecordingOverlay,
        ShortcutPicker,
    )
    from soundflow.ui.pages import DictationPage

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class UiTests(unittest.TestCase):
    _windows = []
    _temps = []
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        windows = list(self._windows)
        self._windows.clear()
        for window in windows:
            window.no_hotkeys = True
        self.application.processEvents()
        for window in windows:
            window.shutdown()
            window.hide()
        self.application.processEvents()
        for window in windows:
            window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        while self._temps:
            self._temps.pop().cleanup()

    def test_shortcut_picker_round_trip(self):
        picker = ShortcutPicker("ctrl+alt+space")
        self.assertEqual(picker.shortcut(), "ctrl+alt+space")
        picker.set_shortcut("ctrl+shift+v")
        self.assertEqual(picker.shortcut(), "ctrl+shift+v")

    def test_appearance_selector_round_trip(self):
        changes: list[str] = []
        selector = AppearanceSelector("light")
        selector.changed.connect(changes.append)
        selector.set_value("dark")
        self.assertEqual(selector.value(), "dark")
        self.assertEqual(changes, ["dark"])

    def test_overlay_displays_three_key_chord(self):
        overlay = RecordingOverlay()
        overlay.show_recording("ctrl+alt+space")
        self.assertEqual(overlay.keycap.text(), "CTRL + ALT + SPACE")
        self.assertLessEqual(overlay.width(), 300)
        self.assertLessEqual(overlay.height(), 52)
        self.assertEqual(overlay.label.text(), "Listening")
        overlay.show_processing()
        self.assertEqual(overlay.label.text(), "Transcribing")
        overlay.hide()
        overlay.close()

    def test_main_window_hosts_four_page_shell(self):
        directory = tempfile.TemporaryDirectory()
        self._temps.append(directory)
        store = SettingsStore(Path(directory.name) / "settings.json")
        window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
        self._windows.append(window)
        self.assertIsInstance(window.dictation_page, DictationPage)
        self.assertEqual(
            set(window._page_indices),
            {"dictation", "history", "playground", "preferences"},
        )
        self.assertIsNone(window.sidebar.findChild(QWidget, "privacyCard"))
        self.assertIsNone(
            window.preferences_page.findChild(QLabel, "savedStatus")
        )
        self.assertTrue(window.persistent_status.isHidden())
        window.navigate("history")
        self.assertEqual(window.pages.currentWidget(), window.history_page)

    def test_authorization_indicator_and_persistence(self):
        class FakeInjector:
            def __init__(self):
                self.starts = 0

            def start(self):
                self.starts += 1

            def stop(self):
                pass

        directory = tempfile.TemporaryDirectory()
        self._temps.append(directory)
        store = SettingsStore(Path(directory.name) / "settings.json")
        settings = Settings(hotkey_authorized=False)
        window = MainWindow(settings, store, demo_mode=True, no_hotkeys=True)
        self._windows.append(window)
        window.apply_appearance("dark")
        self.assertTrue(window.property("darkAppearance"))
        self.assertEqual(
            window.preferences_page.general_tab._theme.value(), "dark"
        )
        window.apply_appearance("light")
        self.assertFalse(window.property("darkAppearance"))
        self.assertEqual(
            window.preferences_page.general_tab._theme.value(), "light"
        )
        injector = FakeInjector()
        window.injector = injector
        window._set_hotkey_indicator("error", "setup required", retry="hotkey")
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


if __name__ == "__main__":
    unittest.main()
