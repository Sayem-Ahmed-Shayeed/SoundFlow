import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QScrollArea,
        QWidget,
    )

    from soundflow.core.settings import Settings
    from soundflow.design import CONTROL_HEIGHT_SM, SPACE_3, stylesheet
    from soundflow.ui import MainWindow  # Load the public UI surface first.
    from soundflow.preferences.tabs.general import GeneralTab

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class GeneralTabUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_general_tab_scrolls_and_uses_compact_theme_field(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            tab = GeneralTab(Settings())
            tab.resize(700, 360)
            tab.show()
            self.application.processEvents()

            scroll = tab.findChild(QScrollArea, "generalScroll")
            self.assertIsNotNone(scroll)
            self.assertGreater(scroll.verticalScrollBar().maximum(), 0)

            theme = tab.findChild(QComboBox, "compactPreferenceField")
            self.assertIsNotNone(theme)
            self.assertLessEqual(theme.height(), CONTROL_HEIGHT_SM)
            self.assertLessEqual(theme.width(), 320)

            cards = tab.findChildren(QWidget, "preferencesCard")
            self.assertTrue(cards)
            self.assertTrue(
                all(card.layout().contentsMargins().top() >= SPACE_3 for card in cards)
            )
            for card in cards:
                heading = card.findChild(QLabel, "headingText")
                self.assertIsNotNone(heading)
                self.assertGreaterEqual(
                    heading.height(), heading.fontMetrics().height()
                )
                self.assertGreaterEqual(heading.geometry().top(), SPACE_3)
                self.assertGreaterEqual(heading.geometry().left(), SPACE_3)
                self.assertLessEqual(card.width(), scroll.viewport().width())

            scroll.verticalScrollBar().setValue(
                scroll.verticalScrollBar().maximum()
            )
            self.assertEqual(
                scroll.verticalScrollBar().value(),
                scroll.verticalScrollBar().maximum(),
            )
        finally:
            self.application.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
