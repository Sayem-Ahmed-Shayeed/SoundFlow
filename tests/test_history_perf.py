import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from soundflow.history.models import TranscriptEntry
from soundflow.history.store import HistoryStore

try:
    from PySide6.QtWidgets import QApplication

    from soundflow.history.page import HistoryPage, TranscriptCard

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


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class LazyCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_editor_starts_empty_and_loads_on_edit(self):
        entry = TranscriptEntry(
            id=7,
            created_at=__import__("datetime").datetime.now(),
            duration_s=3.0,
            title="t",
            summary="s",
            body="preview…",
        )
        loaded = []
        card = TranscriptCard(
            entry, True, lambda entry_id: loaded.append(entry_id) or "FULL BODY", None
        )
        self.assertEqual(card.editor.toPlainText(), "")
        card.begin_edit()
        self.assertEqual(card.editor.toPlainText(), "FULL BODY")
        self.assertEqual(loaded, [7])

    def test_expand_loads_full_body(self):
        entry = TranscriptEntry(
            id=8,
            created_at=__import__("datetime").datetime.now(),
            duration_s=3.0,
            title="t",
            summary="s",
            body="preview…",
        )
        card = TranscriptCard(entry, True, lambda entry_id: "FULL BODY", None)
        self.assertFalse(card.expand_button.isHidden())
        card.toggle_expand()
        self.assertEqual(card.body_label.text(), "FULL BODY")
        self.assertTrue(card.expand_button.isHidden())

    def test_history_page_paginates_and_skips_redundant_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.db")
            try:
                for index in range(25):
                    store.add(f"transcript number {index}", 1.0)
                page = HistoryPage(store)
                self.application.processEvents()
                cards = [
                    page.cards.itemAt(i).widget()
                    for i in range(page.cards.count())
                ]
                cards = [w for w in cards if isinstance(w, TranscriptCard)]
                self.assertEqual(len(cards), 20)
                self.assertIn("remaining", page.cards.itemAt(
                    page.cards.count() - 2).widget().text())
                before = [page.cards.itemAt(i).widget() for i in range(page.cards.count())]
                page.refresh()
                after = [page.cards.itemAt(i).widget() for i in range(page.cards.count())]
                self.assertEqual(before, after)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
