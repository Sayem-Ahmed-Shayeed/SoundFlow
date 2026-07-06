import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QLabel

    from soundflow.design import stylesheet
    from soundflow.ui import MainWindow  # Load the public UI surface first.
    from soundflow.playground.page import PlaygroundPage

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class PlaygroundUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_quick_actions_keep_both_text_lines_visible(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        try:
            page = PlaygroundPage()
            page.resize(1000, 650)
            page.show()
            self.application.processEvents()

            self.assertGreaterEqual(page._command.height(), 132)
            self.assertLessEqual(page._command.height(), 220)
            for card in (
                page._insert_card,
                page._format_card,
                page._rewrite_card,
            ):
                self.assertEqual(card.height(), 52)
                labels = card.findChildren(QLabel)
                self.assertEqual(len(labels), 3)
                for label in labels[1:]:
                    self.assertGreaterEqual(
                        label.height(),
                        label.fontMetrics().height(),
                    )
        finally:
            self.application.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
