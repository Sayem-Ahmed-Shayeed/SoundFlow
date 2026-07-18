import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QPushButton,
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

    def test_general_tab_scrolls_and_uses_segmented_theme_toggle(self):
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

            self.assertIsNone(tab.findChild(QComboBox, "compactPreferenceField"))
            theme = tab.findChild(QWidget, "segmentedControl")
            self.assertIsNotNone(theme)
            buttons = theme.findChildren(QPushButton)
            self.assertEqual([button.text() for button in buttons], ["Light", "Dark"])
            self.assertEqual(sum(button.isChecked() for button in buttons), 1)
            self.assertLessEqual(theme.height(), CONTROL_HEIGHT_SM + 4)
            presets = tab.findChildren(QPushButton, "presetChip")
            self.assertEqual(len(presets), 3)
            self.assertTrue(
                all(preset.height() == buttons[0].height() for preset in presets)
            )

            buttons[1].click()
            updated = Settings(appearance="light")
            tab.write_back(updated)
            self.assertEqual(updated.appearance, "dark")

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
