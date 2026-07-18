import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLabel

    from soundflow.core.settings import Settings, SettingsStore
    from soundflow.ui import MainWindow
    from soundflow.ui.pages import DictationPage
    from soundflow.ui.widgets import WindowChrome
    from soundflow.preferences.page import PreferencesPage
    from soundflow.preferences.tabs.dictation import DictationTab
    from soundflow.preferences.tabs.shortcuts import ShortcutsTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class UiRuntimeContractTests(unittest.TestCase):
    _windows = []

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_silence_timeout_participates_in_runtime_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(
                Settings(silence_duration_ms=700),
                store,
                demo_mode=True,
                no_hotkeys=True,
            )
            self._windows.append(window)
            before = window._runtime_settings_signature()
            window.settings.silence_duration_ms = 1200
            after = window._runtime_settings_signature()
            self.assertNotEqual(before, after)

    def test_runtime_change_during_recording_rebuilds_after_drain(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(
                Settings(),
                store,
                demo_mode=True,
                no_hotkeys=True,
            )
            self._windows.append(window)
            window.state.start()
            window.settings.silence_duration_ms = 1200
            with patch.object(window, "_rebuild_runtime") as rebuild:
                window._preferences_saved()
                self.assertTrue(window._pending_runtime_rebuild)
                rebuild.assert_not_called()
                window.state.stop()
                window._pipeline_finished()
                rebuild.assert_called_once()
                self.assertFalse(window._pending_runtime_rebuild)

    def test_dictation_device_choices_match_normalized_settings(self):
        with patch(
            "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
            return_value=[],
        ):
            tab = DictationTab(Settings())
        values = [
            tab._device.itemData(index)
            for index in range(tab._device.count())
        ]
        self.assertEqual(values, ["cpu", "cuda"])

    def test_browsed_model_path_is_auto_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            settings = Settings()
            with patch(
                "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
                return_value=[],
            ):
                page = PreferencesPage(settings, store)
            dictation = page._tab_widgets[1]
            with patch(
                "soundflow.preferences.tabs.dictation.QFileDialog.getExistingDirectory",
                return_value="/tmp/new-model",
            ):
                dictation._browse_model()
            QTest.qWait(180)
            self.application.processEvents()
            self.assertEqual(store.load().model_path, "/tmp/new-model")

    def test_model_manager_selection_is_saved_immediately(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            settings = Settings()
            with patch(
                "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
                return_value=[],
            ):
                page = PreferencesPage(settings, store)
            page.dictation_tab.model_path_changed.emit(
                "/tmp/faster-whisper-medium"
            )
            self.assertEqual(
                store.load().model_path, "/tmp/faster-whisper-medium"
            )

    def test_model_switch_defers_rebuild_while_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            self._windows.append(window)
            window.state.start()
            with patch.object(window, "_rebuild_runtime") as rebuild:
                window.preferences_page.dictation_tab.model_path_changed.emit(
                    "/tmp/faster-whisper-base"
                )
                self.assertTrue(window._pending_runtime_rebuild)
                rebuild.assert_not_called()
                window.state.stop()
                window._pipeline_finished()
                rebuild.assert_called_once()

    def test_preferences_shutdown_delegates_to_model_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            with patch(
                "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
                return_value=[],
            ):
                page = PreferencesPage(Settings(), store)
            with patch.object(
                page.dictation_tab._model_manager, "shutdown"
            ) as manager_shutdown:
                page.shutdown()
            manager_shutdown.assert_called_once_with()

    def test_window_shutdown_delegates_to_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            self._windows.append(window)
            with (
                patch.object(window.preferences_page, "shutdown") as shutdown,
                patch(
                    "soundflow.ui.main_window.LegacyMainWindow.shutdown",
                    autospec=True,
                ) as runtime_shutdown,
            ):
                window.shutdown()
            shutdown.assert_called_once_with()
            runtime_shutdown.assert_called_once_with(window)

    def test_shortcut_summary_tracks_picker_and_reset(self):
        tab = ShortcutsTab(Settings(push_to_talk_hotkey="ctrl+alt+space"))
        tab._picker.set_shortcut("ctrl+shift+v")
        self.application.processEvents()
        caps = tab.findChildren(QLabel, "shortcutSummaryCap")
        self.assertEqual([cap.text() for cap in caps], ["Ctrl", "Shift", "V"])
        tab._reset()
        self.application.processEvents()
        self.assertEqual(
            [cap.text() for cap in caps],
            ["Ctrl", "Alt", "SPACE"],
        )

    def test_dictation_ring_is_accessible_and_ignores_right_click(self):
        page = DictationPage()
        page.resize(900, 600)
        page.show()
        self.application.processEvents()
        self.assertTrue(page._ring.accessibleName())
        emissions = []
        page.dictation_toggled.connect(lambda: emissions.append(True))
        QTest.mouseClick(page._ring, Qt.MouseButton.RightButton)
        self.assertEqual(emissions, [])
        QTest.mouseClick(page._ring, Qt.MouseButton.LeftButton)
        self.assertEqual(emissions, [True])

    def test_dictation_copy_tracks_configured_global_shortcut(self):
        page = DictationPage()
        page.set_shortcut("ctrl+shift+v")
        self.assertIn("Ctrl + Shift + V", page._hero.text())

    def test_window_chrome_keeps_28px_targets(self):
        chrome = WindowChrome()
        chrome.show()
        self.application.processEvents()
        buttons = chrome.findChildren(type(chrome._close))
        self.assertEqual(len(buttons), 3)
        self.assertTrue(all(button.size().height() >= 28 for button in buttons))


if __name__ == "__main__":
    unittest.main()
