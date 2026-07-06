import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
    )

    from soundflow.core.settings import Settings
    from soundflow.design import CONTROL_HEIGHT_SM, stylesheet
    from soundflow.ui import MainWindow  # Load the application's public UI surface first.
    from soundflow.preferences.system_check import SystemCheckResult
    from soundflow.preferences.tabs.system import SystemTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class SystemTabUiTests(unittest.TestCase):
    _tabs = []

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def test_builds_scannable_readiness_and_data_cards(self):
        tab = SystemTab(Settings(model_path="/tmp/soundflow/model"))

        self.assertEqual(len(tab.findChildren(QWidget, "systemCheckRow")), 5)
        check_button = tab.findChild(QPushButton, "systemCheckButton")
        self.assertIsNotNone(check_button)
        self.assertEqual(
            check_button.maximumHeight(),
            CONTROL_HEIGHT_SM,
        )
        last_checked = tab.findChild(QLabel, "systemLastChecked")
        self.assertIsNotNone(last_checked)
        self.assertTrue(
            last_checked.alignment() & Qt.AlignmentFlag.AlignVCenter
        )
        model_path = tab.findChild(QLineEdit, "systemModelPath")
        self.assertIsNotNone(model_path)
        self.assertEqual(model_path.text(), "/tmp/soundflow/model")
        self.assertTrue(model_path.isReadOnly())
        self.assertEqual(model_path.maximumHeight(), CONTROL_HEIGHT_SM)
        data_path = tab.findChild(QLineEdit, "systemDataPath")
        self.assertTrue(data_path.text())
        self.assertTrue(data_path.isReadOnly())
        self.assertFalse(data_path.toolTip())

        open_button = tab.findChild(QPushButton, "systemSecondaryButton")
        self.assertEqual(open_button.text(), "Open folder")
        self.assertEqual(
            open_button.maximumHeight(),
            CONTROL_HEIGHT_SM,
        )

        local_data_card = tab.findChild(QWidget, "localDataCard")
        self.assertLess(local_data_card.sizeHint().height(), 180)

    def test_run_check_updates_individual_statuses_and_fallback_copy(self):
        tab = SystemTab(Settings(inference_device="cuda"))
        result = SystemCheckResult(
            model_ready=True,
            microphone_ready=False,
            hotkey_ready=False,
            paste_ready=True,
            effective_device="cpu",
        )

        with patch(
            "soundflow.preferences.tabs.system.run_system_check",
            return_value=result,
        ):
            tab.run_check()

        self.assertEqual(tab.findChild(QLabel, "systemStatusPill").text(), "Needs attention")
        self.assertEqual(tab.findChild(QLabel, "systemStatusModel").text(), "Ready")
        self.assertEqual(
            tab.findChild(QLabel, "systemStatusMicrophone").text(),
            "Unavailable",
        )
        self.assertEqual(
            tab.findChild(QLabel, "systemStatusShortcut").text(),
            "Permission needed",
        )
        self.assertEqual(
            tab.findChild(QLabel, "systemStatusInsertion").text(),
            "Ready",
        )
        self.assertEqual(
            tab.findChild(QLabel, "systemStatusDevice").text(),
            "CPU · CUDA unavailable",
        )

    def test_real_preferences_height_preserves_readiness_rows(self):
        tab = SystemTab(Settings())
        self._tabs.append(tab)
        tab.resize(1175, 470)
        tab.show()
        self.application.processEvents()

        rows = tab.findChildren(QWidget, "systemCheckRow")
        self.assertIsNotNone(tab.findChild(QScrollArea, "systemScroll"))
        self.assertTrue(rows)
        self.assertTrue(
            all(row.height() >= row.minimumSizeHint().height() for row in rows)
        )

    def test_compact_system_actions_remain_compact_with_theme_applied(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = SystemTab(Settings())
            self._tabs.append(tab)
            tab.resize(1000, 700)
            tab.show()
            self.application.processEvents()

            self.assertLessEqual(
                tab.findChild(QPushButton, "systemCheckButton").height(),
                CONTROL_HEIGHT_SM,
            )
            self.assertLessEqual(
                tab.findChild(QPushButton, "systemSecondaryButton").height(),
                CONTROL_HEIGHT_SM,
            )
            self.assertLessEqual(
                tab.findChild(QLineEdit, "systemDataPath").height(),
                CONTROL_HEIGHT_SM,
            )
            self.assertLessEqual(
                tab.findChild(QLineEdit, "systemModelPath").height(),
                CONTROL_HEIGHT_SM,
            )
            rows = tab.findChildren(QWidget, "systemCheckRow")
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(row.height() >= 32 for row in rows))
            self.assertGreater(
                tab.findChild(QLabel, "systemStatusPill").height(),
                0,
            )
        finally:
            self.application.setStyleSheet(previous_stylesheet)


if HAS_QT:
    from PySide6.QtWidgets import QWidget


if __name__ == "__main__":
    unittest.main()
