import gc
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLabel

    from soundflow.design import register_application_fonts, stylesheet
    from soundflow.history.page import HistoryPage
    from soundflow.history.store import HistoryStore
    from soundflow.history.widgets import TranscriptItem

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class HistoryGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        register_application_fonts()

    def setUp(self):
        self.previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(stylesheet(True))
        self._directory = tempfile.TemporaryDirectory()
        self.store = HistoryStore(Path(self._directory.name) / "history.db")
        self._pages = []

    def tearDown(self):
        for page in self._pages:
            page.close()
            page.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self._pages = []
        gc.collect()
        self.store.close()
        self._directory.cleanup()
        self.application.setStyleSheet(self.previous_stylesheet)

    def _page(self, width=1180, height=700):
        page = HistoryPage(self.store)
        self._pages.append(page)
        page.resize(width, height)
        page.show()
        for _ in range(4):
            self.application.processEvents()
        return page

    def _items(self, page):
        return [
            page.cards.itemAt(index).widget()
            for index in range(page.cards.count())
            if isinstance(page.cards.itemAt(index).widget(), TranscriptItem)
        ]

    def test_long_transcript_is_not_clipped_in_the_detail_pane(self):
        body = " ".join(f"Complete sentence number {i} with a few words." for i in range(60))
        self.store.add(body, 120.0)
        for width, height in ((720, 500), (1180, 700)):
            page = self._page(width, height)
            view = page.detail.text_view
            document = view.document()
            self.assertGreaterEqual(view.height(), int(document.size().height()))
            self.assertLessEqual(view.width(), 680)  # the reading measure
            # The text wraps inside the pane rather than running off its edge.
            pane = page.detail.scroll.viewport()
            right = view.mapTo(pane, view.rect().topRight()).x()
            self.assertLessEqual(right, pane.width())
            self.assertLessEqual(document.idealWidth(), view.viewport().width() + 1)
            page.close()

    def test_list_column_is_fixed_width_and_rows_fit_their_previews(self):
        for index in range(8):
            self.store.add(f"Transcript {index} " + ("with complete preview text " * 12), 12.0)
        page = self._page()
        self.assertEqual(page.findChild(object, "historyList").width(), 356)
        items = self._items(page)
        self.assertEqual(len(items), 8)
        for item in items:
            preview = item.preview
            self.assertLessEqual(preview.sizeHint().height(), item.height())
            self.assertTrue(preview.text().endswith("…"))

    def test_bangla_transcript_renders_in_list_and_detail(self):
        bangla = "আজকের মিটিংয়ে আমরা নতুন ডেমো নিয়ে কথা বলব। সবাই যেন সময়মতো আসে।"
        entry = self.store.add(bangla, 5.0)
        page = self._page()
        items = self._items(page)
        self.assertEqual(items[0].entry_id, entry.id)
        self.assertTrue(items[0].preview.text())
        self.assertEqual(page.detail.text_view.toPlainText(), bangla)

    def test_empty_history_message_sits_at_the_top_of_the_list(self):
        page = self._page()
        empty = page.findChild(QLabel, "emptyTitle")
        self.assertIsNotNone(empty)
        panel = empty.parentWidget()
        top = panel.mapTo(page, panel.rect().topLeft())
        self.assertLess(top.y(), page.height() // 3)
        self.assertGreaterEqual(top.x(), 0)
        self.assertLessEqual(panel.mapTo(page, panel.rect().bottomRight()).x(), 356)


if __name__ == "__main__":
    unittest.main()
