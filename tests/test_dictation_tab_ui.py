import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QProgressBar,
        QWidget,
    )

    from soundflow.core.settings import Settings
    from soundflow.design import CONTROL_HEIGHT_SM, stylesheet
    from soundflow.ui import MainWindow  # Load the public UI surface first.
    from soundflow.preferences.tabs.dictation import DictationTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class DictationTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_recognition_fields_are_compact_and_decorative_meter_is_hidden(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            with patch(
                "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
                return_value=[],
            ):
                tab = DictationTab(Settings())
            tab.resize(1000, 500)
            tab.show()
            self.application.processEvents()

            fields = tab.findChildren(QComboBox, "compactPreferenceField")
            self.assertEqual(len(fields), 3)
            self.assertTrue(
                all(field.height() <= CONTROL_HEIGHT_SM for field in fields)
            )
            self.assertFalse(tab.findChildren(QProgressBar))
            card = tab.findChild(QWidget, "preferencesCard")
            labels = [
                label for label in card.findChildren(QLabel)
                if label.isVisible()
            ]
            self.assertTrue(labels)
            self.assertTrue(
                all(label.height() >= label.fontMetrics().height() for label in labels)
            )
        finally:
            self.application.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
