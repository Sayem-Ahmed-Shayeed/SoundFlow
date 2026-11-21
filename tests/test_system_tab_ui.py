import gc
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QWidget,
    )

    from soundflow import __version__
    from soundflow.core.settings import Settings
    from soundflow.design import stylesheet
    from soundflow.preferences.system_check import SystemCheckResult
    from soundflow.preferences.tabs.system import SystemTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


def _result(**overrides) -> SystemCheckResult:
    values = {
        "model_ready": True,
        "microphone_ready": True,
        "hotkey_ready": True,
        "paste_ready": True,
        "effective_device": "cpu",
    }
    values.update(overrides)
    return SystemCheckResult(**values)


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class SystemTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def test_five_readiness_rows_and_no_duplicate_model_location(self):
        tab = SystemTab(Settings(model_path="/tmp/soundflow/model"))
        # Five checks, the data folder and the About line.
        self.assertEqual(len(tab.findChildren(QWidget, "prefsRow")), 7)
        self.assertIsNone(tab.findChild(QLineEdit, "systemModelPath"))

    def test_checks_run_when_the_page_is_shown(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = SystemTab(Settings())
            with patch(
                "soundflow.preferences.tabs.system.run_system_check",
                return_value=_result(),
            ) as check:
                tab.resize(960, 700)
                tab.show()
                self.application.processEvents()
                self.application.processEvents()
                check.assert_called()
            self.assertEqual(tab.findChild(QLabel, "systemStatusModel").text(), "Ready")
        finally:
            self.application.setStyleSheet(previous_stylesheet)

    def test_statuses_and_fixes_follow_the_check(self):
        tab = SystemTab(Settings(inference_device="cuda", global_hotkeys=True))
        result = _result(
            microphone_ready=False,
            hotkey_ready=False,
            effective_device="cpu",
        )
        with patch(
            "soundflow.preferences.tabs.system.run_system_check",
            return_value=result,
        ):
            tab.run_check()

        self.assertEqual(
            tab.findChild(QLabel, "systemStatusMicrophone").text(), "Unavailable"
        )
        self.assertEqual(tab.findChild(QLabel, "systemStatusModel").text(), "Ready")
        self.assertEqual(
            tab.findChild(QLabel, "systemStatusShortcut").text(), "Needs permission"
        )
        self.assertEqual(
            tab.findChild(QLabel, "systemStatusDevice").text(), "Processor"
        )
        self.assertEqual(tab._fix_buttons["shortcut"].text(), "Allow")
        self.assertFalse(tab._fix_buttons["shortcut"].isHidden())
        self.assertEqual(tab._fix_buttons["microphone"].text(), "Choose microphone")
        self.assertTrue(tab._fix_buttons["model"].isHidden())

    def test_allow_emits_the_permission_request(self):
        tab = SystemTab(Settings(global_hotkeys=True))
        with patch(
            "soundflow.preferences.tabs.system.run_system_check",
            return_value=_result(hotkey_ready=False),
        ):
            tab.run_check()
        requests = []
        tab.shortcut_permission_requested.connect(lambda: requests.append(True))
        tab._fix_buttons["shortcut"].click()
        self.assertEqual(requests, [True])

    def test_fix_buttons_ask_the_page_to_open_the_right_tab(self):
        tab = SystemTab(Settings())
        with patch(
            "soundflow.preferences.tabs.system.run_system_check",
            return_value=_result(microphone_ready=False, model_ready=False),
        ):
            tab.run_check()
        sections = []
        tab.section_requested.connect(sections.append)
        tab._fix_buttons["microphone"].click()
        tab._fix_buttons["model"].click()
        self.assertEqual(sections, ["dictation", "speech_model"])

    def test_processing_reports_gpu_and_fallback_copy(self):
        tab = SystemTab(Settings(inference_device="cuda"))
        with patch(
            "soundflow.preferences.tabs.system.run_system_check",
            return_value=_result(effective_device="cuda"),
        ):
            tab.run_check()
        self.assertEqual(tab.findChild(QLabel, "systemStatusDevice").text(), "GPU")

        with patch(
            "soundflow.preferences.tabs.system.run_system_check",
            return_value=_result(effective_device="cpu"),
        ):
            tab.run_check()
        self.assertEqual(tab.findChild(QLabel, "systemStatusDevice").text(), "Processor")
        self.assertIn("CUDA isn", tab._rows["device"].description_label.text())

    def test_data_folder_is_read_only_with_an_open_button(self):
        tab = SystemTab(Settings())
        data_path = tab.findChild(QLineEdit, "systemDataPath")
        self.assertIsNotNone(data_path)
        self.assertTrue(data_path.text())
        self.assertTrue(data_path.isReadOnly())
        open_button = tab.findChild(QPushButton, "systemSecondaryButton")
        self.assertEqual(open_button.text(), "Open folder")

    def test_about_shows_the_version_and_tagline(self):
        tab = SystemTab(Settings())
        texts = [label.text() for label in tab.findChildren(QLabel)]
        self.assertIn(f"Soundflow {__version__}", texts)
        self.assertIn("Free and private dictation for Linux.", texts)

    def test_check_again_reruns_the_checks(self):
        tab = SystemTab(Settings())
        with patch(
            "soundflow.preferences.tabs.system.run_system_check",
            return_value=_result(),
        ) as check:
            tab._check_button.click()
        check.assert_called_once()

    def test_layout_scrolls_at_small_heights(self):
        tab = SystemTab(Settings())
        tab.resize(960, 470)
        tab.show()
        self.application.processEvents()
        self.assertIsNotNone(tab.findChild(QScrollArea, "systemTabScroll"))


if __name__ == "__main__":
    unittest.main()
