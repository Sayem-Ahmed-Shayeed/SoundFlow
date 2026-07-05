"""Full-text, editable transcript history page."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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
    DISPLAY_FONT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TITLE,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SPACE_8,
)
from soundflow.history.models import TranscriptEntry
from soundflow.history.store import HistoryStore


class TranscriptCard(QWidget):
    """Full transcript card with inline editing and visible common actions."""

    save_requested = Signal(int, str)
    delete_requested = Signal(int)
    insert_requested = Signal(str)
    export_requested = Signal(int)

    def __init__(self, entry: TranscriptEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.entry = entry
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_3)
        outer.setSpacing(SPACE_3)

        header = QHBoxLayout()
        heading = QLabel(entry.title)
        heading.setObjectName("headingText")
        heading.setFont(QFont(BODY_FONT, FONT_HEADING))
        heading.setWordWrap(True)
        normalized_title = entry.title.rstrip(".!? ").casefold()
        if normalized_title and entry.body.casefold().startswith(normalized_title):
            heading.hide()
        header.addWidget(heading, 1)
        words = len(entry.body.split())
        meta = QLabel(
            f"{entry.created_at.strftime('%I:%M %p').lstrip('0')}  ·  "
            f"{int(entry.duration_s // 60):02d}:{int(entry.duration_s % 60):02d}"
            f"  ·  {words} words"
        )
        meta.setObjectName("dimText")
        header.addWidget(meta, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)

        self.body_label = QLabel(entry.body)
        self.body_label.setObjectName("historyBody")
        self.body_label.setFont(QFont(BODY_FONT, FONT_BODY))
        self.body_label.setWordWrap(True)
        self.body_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        outer.addWidget(self.body_label)

        self.editor = QPlainTextEdit(entry.body)
        self.editor.setObjectName("historyEditor")
        self.editor.setMinimumHeight(120)
        self.editor.setMaximumHeight(360)
        self.editor.hide()
        outer.addWidget(self.editor)

        self.feedback = QLabel("")
        self.feedback.setObjectName("historyFeedback")
        self.feedback.hide()
        outer.addWidget(self.feedback)

        actions = QHBoxLayout()
        actions.setSpacing(SPACE_2)
        self.edit_button = self._button("✎  Edit", "Edit transcript")
        self.copy_button = self._button("Copy", "Copy transcript")
        self.insert_button = self._button("Insert", "Insert transcript at cursor")
        self.edit_button.clicked.connect(self.begin_edit)
        self.copy_button.clicked.connect(self.copy_text)
        self.insert_button.clicked.connect(
            lambda: self.insert_requested.emit(self.entry.body)
        )
        actions.addWidget(self.edit_button)
        actions.addWidget(self.copy_button)
        actions.addWidget(self.insert_button)
        actions.addStretch(1)

        self.save_button = self._button("Save", "Save transcript changes")
        self.save_button.setObjectName("accentButton")
        self.cancel_button = self._button("Cancel", "Cancel transcript editing")
        self.save_button.clicked.connect(self.save_edit)
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.save_button.hide()
        self.cancel_button.hide()
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.save_button)

        menu_button = self._button("⋯", "More transcript actions")
        menu_button.setFixedWidth(36)
        menu_button.clicked.connect(lambda: self._show_menu(menu_button))
        actions.addWidget(menu_button)
        outer.addLayout(actions)

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

    def begin_edit(self) -> None:
        self.feedback.hide()
        self.body_label.hide()
        self.editor.setPlainText(self.entry.body)
        self.editor.show()
        self.edit_button.hide()
        self.copy_button.setEnabled(False)
        self.insert_button.setEnabled(False)
        self.save_button.show()
        self.cancel_button.show()
        self.editor.setFocus()
        self.editor.selectAll()

    def cancel_edit(self) -> None:
        self.editor.hide()
        self.body_label.show()
        self.edit_button.show()
        self.copy_button.setEnabled(True)
        self.insert_button.setEnabled(True)
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
        QApplication.clipboard().setText(self.entry.body)
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

    insert_at_cursor = Signal(str)

    def __init__(self, store: HistoryStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._store = store

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_8, SPACE_4, SPACE_8, SPACE_6)
        outer.setSpacing(SPACE_4)
        title_row = QHBoxLayout()
        title = QLabel("History")
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        title.setObjectName("displayText")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self.result_count = QLabel()
        self.result_count.setObjectName("mutedText")
        title_row.addWidget(self.result_count)
        outer.addLayout(title_row)

        self.search = QLineEdit()
        self.search.setObjectName("historySearch")
        self.search.setPlaceholderText("Search transcripts…")
        self.search.setClearButtonEnabled(True)
        outer.addWidget(self.search)

        self.scroll = QScrollArea()
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
        self.search_timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.search_timer.start())
        focus_search = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_search.activated.connect(self.search.setFocus)
        self.refresh()

    def refresh(self) -> None:
        scroll_position = self.scroll.verticalScrollBar().value()
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        query = self.search.text().strip()
        entries = self._store.list_entries(query)
        self.result_count.setText(
            f"{len(entries)} transcript{'s' if len(entries) != 1 else ''}"
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
            self.cards.insertWidget(0, empty)
            return

        groups: dict[str, list[TranscriptEntry]] = {}
        for entry in entries:
            if entry.is_today():
                label = "Today"
            elif entry.is_yesterday():
                label = "Yesterday"
            else:
                label = entry.created_at.strftime("%B %d, %Y").replace(" 0", " ")
            groups.setdefault(label, []).append(entry)

        for label, group in groups.items():
            heading = QLabel(f"{label}  ·  {len(group)}")
            heading.setObjectName("historyGroup")
            heading.setFont(QFont(BODY_FONT, FONT_SMALL))
            self.cards.insertWidget(self.cards.count() - 1, heading)
            for entry in group:
                card = TranscriptCard(entry)
                card.save_requested.connect(
                    lambda entry_id, text, source=card:
                    self._save_entry(source, entry_id, text)
                )
                card.insert_requested.connect(self.insert_at_cursor)
                card.export_requested.connect(self._export_entry)
                card.delete_requested.connect(self._delete_entry)
                self.cards.insertWidget(self.cards.count() - 1, card)
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
        answer = QMessageBox.question(
            self,
            "Delete transcript?",
            f'Delete “{entry.title}”? This cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._store.delete(entry_id)
            self.refresh()

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


__all__ = ["HistoryPage", "TranscriptCard"]
