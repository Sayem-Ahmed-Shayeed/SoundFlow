"""Full-text, editable transcript history page."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from soundflow.core.export import ExportError, export_transcript
from soundflow.design import current_palette, icon
from soundflow.design.fonts import tabular
from soundflow.history.models import TranscriptEntry
from soundflow.history.store import HistoryStore
from soundflow.history.widgets import (
    QUOTE_WIDTH,
    TranscriptDetail,
    TranscriptItem,
    day_label,
    fit_lines,
)
from soundflow.ui.widgets.message_dialog import ask, inform
from soundflow.ui.widgets.segmented import SegmentedControl

FILTERS: tuple[tuple[str, str], ...] = (
    ("all", "All"),
    ("today", "Today"),
    ("yesterday", "Yesterday"),
    ("week", "This week"),
)


class DeleteTranscriptDialog(QDialog):
    """Compact, branded confirmation for a destructive history action."""

    def __init__(self, text: str, synced: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("deleteTranscriptDialog")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(404)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        surface = QFrame()
        surface.setObjectName("deleteDialogSurface")
        surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content = QVBoxLayout(surface)
        content.setContentsMargins(22, 22, 22, 18)
        content.setSpacing(0)

        heading = QLabel("Delete this transcript?")
        heading.setObjectName("deleteDialogTitle")
        content.addWidget(heading)
        content.addSpacing(6)

        if synced:
            copy_text = (
                "It's removed from this computer and from your other computers. "
                "You can't undo this."
            )
        else:
            copy_text = "It's removed from this computer. You can't undo this."
        message = QLabel(copy_text)
        message.setObjectName("deleteDialogCopy")
        message.setWordWrap(True)
        content.addWidget(message)
        content.addSpacing(18)

        self.quote = QLabel()
        self.quote.setObjectName("deleteDialogQuote")
        self.quote.setWordWrap(True)
        self.quote.setTextFormat(Qt.TextFormat.PlainText)
        self.ensurePolished()
        self.quote.setText(fit_lines(text, self.quote.font(), QUOTE_WIDTH, 2))
        content.addWidget(self.quote)
        content.addSpacing(18)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)
        cancel = QPushButton("Keep it")
        cancel.setObjectName("deleteDialogCancel")
        cancel.setDefault(True)
        cancel.setAutoDefault(True)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)

        delete = QPushButton("Delete transcript")
        delete.setObjectName("destructiveButton")
        delete.setAutoDefault(False)
        delete.setCursor(Qt.CursorShape.PointingHandCursor)
        delete.clicked.connect(self.accept)
        actions.addWidget(delete)
        content.addLayout(actions)
        outer.addWidget(surface)


class HistoryPage(QWidget):
    """Searchable, date-grouped, full-text transcript history with a detail pane."""

    ai_polish_settings_requested = Signal()

    def __init__(self, store: HistoryStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._store = store
        self._selected_id: int | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        column = QWidget()
        column.setObjectName("historyList")
        column.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        column.setFixedWidth(356)
        side = QVBoxLayout(column)
        side.setContentsMargins(22, 6, 18, 12)
        side.setSpacing(12)

        title = QLabel("History")
        title.setObjectName("pageTitle")
        side.addWidget(title)

        self.search = QLineEdit()
        self.search.setObjectName("historySearch")
        self.search.setPlaceholderText("Search transcripts")
        self.search.setAccessibleName("Search transcripts")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(
            icon("search", current_palette()["text3"], 16),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        side.addWidget(self.search)

        self._filter = SegmentedControl(FILTERS, "all", accessible_name="Show")
        self._filter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for value, _label in FILTERS:
            self._filter.button(value).setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        side.addWidget(self._filter)

        self.result_count = QLabel()
        self.result_count.setObjectName("resultCount")
        self.result_count.setFont(tabular(self.result_count.font()))
        self.result_count.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        side.addWidget(self.result_count)

        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("historyScroll")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.holder = QWidget()
        self.holder.setObjectName("historyListHolder")
        self.cards = QVBoxLayout(self.holder)
        self.cards.setContentsMargins(0, 0, 0, 0)
        self.cards.setSpacing(0)
        self.cards.addStretch(1)
        self.scroll.setWidget(self.holder)
        side.addWidget(self.scroll, 1)
        root.addWidget(column)

        self.detail = TranscriptDetail(self)
        self.detail.save_requested.connect(self._save_entry)
        self.detail.delete_requested.connect(self._delete_entry)
        self.detail.export_requested.connect(self._export_entry)
        self.detail.polish_requested.connect(self._polish_entry)
        root.addWidget(self.detail, 1)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150)
        self.search_timer.timeout.connect(lambda: self.refresh(reset=True))
        self.search.textChanged.connect(lambda: self.search_timer.start())
        self._filter.changed.connect(lambda _value: self.refresh(reset=True))
        focus_search = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_search.activated.connect(self.search.setFocus)
        self._page_size = 20
        self._shown = 0
        self._generation = -1
        self._last_query: tuple[str, str] | None = None
        self.refresh(reset=True)

    # -- data ----------------------------------------------------------------
    def _filter_since(self) -> str | None:
        mode = self._filter.value()
        today = date.today()
        if mode == "today":
            return today.isoformat()
        if mode == "yesterday":
            return (today - timedelta(days=1)).isoformat()
        if mode == "week":
            return (today - timedelta(days=6)).isoformat()
        return None

    def _sync_facts(self, entry_id: int) -> tuple[str, str]:
        if self._store.user_id is None:
            return ("Local only", "Sync is off")
        if self._store.sync_state(entry_id) == "synced":
            return ("Synced", "Saved to your account")
        return ("Waiting", "Uploads at the next sync")

    def _is_synced(self, entry_id: int) -> bool:
        return self._store.user_id is not None and self._store.sync_state(entry_id) == "synced"

    def refresh(self, reset: bool = False) -> None:
        query = self.search.text().strip()
        key = (query, self._filter.value())
        if (
            not reset
            and key == self._last_query
            and self._generation == self._store.generation
            and self._shown > 0
        ):
            return
        if reset or key != self._last_query:
            self._shown = 0
        self._last_query = key
        self._generation = self._store.generation
        since = self._filter_since()
        total = self._store.count(query, since=since)
        # Keep however many rows were already shown; only "Show more" grows it.
        self._shown = max(self._page_size, min(self._shown or self._page_size, max(total, 1)))
        entries, truncated = self._store.list_previews(
            query, limit=self._shown, offset=0, since=since
        )
        self._render(entries, truncated, total, scroll_position=None)

    def select_entry(self, entry_id: int) -> None:
        """Show one transcript, e.g. picked from Recent on the Dictation page."""
        if self.search.text() or self._filter.value() != "all":
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
            self._filter.set_value("all")
        self._selected_id = entry_id
        self.refresh(reset=True)
        if any(item.entry_id == entry_id for item in self._items()):
            self._select(entry_id)

    def load_more(self) -> None:
        """Show the next page of transcripts below the current ones."""
        self._shown += self._page_size
        self._generation = -1  # force a re-query with the larger page
        self.refresh()

    # -- list ----------------------------------------------------------------
    def _items(self) -> list[TranscriptItem]:
        found = []
        for index in range(self.cards.count()):
            widget = self.cards.itemAt(index).widget()
            if isinstance(widget, TranscriptItem):
                found.append(widget)
        return found

    def _clear_list(self) -> None:
        while self.cards.count():
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Detach now so the stale row cannot paint before deleteLater runs.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _render(
        self,
        entries: list[TranscriptEntry],
        truncated: list[bool],
        total: int,
        scroll_position: int | None,
    ) -> None:
        if scroll_position is None:
            scroll_position = self.scroll.verticalScrollBar().value()
        self._clear_list()

        query = (self._last_query or ("", ""))[0]
        self.result_count.setText(f"{total:,} transcript{'s' if total != 1 else ''}")
        if not entries:
            self.cards.addWidget(self._empty_state(query))
            self.cards.addStretch(1)
            self._select(None)
            return

        ids = [entry.id for entry in entries]
        if self._selected_id not in ids:
            self._selected_id = ids[0]

        groups: dict[str, list[tuple[TranscriptEntry, bool]]] = {}
        today = date.today()
        for entry, cut in zip(entries, truncated):
            groups.setdefault(day_label(entry.created_at, today), []).append((entry, cut))

        for label, group in groups.items():
            heading = QLabel(label)
            heading.setObjectName("historyGroup")
            heading.setContentsMargins(12, 14, 0, 2)
            self.cards.addWidget(heading)
            for entry, cut in group:
                item = TranscriptItem(entry, cut, self.holder)
                item.activated.connect(self._select)
                self.cards.addWidget(item)
        if total > len(entries):
            more = QPushButton(f"Show more ({total - len(entries)} remaining)")
            more.setObjectName("textActionButton")
            more.setCursor(Qt.CursorShape.PointingHandCursor)
            more.clicked.connect(self.load_more)
            self.cards.addWidget(more)
        self.cards.addStretch(1)
        self._select(self._selected_id)
        QTimer.singleShot(
            0, lambda: self.scroll.verticalScrollBar().setValue(scroll_position)
        )

    def _empty_state(self, query: str) -> QWidget:
        panel = QWidget()
        panel.setObjectName("historyEmpty")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 28, 12, 0)
        layout.setSpacing(0)
        title = QLabel()
        title.setObjectName("emptyTitle")
        title.setWordWrap(True)
        body = QLabel()
        body.setObjectName("emptyBody")
        body.setWordWrap(True)
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(body)
        if query:
            title.setText(f"No transcripts match “{query}”")
            body.setText("Try fewer words, or search all dates.")
            clear = QPushButton("Clear search")
            clear.setCursor(Qt.CursorShape.PointingHandCursor)
            clear.clicked.connect(lambda: self.search.clear())
            layout.addSpacing(12)
            layout.addWidget(clear, 0, Qt.AlignmentFlag.AlignLeft)
        elif self._filter.value() != "all":
            title.setText("No transcripts here")
            body.setText("Choose All to see the rest of your history.")
        else:
            title.setText("No dictations yet")
            body.setText("Hold Ctrl Alt Space in any app and start speaking.")
        return panel

    def _select(self, entry_id: int | None) -> None:
        """Mark *entry_id* as the selected row and show it in the detail pane."""
        self._selected_id = entry_id
        for item in self._items():
            item.set_selected(item.entry_id == entry_id)
        if entry_id is None:
            self.detail.show_empty()
            return
        if self.detail.is_editing() and self.detail.entry_id() == entry_id:
            return  # keep an edit in progress when the list refreshes
        entry = self._store.get(entry_id)
        if entry is None:
            self._selected_id = None
            self.detail.show_empty()
            return
        self.detail.show_entry(entry, self._sync_facts(entry_id))

    # -- actions -------------------------------------------------------------
    def _save_entry(self, entry_id: int, text: str) -> None:
        try:
            self._store.update(entry_id, text)
        except (KeyError, ValueError, OSError) as exc:
            self.detail.show_error(str(exc))
            return
        self.detail.cancel_edit()
        self.refresh()

    def _delete_entry(self, entry_id: int) -> None:
        entry = self._store.get(entry_id)
        if entry is None:
            return
        dialog = DeleteTranscriptDialog(entry.body, self._is_synced(entry_id), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._store.delete(entry_id)
            self._selected_id = None
            self.refresh()

    def _polish_entry(self, entry_id: int) -> None:
        from soundflow.core.llm import polish_in_background
        from soundflow.core.settings import SettingsStore

        settings = SettingsStore().load()
        if not settings.ai_cleanup_enabled:
            if ask(
                self,
                "AI Polish is off",
                "Turn it on and add a model in Preferences, then polish this transcript again.",
                accept_text="Open AI Polish",
                reject_text="Not now",
                kind="info",
            ):
                self.ai_polish_settings_requested.emit()
            return
        entry = self._store.get(entry_id)
        if entry is None:
            return
        if self.detail.entry_id() == entry_id:
            self.detail.set_polishing(True)

        def done(cleaned: str) -> None:
            self.detail.set_polishing(False)
            try:
                self._store.update(entry_id, cleaned)
            except (KeyError, ValueError, OSError) as exc:
                if self.detail.entry_id() == entry_id:
                    self.detail.show_error(str(exc))
                return
            self.refresh(reset=False)

        def failed(message: str) -> None:
            self.detail.set_polishing(False)
            if self.detail.entry_id() == entry_id:
                self.detail.show_error(message)
            else:
                inform(self, "AI Polish failed", message, kind="error")

        polish_in_background(entry.body, settings, done, failed, parent=self)

    def _export_entry(self, entry_id: int) -> None:
        entry = self._store.get(entry_id)
        if entry is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export transcript",
            f"{_safe_filename(entry.title)}.txt",
            "Text (*.txt);;Markdown (*.md);;Word document (*.docx)",
        )
        if not path:
            return
        try:
            export_transcript(Path(path), entry.body)
        except (ExportError, OSError) as exc:
            inform(self, "Export failed", str(exc), kind="error")


def _safe_filename(title: str) -> str:
    """A file name from a transcript title (Bangla and other scripts kept)."""
    cleaned = "".join("-" if ch in '/\\:*?"<>|' else ch for ch in title).strip(" .")
    return cleaned[:80] or "Transcript"


__all__ = ["DeleteTranscriptDialog", "HistoryPage", "TranscriptDetail", "TranscriptItem"]
