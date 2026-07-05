import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QLabel, QPushButton

    from soundflow.core.settings import Settings
    from soundflow.ui import MainWindow  # Load the application's public UI surface first.
    from soundflow.preferences.system_check import SystemCheckResult
    from soundflow.preferences.tabs.system import SystemTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class SystemTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_builds_scannable_readiness_and_data_cards(self):
        tab = SystemTab(Settings(model_path="/tmp/soundflow/model"))

        self.assertEqual(len(tab.findChildren(QWidget, "systemCheckRow")), 5)
        self.assertIsNotNone(tab.findChild(QPushButton, "systemCheckButton"))
        self.assertEqual(
            tab.findChild(QLabel, "systemModelPath").text(),
            "/tmp/soundflow/model",
        )
        model_path = tab.findChild(QLabel, "systemModelPath")
        self.assertGreater(
            model_path.minimumHeight(),
            model_path.fontMetrics().lineSpacing(),
        )
        self.assertTrue(tab.findChild(QLabel, "systemDataPath").text())

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


if HAS_QT:
    from PySide6.QtWidgets import QWidget


if __name__ == "__main__":
    unittest.main()
