"""Persistent transcript history.

* :class:`TranscriptEntry` — single dictation session.
* :class:`HistoryStore` — SQLite-backed storage at
  ``$XDG_DATA_HOME/soundflow/history.db``.
* :class:`HistoryPage` — Qt page that lists entries grouped by date.

:class:`HistoryPage` is imported lazily to allow the store to be used in
environments without PySide6 (e.g. unit tests).
"""

from soundflow.history.models import TranscriptEntry
from soundflow.history.store import HistoryStore

__all__ = ["HistoryPage", "HistoryStore", "TranscriptEntry"]


def __getattr__(name: str):  # PEP 562 lazy attribute
    if name == "HistoryPage":
        from soundflow.history.page import HistoryPage
        return HistoryPage
    raise AttributeError(f"module 'soundflow.history' has no attribute {name!r}")