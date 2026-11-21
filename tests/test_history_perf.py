import gc
import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from soundflow.history.store import HistoryStore

try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QPushButton

    from soundflow.history.page import HistoryPage
    from soundflow.history.widgets import TranscriptItem

    HAS_QT = True
except ImportError:
    HAS_QT = False


class PreviewStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = HistoryStore(Path(self.directory.name) / "history.db")

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_previews_truncate_long_bodies(self):
        long_body = "word " * 500
        entry = self.store.add(long_body, 12.0)
        previews, truncated = self.store.list_previews()
        self.assertEqual(len(previews), 1)
        self.assertEqual(truncated, [True])
        self.assertLess(len(previews[0].body), len(long_body))
        self.assertTrue(previews[0].body.endswith("…"))
        full = self.store.get(entry.id)
        self.assertEqual(full.body, long_body.strip())

    def test_previews_keep_short_bodies_intact(self):
        self.store.add("short body here", 1.0)
        previews, truncated = self.store.list_previews()
        self.assertEqual(truncated, [False])
        self.assertEqual(previews[0].body, "short body here")

    def test_pagination_and_count(self):
        for index in range(25):
            self.store.add(f"transcript number {index}", 1.0)
        self.assertEqual(self.store.count(), 25)
        first, _ = self.store.list_previews(limit=20, offset=0)
        second, _ = self.store.list_previews(limit=20, offset=20)
        self.assertEqual(len(first), 20)
        self.assertEqual(len(second), 5)
        self.assertIn("24", first[0].body)
        self.assertEqual(self.store.count("number 3"), 1)

    def test_generation_bumps_on_mutation(self):
        start = self.store.generation
        entry = self.store.add("hello", 1.0)
        self.assertEqual(self.store.generation, start + 1)
        self.store.update(entry.id, "hello edited")
        self.assertEqual(self.store.generation, start + 2)
        self.store.delete(entry.id)
        self.assertEqual(self.store.generation, start + 3)

    def test_sync_state_reports_pending_for_new_rows(self):
        entry = self.store.add("sync me", 1.0)
        self.assertEqual(self.store.sync_state(entry.id), "pending")
        self.assertIsNone(self.store.sync_state(999999))


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class LazyPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
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

    def _items(self, page):
        found = []
        for index in range(page.cards.count()):
            widget = page.cards.itemAt(index).widget()
            if isinstance(widget, TranscriptItem):
                found.append(widget)
        return found

    def test_history_page_paginates_and_skips_redundant_refresh(self):
        for index in range(25):
            self.store.add(f"transcript number {index}", 1.0)
        page = HistoryPage(self.store)
        self._pages.append(page)
        self.application.processEvents()
        self.assertEqual(len(self._items(page)), 20)
        more = [
            button
            for button in page.holder.findChildren(QPushButton, "textActionButton")
            if "remaining" in button.text()
        ]
        self.assertEqual(len(more), 1)
        before = [page.cards.itemAt(i).widget() for i in range(page.cards.count())]
        page.refresh()
        after = [page.cards.itemAt(i).widget() for i in range(page.cards.count())]
        self.assertEqual(before, after)
        page.load_more()
        self.application.processEvents()
        self.assertEqual(len(self._items(page)), 25)

    def test_page_stays_fast_with_thousands_of_transcripts(self):
        for index in range(3000):
            self.store.add(f"transcript {index} with a short body of words", 2.0)
        started = time.perf_counter()
        page = HistoryPage(self.store)
        self._pages.append(page)
        self.application.processEvents()
        opened = time.perf_counter() - started
        self.assertEqual(len(self._items(page)), 20)
        self.assertLess(opened, 5.0)

        started = time.perf_counter()
        page.search.setText("transcript 2999")
        page.refresh(reset=True)
        self.application.processEvents()
        searched = time.perf_counter() - started
        self.assertEqual(len(self._items(page)), 1)
        self.assertLess(searched, 2.0)


if __name__ == "__main__":
    unittest.main()
