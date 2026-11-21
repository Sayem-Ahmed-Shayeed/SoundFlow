import gc
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QPushButton

    from soundflow.core.settings import Settings
    from soundflow.design import stylesheet
    from soundflow.preferences.tabs.dictation import (
        DictationTab,
        pause_choice,
        pause_milliseconds,
    )
    from soundflow.preferences.widgets import key_token
    from soundflow.ui.widgets import SegmentedControl, ToggleSwitch

    HAS_QT = True
except ImportError:
    HAS_QT = False

_LIST_DEVICES = "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices"
_CAPTURE = "soundflow.preferences.tabs.dictation.AudioCapture"


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class DictationTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self):
        # Delete this test's windows on the main thread. Left to the garbage
        # collector, they can be freed from the device-scan thread, which
        # makes Shiboken delete an already-destroyed widget and crash.
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def make_tab(self, settings=None):
        with patch(_LIST_DEVICES, return_value=[]):
            return DictationTab(settings or Settings())

    def test_shortcut_recorder_takes_a_new_combination(self):
        settings = Settings(push_to_talk_hotkey="ctrl+alt+space", hotkey_authorized=True)
        tab = self.make_tab(settings)
        tab._recorder.findChild(QPushButton).click()
        self.assertTrue(tab._recorder.recording)
        QTest.keyClick(
            tab._recorder,
            Qt.Key.Key_K,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
        )
        self.assertFalse(tab._recorder.recording)
        self.assertEqual(tab._recorder.shortcut(), "ctrl+shift+k")

        updated = Settings(push_to_talk_hotkey="ctrl+alt+space", hotkey_authorized=True)
        tab.write_back(updated)
        self.assertEqual(updated.push_to_talk_hotkey, "ctrl+shift+k")
        self.assertFalse(updated.hotkey_authorized)

    def test_escape_cancels_recording_and_keeps_the_shortcut(self):
        tab = self.make_tab()
        tab._recorder.start()
        QTest.keyClick(tab._recorder, Qt.Key.Key_Escape)
        self.assertFalse(tab._recorder.recording)
        self.assertEqual(tab._recorder.shortcut(), "ctrl+alt+space")

    def test_a_key_without_a_modifier_is_refused_while_recording(self):
        tab = self.make_tab()
        tab._recorder.start()
        QTest.keyClick(tab._recorder, Qt.Key.Key_K)
        self.assertTrue(tab._recorder.recording)
        self.assertEqual(tab._recorder.shortcut(), "ctrl+alt+space")
        self.assertFalse(tab._recorder._hint.isHidden())

    def test_go_back_link_only_appears_when_the_shortcut_is_not_default(self):
        tab = self.make_tab(Settings(push_to_talk_hotkey="ctrl+alt+space"))
        tab.show()
        self.application.processEvents()
        self.assertFalse(tab._reset.isVisibleTo(tab))

        tab._recorder.set_shortcut("ctrl+shift+k")
        tab._recorder.changed.emit("ctrl+shift+k")
        self.assertTrue(tab._reset.isVisibleTo(tab))
        tab._reset.click()
        self.assertEqual(tab._recorder.shortcut(), "ctrl+alt+space")
        self.assertFalse(tab._reset.isVisibleTo(tab))

    def test_wayland_note_follows_the_other_apps_switch(self):
        tab = self.make_tab(Settings(global_hotkeys=True))
        tab.show()
        self.application.processEvents()
        self.assertTrue(tab._wayland_note.isVisibleTo(tab))
        tab._other_apps.setChecked(False)
        self.assertFalse(tab._wayland_note.isVisibleTo(tab))

    def test_finish_choice_maps_onto_the_existing_fields(self):
        settings = Settings(auto_insert=True, auto_copy=False, terminal_paste=True)
        tab = self.make_tab(settings)
        tab.show()
        self.application.processEvents()
        self.assertEqual(tab._finish.value(), "paste")
        self.assertTrue(tab._terminal_slot.isVisibleTo(tab))

        updated = Settings()
        tab.write_back(updated)
        self.assertTrue(updated.auto_insert)
        self.assertTrue(updated.terminal_paste)

        tab._finish.set_value("copy")
        tab._finish.changed.emit("copy")
        self.assertFalse(tab._terminal_slot.isVisibleTo(tab))
        copied = Settings()
        tab.write_back(copied)
        self.assertFalse(copied.auto_insert)
        self.assertTrue(copied.auto_copy)

    def test_paste_choice_also_leaves_the_text_on_the_clipboard(self):
        tab = self.make_tab(Settings(auto_insert=False, auto_copy=False))
        self.assertEqual(tab._finish.value(), "copy")
        tab._finish.rows[0].radio.setChecked(True)
        updated = Settings()
        tab.write_back(updated)
        self.assertTrue(updated.auto_insert)
        self.assertTrue(updated.auto_copy)

    def test_pause_length_maps_to_the_three_stored_values(self):
        self.assertEqual(pause_milliseconds("short"), 400)
        self.assertEqual(pause_milliseconds("medium"), 700)
        self.assertEqual(pause_milliseconds("long"), 1200)
        self.assertEqual(pause_choice(400), "short")
        self.assertEqual(pause_choice(700), "medium")
        self.assertEqual(pause_choice(1200), "long")
        self.assertEqual(pause_choice(1000), "long")
        self.assertEqual(pause_choice(250), "short")

        tab = self.make_tab(Settings(silence_duration_ms=1200))
        self.assertEqual(tab._pause.value(), "long")
        tab._pause.button("short").click()
        updated = Settings()
        tab.write_back(updated)
        self.assertEqual(updated.silence_duration_ms, 400)

    def test_microphone_test_opens_capture_only_while_running(self):
        tab = self.make_tab(Settings(microphone=3))
        tab._select_microphone(3)
        with patch(_CAPTURE) as capture_cls:
            capture = capture_cls.return_value
            tab._toggle_mic_test()
            capture_cls.assert_called_once()
            capture.start.assert_called_once_with(3)
            on_level = capture_cls.call_args.kwargs["on_level"]
            on_level(0.5)
            self.assertEqual(tab._meter.value(), 50)
            self.assertFalse(tab._meter_line.isHidden())

            tab._toggle_mic_test()
            capture.stop.assert_called_once()
            self.assertTrue(tab._meter_line.isHidden())
            self.assertEqual(tab._test_button.text(), "Test")

    def test_leaving_the_tab_stops_the_microphone_test(self):
        tab = self.make_tab()
        tab.show()
        with patch(_CAPTURE) as capture_cls:
            tab._toggle_mic_test()
            capture = capture_cls.return_value
            tab.hide()
            capture.stop.assert_called_once()

    def test_microphone_error_is_shown_inline(self):
        tab = self.make_tab()
        with patch(_CAPTURE) as capture_cls:
            capture_cls.return_value.start.side_effect = RuntimeError("no device")
            tab._toggle_mic_test()
        self.assertIn("no device", tab._mic_row.description_label.text())
        self.assertIsNone(tab._capture)

    def test_refresh_reads_language_and_microphone_from_settings(self):
        tab = self.make_tab(Settings(language="en", microphone=None))
        tab.refresh_from_settings(Settings(language="bn", microphone=7))
        self.assertEqual(tab._language.currentData(), "bn")
        self.assertEqual(tab._mic.currentData(), 7)

    def test_the_mic_test_button_and_pickers_use_compact_height(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = self.make_tab()
            tab.resize(960, 700)
            tab.show()
            self.application.processEvents()
            combos = tab.findChildren(QComboBox, "compactPreferenceField")
            self.assertEqual(len(combos), 2)
            self.assertTrue(all(combo.height() <= 36 for combo in combos))
            labels = [label for label in tab.findChildren(QLabel) if label.isVisible()]
            self.assertTrue(
                all(label.height() >= label.fontMetrics().height() for label in labels)
            )
            self.assertIsInstance(tab.findChild(SegmentedControl), SegmentedControl)
            self.assertEqual(len(tab.findChildren(ToggleSwitch)), 3)
        finally:
            self.application.setStyleSheet(previous_stylesheet)

    def test_key_token_maps_qt_keys_to_hotkey_names(self):
        self.assertEqual(key_token(Qt.Key.Key_K.value), "k")
        self.assertEqual(key_token(Qt.Key.Key_5.value), "5")
        self.assertEqual(key_token(Qt.Key.Key_F7.value), "f7")
        self.assertEqual(key_token(Qt.Key.Key_Space.value), "space")
        self.assertEqual(key_token(Qt.Key.Key_Return.value), "enter")
        self.assertIsNone(key_token(Qt.Key.Key_Control.value))


if __name__ == "__main__":
    unittest.main()
