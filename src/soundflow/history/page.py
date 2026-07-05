"""History page — date-grouped transcript cards.

Layout:

* Header — ``History`` title.
* Search bar with a placeholder and a filter glyph on the right.
* Scroll area with day-grouped sections (Today / Yesterday / Earlier).
* Each card shows title, summary preview, timestamp + duration, and a
  ``\u22EE`` action menu that exposes Copy / Export / Delete / Insert.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from soundflow.core.export import ExportError, export_transcript
from soundflow.design import (
    BODY_FONT,
    DISPLAY_FONT,
    FG_MUTED,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TITLE,
    MONO_FONT,
    RADIUS_MD,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SPACE_8,
)
from soundflow.history.models import TranscriptEntry
from soundflow.history.store import HistoryStore


class _Card(QWidget):
    """Single transcript card with action menu."""

    delete_requested = Signal(int)
    copy_requested = Signal(str)
    insert_requested = Signal(str)
    export_requested = Signal(int)

    def __init__(self, entry: TranscriptEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyCard")
        self._entry = entry

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_3)
        layout.setSpacing(SPACE_4)

        # Left text column
        text = QVBoxLayout()
        text.setSpacing(SPACE_2)

        title = QLabel(entry.title)
        title.setObjectName("headingText")
        title.setFont(QFont(BODY_FONT, FONT_HEADING))
        text.addWidget(title)

        summary = QLabel(entry.summary)
        summary.setObjectName("mutedText")
        summary.setFont(QFont(BODY_FONT, FONT_SMALL))
        summary.setWordWrap(True)
        text.addWidget(summary)

        meta = QLabel(
            f"{entry.created_at.strftime('%I:%M %p').lstrip('0')} \u00B7 "
            f"{int(entry.duration_s // 60):02d}:{int(entry.duration_s % 60):02d}"
        )
        meta.setObjectName("dimText")
        meta.setFont(QFont(BODY_FONT, FONT_SMALL))
        text.addWidget(meta)

        layout.addLayout(text, 1)

        # Action menu button
        menu_btn = QPushButton("\u22EE")
        menu_btn.setObjectName("cardMenu")
        menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_btn.setFixedSize(28, 28)
        menu_btn.clicked.connect(lambda _checked=False: self._show_menu(menu_btn))
        layout.addWidget(menu_btn, 0, Qt.AlignmentFlag.AlignTop)

    def _show_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        copy_a = QAction("Copy", menu)
        copy_a.triggered.connect(lambda: self.copy_requested.emit(self._entry.body))
        export_a = QAction("Export\u2026", menu)
        export_a.triggered.connect(lambda: self.export_requested.emit(self._entry.id))
        insert_a = QAction("Insert at cursor", menu)
        insert_a.triggered.connect(lambda: self.insert_requested.emit(self._entry.body))
        menu.addAction(copy_a)
        menu.addAction(export_a)
        menu.addAction(insert_a)
        menu.addSeparator()
        delete_a = QAction("Delete", menu)
        delete_a.triggered.connect(lambda: self.delete_requested.emit(self._entry.id))
        menu.addAction(delete_a)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    @property
    def entry(self) -> TranscriptEntry:
        return self._entry


class HistoryPage(QWidget):
    """History page — search + date-grouped cards."""

    insert_at_cursor = Signal(str)

    def __init__(self, store: HistoryStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._store = store

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_8, SPACE_6, SPACE_8, SPACE_6)
        outer.setSpacing(SPACE_4)

        # Header
        header = QHBoxLayout()
        title = QLabel("History")
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        title.setObjectName("displayText")
        header.addWidget(title)
        header.addStretch(1)
        outer.addLayout(header)

        # Search
        search_row = QHBoxLayout()
        search_row.setSpacing(SPACE_2)
        self._search = QLineEdit()
        self._search.setObjectName("historySearch")
        self._search.setPlaceholderText("Search transcripts\u2026")
        self._search.textChanged.connect(self._refresh)
        self._search.setFont(QFont(BODY_FONT, FONT_BODY))
        search_row.addWidget(self._search, 1)

        filter_btn = QPushButton("\u2630")
        filter_btn.setObjectName("historyFilter")
        filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        filter_btn.setFixedWidth(36)
        search_row.addWidget(filter_btn)
        outer.addLayout(search_row)

        # Scroll area for the card list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("historyScroll")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._list_holder = QWidget()
        self._list_holder.setObjectName("historyListHolder")
        self._list_layout = QVBoxLayout(self._list_holder)
        self._list_layout.setContentsMargins(SPACE_2, SPACE_2, SPACE_2, SPACE_2)
        self._list_layout.setSpacing(SPACE_3)
        self._list_layout.addStretch(1)

        self._scroll.setWidget(self._list_holder)
        outer.addWidget(self._scroll, 1)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._refresh(self._search.text())

    def _refresh(self, query: str = "") -> None:
        # Clear layout (keep the final stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        entries = self._store.list_entries(query)
        if not entries:
            empty = QLabel("No transcripts yet.")
            empty.setObjectName("mutedText")
            empty.setFont(QFont(BODY_FONT, FONT_BODY))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, empty)
            return

        groups: dict[str, list[TranscriptEntry]] = {
            "Today": [], "Yesterday": [], "Earlier": [],
        }
        for e in entries:
            if e.is_today():
                groups["Today"].append(e)
            elif e.is_yesterday():
                groups["Yesterday"].append(e)
            else:
                groups["Earlier"].append(e)

        first = True
        for label, group in groups.items():
            if not group:
                continue
            heading = QLabel(label)
            heading.setObjectName("mutedText")
            heading.setFont(QFont(BODY_FONT, FONT_SMALL))
            self._list_layout.insertWidget(self._list_layout.count() - 1, heading)

            for e in group:
                card = _Card(e)
                card.copy_requested.connect(self._copy_to_clipboard)
                card.insert_requested.connect(self.insert_at_cursor)
                card.export_requested.connect(self._export_entry)
                card.delete_requested.connect(self._delete_entry)
                self._list_layout.insertWidget(self._list_layout.count() - 1, card)

    # ------------------------------------------------------------------
    def _copy_to_clipboard(self, body: str) -> None:
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(body)

    def _delete_entry(self, entry_id: int) -> None:
        self._store.delete(entry_id)
        self.refresh()

    def _export_entry(self, entry_id: int) -> None:
        entry = self._store.get(entry_id)
        if entry is None:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Export transcript", f"{entry.title}.txt",
            "Text (*.txt);;Markdown (*.md);;Word document (*.docx)",
        )
        if not path_str:
            return
        try:
            export_transcript(Path(path_str), entry.body)
        except ExportError as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export failed", str(exc))


__all__ = ["HistoryPage"]
