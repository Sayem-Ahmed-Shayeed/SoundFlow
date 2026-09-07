import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent, Qt
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

    def test_model_selection_coalesces_pending_full_form_save(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            settings = Settings()
            with patch(
                "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
                return_value=[],
            ):
                page = PreferencesPage(settings, store)
            saved = []
            page.settings_saved.connect(lambda: saved.append(True))
            device_index = page.dictation_tab._device.findData("cuda")

            with patch.object(store, "save", wraps=store.save) as save:
                page.dictation_tab._device.setCurrentIndex(device_index)
                self.assertTrue(page._save_timer.isActive())
                page.dictation_tab._model_manager.model_path_selected.emit(
                    "/tmp/faster-whisper-medium"
                )
                self.assertFalse(page._save_timer.isActive())
                QTest.qWait(180)
                self.application.processEvents()

            loaded = store.load()
            self.assertEqual(loaded.inference_device, "cuda")
            self.assertEqual(
                loaded.model_path, "/tmp/faster-whisper-medium"
            )
            self.assertEqual(save.call_count, 1)
            self.assertEqual(saved, [True])

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

    def test_reverting_runtime_signature_clears_deferred_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            self._windows.append(window)
            original_model_path = window.settings.model_path
            window.state.start()
            with patch.object(window, "_rebuild_runtime") as rebuild:
                window.settings.model_path = "/tmp/faster-whisper-base"
                window._preferences_saved()
                self.assertTrue(window._pending_runtime_rebuild)

                window.settings.model_path = original_model_path
                window._preferences_saved()
                self.assertFalse(window._pending_runtime_rebuild)

                window.state.stop()
                window._pipeline_finished()
                rebuild.assert_not_called()

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
            order = []
            with (
                patch.object(
                    window.preferences_page,
                    "shutdown",
                    side_effect=lambda: order.append("preferences"),
                ) as shutdown,
                patch.object(
                    window._history_store,
                    "close",
                    side_effect=lambda: order.append("history"),
                ),
                patch(
                    "soundflow.ui.main_window.LegacyMainWindow.shutdown",
                    autospec=True,
                    side_effect=lambda _window: order.append("runtime"),
                ) as runtime_shutdown,
            ):
                window.shutdown()
            shutdown.assert_called_once_with()
            runtime_shutdown.assert_called_once_with(window)
            self.assertEqual(order, ["preferences", "history", "runtime"])

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
        caps = [
            page._keys_box.itemAt(index).widget().text()
            for index in range(page._keys_box.count())
            if hasattr(page._keys_box.itemAt(index).widget(), "text")
        ]
        self.assertIn("Ctrl", caps)
        self.assertIn("Shift", caps)
        self.assertIn("V", caps)

    def test_dictation_home_has_a_clear_recorder_hierarchy(self):
        page = DictationPage()

        self.assertEqual(page._eyebrow.text(), "PRIVATE VOICE INPUT")
        self.assertEqual(page._prompt.text(), "Dictation")
        self.assertEqual(page._hero_panel.objectName(), "dictationStage")
        self.assertEqual(page._hero_effect.opacity(), 1.0)

    def test_window_chrome_keeps_28px_targets(self):
        chrome = WindowChrome()
        chrome.show()
        self.application.processEvents()
        buttons = chrome.findChildren(type(chrome._close))
        self.assertEqual(len(buttons), 3)
        self.assertTrue(all(button.size().height() >= 28 for button in buttons))


if __name__ == "__main__":
    unittest.main()
