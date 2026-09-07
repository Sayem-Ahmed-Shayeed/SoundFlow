"""Full-text, editable transcript history page."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from soundflow.core.export import ExportError, export_transcript
from soundflow.design import (
    BODY_FONT,
    CONTROL_HEIGHT_SM,
    DISPLAY_FONT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TITLE,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SPACE_8,
)
from soundflow.history.models import TranscriptEntry
from soundflow.history.store import HistoryStore


class DeleteTranscriptDialog(QDialog):
    """Compact, branded confirmation for a destructive history action."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("deleteTranscriptDialog")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(400)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        surface = QFrame()
        surface.setObjectName("deleteDialogSurface")
        surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content = QVBoxLayout(surface)
        content.setContentsMargins(SPACE_6, SPACE_6, SPACE_6, SPACE_6)
        content.setSpacing(SPACE_3)

        heading = QLabel("Delete transcript?")
        heading.setObjectName("deleteDialogTitle")
        content.addWidget(heading)

        message = QLabel(f'Delete “{title}”?')
        message.setObjectName("deleteDialogCopy")
        message.setTextFormat(Qt.TextFormat.PlainText)
        message.setWordWrap(True)
        content.addWidget(message)

        warning = QLabel("This action cannot be undone.")
        warning.setObjectName("deleteDialogWarning")
        content.addWidget(warning)

        actions = QHBoxLayout()
        actions.setSpacing(SPACE_2)
        actions.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("deleteDialogCancel")
        cancel.setDefault(True)
        cancel.setAutoDefault(True)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)

        delete = QPushButton("Delete")
        delete.setObjectName("destructiveButton")
        delete.setAutoDefault(False)
        delete.setCursor(Qt.CursorShape.PointingHandCursor)
        delete.clicked.connect(self.accept)
        actions.addWidget(delete)
        content.addLayout(actions)
        outer.addWidget(surface)


class TranscriptCard(QWidget):
    """Preview transcript card; full text loads on demand."""

    save_requested = Signal(int, str)
    delete_requested = Signal(int)
    export_requested = Signal(int)
    polish_requested = Signal(int)

    def __init__(
        self,
        entry: TranscriptEntry,
        truncated: bool = False,
        load_full: Callable[[int], str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("historyCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.entry = entry
        self._truncated = truncated
        self._load_full = load_full
        self._expanded = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_2, SPACE_3, SPACE_2, SPACE_3)
        outer.setSpacing(SPACE_2)

        row = QHBoxLayout()
        row.setSpacing(SPACE_4)

        meta_stack = QVBoxLayout()
        meta_stack.setSpacing(SPACE_1)
        time_label = QLabel(entry.created_at.strftime("%I:%M %p").lstrip("0"))
        time_label.setObjectName("headingText")
        time_label.setFont(QFont(BODY_FONT, FONT_BODY))
        meta_stack.addWidget(time_label)
        words = len(entry.body.split())
        meta = QLabel(
            f"{int(entry.duration_s // 60):02d}:{int(entry.duration_s % 60):02d}"
            f" · {words} words"
        )
        meta.setObjectName("dimText")
        meta_stack.addWidget(meta)
        meta_stack.addStretch(1)
        time_holder = QWidget()
        time_holder.setLayout(meta_stack)
        time_holder.setFixedWidth(150)
        row.addWidget(time_holder, 0, Qt.AlignmentFlag.AlignTop)

        middle = QVBoxLayout()
        middle.setSpacing(SPACE_2)

        self.body_label = QLabel(entry.body)
        self.body_label.setObjectName("historyBody")
        self.body_label.setFont(QFont(BODY_FONT, FONT_BODY))
        self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        middle.addWidget(self.body_label)

        self.expand_button = self._button("Show full transcript", "Show full transcript")
        self.expand_button.setObjectName("textActionButton")
        self.expand_button.clicked.connect(self.toggle_expand)
        self.expand_button.hide()
        middle.addWidget(self.expand_button, 0, Qt.AlignmentFlag.AlignLeft)
        self._sync_expand_button()

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("historyEditor")
        self.editor.setMinimumHeight(120)
        self.editor.setMaximumHeight(360)
        self.editor.hide()
        middle.addWidget(self.editor)

        self.feedback = QLabel("")
        self.feedback.setObjectName("historyFeedback")
        self.feedback.hide()
        middle.addWidget(self.feedback)
        row.addLayout(middle, 1)

        actions = QVBoxLayout()
        actions.setSpacing(SPACE_1)
        self.edit_button = self._button("✎", "Edit transcript")
        self.copy_button = self._button("⧉", "Copy transcript")
        self.polish_button = self._button("✨", "Polish with AI")
        self.edit_button.clicked.connect(self.begin_edit)
        self.copy_button.clicked.connect(self.copy_text)
        self.polish_button.clicked.connect(
            lambda: self.polish_requested.emit(self.entry.id)
        )
        actions.addWidget(self.edit_button, 0, Qt.AlignmentFlag.AlignTop)
        actions.addWidget(self.copy_button, 0, Qt.AlignmentFlag.AlignTop)
        actions.addWidget(self.polish_button, 0, Qt.AlignmentFlag.AlignTop)

        self.save_button = self._button("Save", "Save transcript changes")
        self.save_button.setObjectName("accentButton")
        self.cancel_button = self._button("Cancel", "Cancel transcript editing")
        self.save_button.clicked.connect(self.save_edit)
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.save_button.hide()
        self.cancel_button.hide()
        actions.addWidget(self.save_button, 0, Qt.AlignmentFlag.AlignTop)
        actions.addWidget(self.cancel_button, 0, Qt.AlignmentFlag.AlignTop)

        menu_button = self._button("⋯", "More transcript actions")
        menu_button.clicked.connect(lambda: self._show_menu(menu_button))
        actions.addWidget(menu_button, 0, Qt.AlignmentFlag.AlignTop)
        actions.addStretch(1)
        row.addLayout(actions)
        outer.addLayout(row)

        save_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.editor)
        save_shortcut.activated.connect(self.save_edit)
        cancel_shortcut = QShortcut(QKeySequence("Escape"), self.editor)
        cancel_shortcut.activated.connect(self.cancel_edit)

    def _button(self, text: str, accessible_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("historyAction")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(accessible_name)
        button.setToolTip(accessible_name)
        return button

    def _full_body(self) -> str:
        if self._load_full is not None:
            try:
                return self._load_full(self.entry.id)
            except (KeyError, OSError, ValueError):
                pass
        return self.entry.body

    def _sync_expand_button(self) -> None:
        if not self._truncated or self._expanded:
            self.expand_button.hide()
            return
        words = len(self.entry.body.split())
        self.expand_button.setText(f"Show full transcript · {words}+ words")
        self.expand_button.show()

    def toggle_expand(self) -> None:
        if self._expanded:
            self.body_label.setText(self.entry.body)
            self._expanded = False
            self._sync_expand_button()
            return
        full = self._full_body()
        self.body_label.setText(full)
        self._expanded = True
        self.expand_button.hide()

    def begin_edit(self) -> None:
        self.feedback.hide()
        self.body_label.hide()
        self.expand_button.hide()
        self.editor.setPlainText(self._full_body())
        self.editor.show()
        self.edit_button.hide()
        self.copy_button.setEnabled(True)
        self.save_button.show()
        self.cancel_button.show()
        self.editor.setFocus()
        self.editor.selectAll()

    def cancel_edit(self) -> None:
        self.editor.hide()
        self.body_label.show()
        self._sync_expand_button()
        self.edit_button.show()
        self.copy_button.setEnabled(True)
        self.save_button.hide()
        self.cancel_button.hide()
        self.feedback.hide()

    def save_edit(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            self.show_error("Transcript text cannot be empty.")
            return
        self.save_requested.emit(self.entry.id, text)

    def copy_text(self) -> None:
        if not self.editor.isHidden():
            text = self.editor.toPlainText()
        elif self._expanded:
            text = self._full_body()
        else:
            text = self.entry.body if not self._truncated else self._full_body()
        QApplication.clipboard().setText(text)
        self.copy_button.setText("Copied")
        QTimer.singleShot(1200, lambda: self.copy_button.setText("Copy"))

    def show_error(self, message: str) -> None:
        self.feedback.setText(message)
        self.feedback.setProperty("state", "error")
        self.feedback.show()

    def _show_menu(self, anchor: QWidget) -> None:
        menu = QMenu(self)
        export_action = QAction("Export…", menu)
        export_action.triggered.connect(
            lambda: self.export_requested.emit(self.entry.id)
        )
        delete_action = QAction("Delete…", menu)
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.entry.id)
        )
        menu.addAction(export_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))


class HistoryPage(QWidget):
    """Searchable, date-grouped, full-text transcript history."""

    def __init__(self, store: HistoryStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._store = store

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_8, SPACE_4, SPACE_8, SPACE_6)
        outer.setSpacing(SPACE_4)
        title_row = QHBoxLayout()
        title_copy = QVBoxLayout()
        title_copy.setSpacing(SPACE_2)
        title = QLabel("History")
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        title.setObjectName("displayText")
        title_copy.addWidget(title)
        subtitle = QLabel("Search, edit, copy, and reuse transcripts saved locally.")
        subtitle.setObjectName("mutedText")
        subtitle.setFont(QFont(BODY_FONT, FONT_SMALL))
        title_copy.addWidget(subtitle)
        title_row.addLayout(title_copy)
        title_row.addStretch(1)
        self.result_count = QLabel()
        self.result_count.setObjectName("resultCount")
        self.result_count.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        title_row.addWidget(
            self.result_count, 0, Qt.AlignmentFlag.AlignVCenter
        )
        outer.addLayout(title_row)

        search_row = QHBoxLayout()
        search_row.setSpacing(SPACE_3)
        self.search = QLineEdit()
        self.search.setObjectName("historySearch")
        self.search.setPlaceholderText("Search transcripts")
        self.search.setAccessibleName("Search transcripts")
        self.search.setClearButtonEnabled(True)
        search_row.addWidget(self.search, 1)
        self._filter = QComboBox()
        self._filter.setObjectName("historyFilter")
        self._filter.setAccessibleName("Filter transcripts by date")
        self._filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self._filter.addItem("All transcripts", "all")
        self._filter.addItem("Today", "today")
        self._filter.addItem("Yesterday", "yesterday")
        self._filter.addItem("This week", "week")
        self._filter.setFixedHeight(CONTROL_HEIGHT_SM)
        self._filter.currentIndexChanged.connect(lambda: self.refresh(reset=True))
        search_row.addWidget(self._filter)
        outer.addLayout(search_row)

        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("historyScroll")
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.holder = QWidget()
        self.holder.setObjectName("historyListHolder")
        self.cards = QVBoxLayout(self.holder)
        self.cards.setContentsMargins(0, 0, 0, 0)
        self.cards.setSpacing(SPACE_3)
        self.cards.addStretch(1)
        self.scroll.setWidget(self.holder)
        outer.addWidget(self.scroll, 1)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150)
        self.search_timer.timeout.connect(lambda: self.refresh(reset=True))
        self.search.textChanged.connect(lambda: self.search_timer.start())
        focus_search = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_search.activated.connect(self.search.setFocus)
        self._page_size = 20
        self._shown = 0
        self._generation = -1
        self._last_query: tuple[str, str] | None = None
        self.refresh(reset=True)

    def _load_full(self, entry_id: int) -> str:
        entry = self._store.get(entry_id)
        if entry is None:
            raise KeyError(entry_id)
        return entry.body

    def _filter_since(self) -> str | None:
        from datetime import date, timedelta

        mode = self._filter.currentData()
        today = date.today()
        if mode == "today":
            return today.isoformat()
        if mode == "yesterday":
            return (today - timedelta(days=1)).isoformat()
        if mode == "week":
            return (today - timedelta(days=6)).isoformat()
        return None

    def refresh(self, reset: bool = False) -> None:
        query = self.search.text().strip()
        key = (query, self._filter.currentData())
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
        self._shown = self._page_size if reset else self._shown + self._page_size
        self._shown = max(self._page_size, min(self._shown, max(total, 1)))
        entries, truncated = self._store.list_previews(
            query, limit=self._shown, offset=0, since=since
        )
        self._render(entries, truncated, total, scroll_position=None)

    def _render(
        self,
        entries: list[TranscriptEntry],
        truncated: list[bool],
        total: int,
        scroll_position: int | None,
    ) -> None:
        if scroll_position is None:
            scroll_position = self.scroll.verticalScrollBar().value()
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards.setStretch(0, 1)

        query = (self._last_query or ("", ""))[0]
        self.result_count.setText(
            f"{total} transcript{'s' if total != 1 else ''}"
        )
        if not entries:
            message = (
                "No matching transcripts. Clear search to see your history."
                if query
                else "No transcripts yet. Completed dictations will appear here."
            )
            empty = QLabel(message)
            empty.setObjectName("mutedText")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.cards.insertWidget(0, empty, 1)
            self.cards.setStretch(1, 0)
            return

        groups: dict[str, list[tuple[TranscriptEntry, bool]]] = {}
        for entry, cut in zip(entries, truncated):
            if entry.is_today():
                label = "Today"
            elif entry.is_yesterday():
                label = "Yesterday"
            else:
                label = entry.created_at.strftime("%B %d, %Y").replace(" 0", " ")
            groups.setdefault(label, []).append((entry, cut))

        for label, group in groups.items():
            heading = QLabel(f"{label.upper()} · {len(group)}")
            heading.setObjectName("historyGroup")
            heading.setFont(QFont(BODY_FONT, FONT_SMALL))
            self.cards.insertWidget(self.cards.count() - 1, heading)
            for entry, cut in group:
                card = TranscriptCard(entry, cut, self._load_full)
                card.save_requested.connect(
                    lambda entry_id, text, source=card:
                    self._save_entry(source, entry_id, text)
                )
                card.export_requested.connect(self._export_entry)
                card.delete_requested.connect(self._delete_entry)
                card.polish_requested.connect(self._polish_entry)
                self.cards.insertWidget(self.cards.count() - 1, card)
        if total > len(entries):
            more = QPushButton(
                f"Show more · {total - len(entries)} remaining"
            )
            more.setObjectName("textActionButton")
            more.setCursor(Qt.CursorShape.PointingHandCursor)
            more.clicked.connect(lambda: self.refresh(reset=False))
            self.cards.insertWidget(self.cards.count() - 1, more)
        QTimer.singleShot(
            0, lambda: self.scroll.verticalScrollBar().setValue(scroll_position)
        )

    def _save_entry(
        self, card: TranscriptCard, entry_id: int, text: str
    ) -> None:
        try:
            self._store.update(entry_id, text)
        except (KeyError, ValueError, OSError) as exc:
            card.show_error(str(exc))
            return
        self.refresh()

    def _delete_entry(self, entry_id: int) -> None:
        entry = self._store.get(entry_id)
        if entry is None:
            return
        dialog = DeleteTranscriptDialog(entry.title, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._store.delete(entry_id)
            self.refresh()

    def _polish_entry(self, entry_id: int) -> None:
        from soundflow.core.llm import LlmError, polish_in_background
        from soundflow.core.settings import SettingsStore

        settings = SettingsStore().load()
        if not settings.ai_cleanup_enabled:
            QMessageBox.information(
                self,
                "AI Polish is off",
                "Enable AI Polish in Preferences → AI Polish first.",
            )
            return
        entry = self._store.get(entry_id)
        if entry is None:
            return
        card = self._find_card(entry_id)
        if card is not None:
            card.polish_button.setEnabled(False)
            card.polish_button.setText("✨ Polishing…")

        def done(cleaned: str) -> None:
            try:
                self._store.update(entry_id, cleaned)
            except (KeyError, ValueError, OSError) as exc:
                if card is not None:
                    card.show_error(str(exc))
                return
            self.refresh()

        def failed(message: str) -> None:
            if card is not None:
                card.polish_button.setEnabled(True)
                card.polish_button.setText("✨ Polish")
                card.show_error(message)
            else:
                QMessageBox.warning(self, "AI Polish failed", message)

        polish_in_background(entry.body, settings, done, failed, parent=self)

    def _find_card(self, entry_id: int) -> TranscriptCard | None:
        for index in range(self.cards.count()):
            widget = self.cards.itemAt(index).widget()
            if isinstance(widget, TranscriptCard) and widget.entry.id == entry_id:
                return widget
        return None

    def _export_entry(self, entry_id: int) -> None:
        entry = self._store.get(entry_id)
        if entry is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export transcript",
            f"{entry.title}.txt",
            "Text (*.txt);;Markdown (*.md);;Word document (*.docx)",
        )
        if not path:
            return
        try:
            export_transcript(Path(path), entry.body)
        except ExportError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))


__all__ = ["DeleteTranscriptDialog", "HistoryPage", "TranscriptCard"]
