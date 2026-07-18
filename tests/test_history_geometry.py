import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QFrame, QPushButton

    from soundflow.design import stylesheet
    from soundflow.ui import MainWindow  # Load the public UI surface first.
    from soundflow.history.page import HistoryPage, TranscriptCard
    from soundflow.history.store import HistoryStore

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class HistoryGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_full_transcripts_and_editors_are_not_clipped(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.db")
            for index in range(8):
                store.add(
                    f"Transcript {index} " + ("with complete editable text " * 8),
                    12.0,
                )
            try:
                page = HistoryPage(store)
                page.resize(720, 500)
                page.show()
                self.application.processEvents()
                self.assertEqual(
                    page.scroll.frameShape(), QFrame.Shape.NoFrame
                )
                cards = page.findChildren(TranscriptCard)
                self.assertEqual(len(cards), 8)
                self.assertLessEqual(page.result_count.height(), 30)
                insert_actions = [
                    button for card in cards
                    for button in card.findChildren(QPushButton)
                    if button.accessibleName() == "Insert transcript at cursor"
                ]
                self.assertEqual(insert_actions, [])
                self.assertTrue(all(card.height() >= 100 for card in cards))
                self.assertTrue(
                    all(
                        card.body_label.height()
                        >= card.body_label.fontMetrics().height()
                        for card in cards
                    )
                )
                self.assertGreater(page.scroll.verticalScrollBar().maximum(), 0)

                cards[0].begin_edit()
                self.application.processEvents()
                self.assertGreaterEqual(cards[0].editor.height(), 120)
            finally:
                store.close()
                self.application.setStyleSheet(previous_stylesheet)

    def test_empty_message_is_centered_in_the_available_history_area(self):
        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.db")
            try:
                page = HistoryPage(store)
                page.resize(720, 500)
                page.show()
                self.application.processEvents()

                empty = page.holder.findChild(type(page.result_count), "mutedText")
                self.assertIsNotNone(empty)
                holder_midpoint = page.holder.height() / 2
                message_midpoint = empty.geometry().center().y()
                self.assertLess(abs(message_midpoint - holder_midpoint), 24)
            finally:
                store.close()
                self.application.setStyleSheet(previous_stylesheet)


if __name__ == "__main__":
    unittest.main()
