"""Unit tests for the persistent History store (no Qt)."""

import sys
import tempfile
import types
import unittest
from pathlib import Path


def _ensure_pyside6_stub() -> None:
    """Insert a minimal PySide6 stub so ``soundflow.history`` is importable."""
    if "PySide6" in sys.modules:
        return
    for mod in ("PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"):
        sys.modules.setdefault(mod, types.ModuleType(mod))
    sys.modules["PySide6.QtCore"].QObject = type("QObject", (), {})
    sys.modules["PySide6.QtCore"].Signal = lambda *a, **k: None
    sys.modules["PySide6.QtCore"].Slot = lambda *a, **k: lambda f: f
    sys.modules["PySide6.QtCore"].Qt = type("Qt", (), {})


_ensure_pyside6_stub()

from soundflow.history import HistoryStore  # noqa: E402
from soundflow.history.models import TranscriptEntry  # noqa: E402


class HistoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = HistoryStore(Path(self._tmp.name) / "history.db")
        self.addCleanup(self.store.close)

    def test_add_and_list(self) -> None:
        a = self.store.add("First entry. With two sentences.", duration_s=2.0)
        b = self.store.add("Second entry.", duration_s=1.0)
        items = self.store.list_entries()
        self.assertEqual(len(items), 2)
        # newest first by id desc
        self.assertEqual(items[0].id, b.id)
        self.assertEqual(items[1].id, a.id)
        # title is the first sentence
        self.assertTrue(a.title.startswith("First entry"))
        # summary is short enough
        self.assertLessEqual(len(a.summary), 200)

    def test_search(self) -> None:
        self.store.add("Hello world.")
        self.store.add("Goodbye world.")
        self.assertEqual(len(self.store.list_entries("Hello")), 1)
        self.assertEqual(len(self.store.list_entries("world")), 2)

    def test_delete(self) -> None:
        e = self.store.add("Disposable.")
        self.store.delete(e.id)
        self.assertEqual(len(self.store.list_entries()), 0)

    def test_update_rebuilds_title_summary_and_preserves_metadata(self) -> None:
        entry = self.store.add("Original body.", duration_s=7.5)
        updated = self.store.update(entry.id, "Edited full transcript. More detail.")
        self.assertEqual(updated.body, "Edited full transcript. More detail.")
        self.assertEqual(updated.duration_s, 7.5)
        self.assertEqual(updated.id, entry.id)
        self.assertTrue(updated.title.startswith("Edited full transcript"))
        self.assertEqual(self.store.get(entry.id).body, updated.body)

    def test_update_rejects_blank_and_missing_entries(self) -> None:
        entry = self.store.add("Keep me.")
        with self.assertRaises(ValueError):
            self.store.update(entry.id, "   ")
        with self.assertRaises(KeyError):
            self.store.update(9999, "Missing")

    def test_get_missing_returns_none(self) -> None:
        self.assertIsNone(self.store.get(9999))

    def test_title_fallback(self) -> None:
        e = self.store.add("")
        self.assertEqual(e.title, TranscriptEntry.make_title(""))


if __name__ == "__main__":
    unittest.main()
