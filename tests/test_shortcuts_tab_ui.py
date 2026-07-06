import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QWidget

    from soundflow.core.settings import Settings
    from soundflow.design import CONTROL_HEIGHT_SM, stylesheet
    from soundflow.ui import MainWindow  # Load the public UI surface first.
    from soundflow.preferences.tabs.shortcuts import ShortcutsTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class ShortcutsTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_other_shortcut_picker_uses_compact_fields(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = ShortcutsTab(Settings())
            tab.resize(1000, 600)
            tab.show()
            self.application.processEvents()

            fields = tab.findChildren(QComboBox, "compactShortcutField")
            self.assertEqual(len(fields), 2)
            self.assertTrue(
                all(field.height() <= CONTROL_HEIGHT_SM for field in fields)
            )
            self.assertLessEqual(fields[0].width(), 128)
            self.assertLessEqual(fields[1].width(), 96)
            cards = tab.findChildren(QWidget, "preferencesCard")
            self.assertEqual(len(cards), 2)
            for card in cards:
                labels = [
                    label for label in card.findChildren(QLabel)
                    if label.isVisible()
                ]
                self.assertTrue(labels)
                self.assertTrue(
                    all(
                        label.height() >= label.fontMetrics().height()
                        for label in labels
                    )
                )
        finally:
            self.application.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
