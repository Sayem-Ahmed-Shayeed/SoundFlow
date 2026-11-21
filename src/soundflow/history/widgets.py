"""Widgets for the History page: list rows, the transcript pane and its menu."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QFont,
    QFontMetrics,
    QKeySequence,
    QShortcut,
    QTextBlockFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import current_palette, icon, icon_size
from soundflow.design.fonts import tabular
from soundflow.history.models import TranscriptEntry

#: Body line height, as a percentage of the font's natural line (about 1.2em),
#: which makes the prototype's 1.55 line height.
LINE_HEIGHT_PERCENT = 130
#: Width of the transcript column: 34em at the 20px reading size.
TEXT_MAX_WIDTH = 680
#: Width the delete dialog's quote can use (dialog width less its padding).
QUOTE_WIDTH = 340


def format_duration(seconds: float) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def word_count(text: str) -> int:
    return len(text.split())


def day_label(created: datetime, today: date | None = None) -> str:
    """"Today", "Yesterday", or the calendar date."""
    today = today or date.today()
    day = created.date()
    if day == today:
        return "Today"
    if day == today - timedelta(days=1):
        return "Yesterday"
    return created.strftime("%B %d, %Y").replace(" 0", " ")


def clock_label(created: datetime) -> str:
    return created.strftime("%I:%M %p").lstrip("0")


def fit_lines(text: str, font: QFont, width: int, lines: int) -> str:
    """Shorten *text* with an ellipsis so it wraps to at most *lines* lines."""
    text = " ".join(text.split())
    if width <= 0:
        return text
    metrics = QFontMetrics(font)
    limit = metrics.lineSpacing() * lines + 1
    flags = int(Qt.TextFlag.TextWordWrap.value)

    def fits(candidate: str) -> bool:
        rect = metrics.boundingRect(QRect(0, 0, width, 100000), flags, candidate)
        return rect.height() <= limit

    if fits(text):
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if fits(text[:middle].rstrip() + "…"):
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + "…"


def _apply_line_height(document) -> None:
    cursor = QTextCursor(document)
    cursor.select(QTextCursor.SelectionType.Document)
    fmt = QTextBlockFormat()
    fmt.setLineHeight(
        LINE_HEIGHT_PERCENT,
        QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
    )
    cursor.mergeBlockFormat(fmt)
    document.markContentsDirty(0, document.characterCount())


def _fit_height(view: QTextBrowser) -> None:
    doc = view.document()
    if view.lineWrapMode() == QTextBrowser.LineWrapMode.FixedPixelWidth:
        doc.setTextWidth(view.lineWrapColumnOrWidth())
    # The proportional leading sits above each line, so the last line needs
    # the leading below it too, which the document size does not count.
    leading = int(view.fontMetrics().lineSpacing() * (LINE_HEIGHT_PERCENT / 100 - 1))
    height = int(doc.size().height()) + 2 * int(view.frameWidth()) + leading + 6
    view.setFixedHeight(max(height, view.fontMetrics().lineSpacing()))


def _keycap(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("keyCap")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class TranscriptItem(QFrame):
    """One row in the history list: meta line and a two-line preview."""

    activated = Signal(int)

    def __init__(
        self,
        entry: TranscriptEntry,
        truncated: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("historyItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setProperty("selected", False)
        self.entry_id = entry.id
        self.truncated = truncated
        self._source = entry.body
        self._fit_width = -1
        words = word_count(entry.body)
        self.setAccessibleName(f"Transcript at {clock_label(entry.created_at)}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(3)
        meta = QHBoxLayout()
        meta.setSpacing(12)
        for text in (
            clock_label(entry.created_at),
            format_duration(entry.duration_s),
            f"{words} word{'s' if words != 1 else ''}",
        ):
            label = QLabel(text)
            label.setObjectName("historyMeta")
            label.setFont(tabular(QFont(label.font())))
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            meta.addWidget(label)
        meta.addStretch(1)
        layout.addLayout(meta)

        self.preview = QLabel()
        self.preview.setObjectName("historyPreview")
        self.preview.setWordWrap(True)
        self.preview.setTextFormat(Qt.TextFormat.PlainText)
        self.preview.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.preview.setText(" ".join(self._source.split()))
        layout.addWidget(self.preview)

    def set_selected(self, selected: bool) -> None:
        if bool(self.property("selected")) == selected:
            return
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = self.layout().contentsRect().width()
        if width > 0 and width != self._fit_width:
            self._fit_width = width
            self.preview.setText(
                fit_lines(self._source, self.preview.font(), width, 2)
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.entry_id)
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.entry_id)
            return
        super().keyPressEvent(event)


class HistoryMenu(QFrame):
    """Small popup list of actions, anchored under a button."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("historyMenu")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(180)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(2)

    def add_item(
        self,
        text: str,
        glyph: str,
        slot: Callable[[], None],
        *,
        danger: bool = False,
    ) -> QPushButton:
        palette = current_palette()
        button = QPushButton(text)
        button.setObjectName("menuItem")
        button.setProperty("danger", danger)
        button.setIcon(icon(glyph, palette["danger" if danger else "text2"], 16))
        button.setIconSize(icon_size(16))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(text)

        def picked() -> None:
            self.hide()
            slot()

        button.clicked.connect(picked)
        self._layout.addWidget(button)
        return button

    def open_at(self, anchor: QWidget) -> None:
        self.adjustSize()
        origin = anchor.mapToGlobal(QPoint(anchor.width(), anchor.height() + 6))
        self.move(origin - QPoint(self.width(), 0))
        self.show()


class TranscriptDetail(QWidget):
    """The selected transcript: heading, actions, facts, text and inline editor."""

    save_requested = Signal(int, str)
    delete_requested = Signal(int)
    export_requested = Signal(int)
    polish_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyDetail")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._entry: TranscriptEntry | None = None
        self._editing = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # Page 0: nothing selected.
        empty_panel = QWidget()
        empty_panel.setObjectName("detailEmpty")
        empty_layout = QVBoxLayout(empty_panel)
        empty_layout.addStretch(1)
        self.empty_label = QLabel("Pick a transcript to read it in full.")
        self.empty_label.setObjectName("mutedText")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_label)
        empty_layout.addStretch(1)
        self.stack.addWidget(empty_panel)

        # Page 1: the transcript.
        self.scroll = QScrollArea()
        self.scroll.setObjectName("detailScroll")
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("detailContent")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body = QVBoxLayout(content)
        body.setContentsMargins(40, 8, 44, 28)
        body.setSpacing(0)
        self._body = body
        self._narrow: bool | None = None
        self.scroll.setWidget(content)
        self.stack.addWidget(self.scroll)

        head = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        head.setSpacing(16)
        self._head = head
        self.heading = QLabel()
        self.heading.setObjectName("tabTitle")
        self.heading.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.heading.setMinimumWidth(120)
        head.addWidget(self.heading, 1, Qt.AlignmentFlag.AlignTop)
        self.toolbar = QWidget()
        tools = QHBoxLayout(self.toolbar)
        tools.setContentsMargins(0, 0, 0, 0)
        tools.setSpacing(4)
        self.copy_button = self._tool("Copy", "copy", "Copy transcript")
        self.edit_button = self._tool("Edit", "edit", "Edit transcript")
        self.polish_button = self._tool("Polish", "sparkle", "Polish with AI")
        self.more_button = QPushButton()
        self.more_button.setObjectName("iconButton")
        self.more_button.setIcon(icon("more", current_palette()["text2"], 18))
        self.more_button.setIconSize(icon_size(18))
        self.more_button.setAccessibleName("More actions")
        self.more_button.setToolTip("More actions")
        self.more_button.setCursor(Qt.CursorShape.PointingHandCursor)
        for button in (self.copy_button, self.edit_button, self.polish_button, self.more_button):
            tools.addWidget(button)
        head.addWidget(self.toolbar, 0, Qt.AlignmentFlag.AlignTop)
        body.addLayout(head)

        self.facts = QWidget()
        facts = QHBoxLayout(self.facts)
        facts.setContentsMargins(0, 0, 0, 0)
        facts.setSpacing(32)
        self._fact_values: dict[str, QLabel] = {}
        for key, name in (("length", "Length"), ("words", "Words"), ("sync", "Sync")):
            cell = QWidget()
            column = QVBoxLayout(cell)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(2)
            value = QLabel()
            value.setObjectName("factValue")
            value.setFont(tabular(QFont(value.font())))
            caption = QLabel(name)
            caption.setObjectName("factLabel")
            column.addWidget(value)
            column.addWidget(caption)
            facts.addWidget(cell)
            self._fact_values[key] = value
        self._sync_caption = caption
        facts.addStretch(1)
        self.facts.setContentsMargins(0, 14, 0, 24)
        body.addWidget(self.facts)

        self.text_view = QTextBrowser()
        self.text_view.setObjectName("detailText")
        self.text_view.setReadOnly(True)
        self.text_view.setOpenExternalLinks(False)
        self.text_view.setUndoRedoEnabled(False)
        self.text_view.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.text_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_view.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.text_view.viewport().setAutoFillBackground(False)
        self.text_view.document().setDocumentMargin(0)
        # Wrap at the pane's width, never wider than the reading measure.
        self.text_view.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.text_view.setMaximumWidth(TEXT_MAX_WIDTH)
        self.text_view.document().documentLayout().documentSizeChanged.connect(
            lambda _size: _fit_height(self.text_view)
        )
        body.addWidget(self.text_view)

        # Inline editor, shown instead of the text while editing.
        self.edit_block = QWidget()
        edit = QVBoxLayout(self.edit_block)
        edit.setContentsMargins(0, 0, 0, 0)
        edit.setSpacing(8)
        label = QLabel("Edit transcript")
        label.setObjectName("fieldLabel")
        edit.addWidget(label)
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setTabChangesFocus(False)
        self.editor.setObjectName("historyEditor")
        self.editor.setAccessibleName("Edit transcript")
        self.editor.setMinimumHeight(210)
        self.editor.setFrameShape(QTextEdit.Shape.NoFrame)
        self.editor.document().setDocumentMargin(0)
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        edit.addWidget(self.editor)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.save_button = QPushButton("Save changes")
        self.save_button.setObjectName("primaryButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        bar.addWidget(self.save_button)
        bar.addWidget(self.cancel_button)
        bar.addSpacing(8)
        for widget in self._hint_widgets():
            bar.addWidget(widget)
        bar.addStretch(1)
        edit.addLayout(bar)
        body.addWidget(self.edit_block)
        self.edit_block.hide()

        self.feedback = QLabel("")
        self.feedback.setObjectName("historyFeedback")
        self.feedback.setProperty("state", "ok")
        self.feedback.hide()
        body.addWidget(self.feedback)
        body.addStretch(1)

        self.save_button.clicked.connect(self.save_edit)
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.copy_button.clicked.connect(self.copy_text)
        self.edit_button.clicked.connect(self.begin_edit)
        self.polish_button.clicked.connect(self._polish)
        self.more_button.clicked.connect(self._toggle_menu)

        self._menu = HistoryMenu(self)
        self._menu.add_item("Export as text", "export", self._export)
        self._menu.add_item("Delete transcript", "trash", self._delete, danger=True)

        save_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.editor)
        save_shortcut.activated.connect(self._save_from_keys)
        save_alt = QShortcut(QKeySequence("Ctrl+Enter"), self.editor)
        save_alt.activated.connect(self._save_from_keys)
        cancel_shortcut = QShortcut(QKeySequence("Escape"), self.editor)
        cancel_shortcut.activated.connect(self.cancel_edit)

        self.stack.setCurrentIndex(0)
        self.ensurePolished()

    # -- construction helpers -------------------------------------------
    # Below this pane width the toolbar drops its labels and moves under the
    # heading, so the pane fits the smallest window.
    NARROW_WIDTH = 560

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._adapt(self.width() < self.NARROW_WIDTH)

    def _adapt(self, narrow: bool) -> None:
        if narrow == self._narrow:
            return
        self._narrow = narrow
        self._body.setContentsMargins(*((24, 8, 24, 24) if narrow else (40, 8, 44, 28)))
        self._head.setDirection(
            QBoxLayout.Direction.TopToBottom if narrow else QBoxLayout.Direction.LeftToRight
        )
        self._head.setSpacing(8 if narrow else 16)
        self._head.setAlignment(self.toolbar, Qt.AlignmentFlag.AlignLeft if narrow else Qt.AlignmentFlag.AlignTop)
        for button in (self.copy_button, self.edit_button, self.polish_button):
            label = button.property("label")
            button.setText("" if narrow else label)

    def _tool(self, text: str, glyph: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("label", text)
        button.setObjectName("ghostButton")
        button.setIcon(icon(glyph, current_palette()["text2"], 16))
        button.setIconSize(icon_size(16))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        return button

    def _hint_widgets(self) -> list[QWidget]:
        widgets: list[QWidget] = []
        for text in ("Ctrl", "Enter"):
            widgets.append(_keycap(text))
        widgets.append(self._hint_text(" saves, "))
        widgets.append(_keycap("Esc"))
        widgets.append(self._hint_text(" cancels"))
        return widgets

    @staticmethod
    def _hint_text(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("historyEditorHint")
        return label

    # -- state -------------------------------------------------------------
    def entry_id(self) -> int | None:
        return self._entry.id if self._entry is not None else None

    def is_editing(self) -> bool:
        return self._editing

    def show_empty(self) -> None:
        self._entry = None
        self._editing = False
        self.stack.setCurrentIndex(0)

    def show_entry(self, entry: TranscriptEntry, sync: tuple[str, str]) -> None:
        """Show *entry* in read mode; *sync* is (value, caption) for the facts row."""
        self._entry = entry
        self._editing = False
        self.feedback.hide()
        self.heading.setText(f"{day_label(entry.created_at)}, {clock_label(entry.created_at)}")
        words = word_count(entry.body)
        self._fact_values["length"].setText(format_duration(entry.duration_s))
        self._fact_values["words"].setText(f"{words:,}")
        self._fact_values["sync"].setText(sync[0])
        self._sync_caption.setText(sync[1])
        self._set_text(self.text_view, entry.body)
        self.text_view.show()
        self.edit_block.hide()
        self.toolbar.show()
        self.polish_button.setEnabled(True)
        self.polish_button.setToolTip("Polish with AI")
        self.stack.setCurrentIndex(1)
        self.scroll.verticalScrollBar().setValue(0)

    def _set_text(self, view: QTextBrowser | QTextEdit, text: str) -> None:
        view.setPlainText(text)
        _apply_line_height(view.document())
        if isinstance(view, QTextBrowser):
            _fit_height(view)

    def show_error(self, message: str) -> None:
        self.feedback.setText(message)
        self.feedback.setProperty("state", "error")
        self._repolish(self.feedback)
        self.feedback.show()

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def set_polishing(self, busy: bool) -> None:
        self.polish_button.setEnabled(not busy)
        self.polish_button.setToolTip("Polishing…" if busy else "Polish with AI")

    # -- editing -----------------------------------------------------------
    def begin_edit(self) -> None:
        if self._entry is None:
            return
        self._menu.hide()
        self._editing = True
        self.feedback.hide()
        self.toolbar.hide()
        self.text_view.hide()
        self._set_text(self.editor, self._entry.body)
        self.edit_block.show()
        # Re-apply once visible: a document laid out while hidden can keep
        # its old line spacing.
        _apply_line_height(self.editor.document())
        self.editor.setFocus()
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    def cancel_edit(self) -> None:
        if not self._editing:
            return
        self._editing = False
        self.feedback.hide()
        self.edit_block.hide()
        self.toolbar.show()
        self.text_view.show()

    def save_edit(self) -> None:
        if not self._editing or self._entry is None:
            return
        text = self.editor.toPlainText().strip()
        if not text:
            self.show_error("Transcript text cannot be empty.")
            return
        self.save_requested.emit(self._entry.id, text)

    def _save_from_keys(self) -> None:
        if self._editing:
            self.save_edit()

    # -- actions -----------------------------------------------------------
    def copy_text(self) -> None:
        if self._entry is None:
            return
        text = self.editor.toPlainText() if self._editing else self._entry.body
        QApplication.clipboard().setText(text)
        self.copy_button.setText("Copied")
        self.copy_button.setIcon(icon("check", current_palette()["success"], 16))
        QTimer.singleShot(1200, self._reset_copy)

    def _reset_copy(self) -> None:
        self.copy_button.setText("Copy")
        self.copy_button.setIcon(icon("copy", current_palette()["text2"], 16))

    def _polish(self) -> None:
        if self._entry is not None:
            self.polish_requested.emit(self._entry.id)

    def _toggle_menu(self) -> None:
        if self._menu.isVisible():
            self._menu.hide()
            return
        if self._entry is None or self._editing:
            return
        self._menu.open_at(self.more_button)

    def _export(self) -> None:
        if self._entry is not None:
            self.export_requested.emit(self._entry.id)

    def _delete(self) -> None:
        if self._entry is not None:
            self.delete_requested.emit(self._entry.id)


__all__ = [
    "HistoryMenu",
    "TranscriptDetail",
    "TranscriptItem",
    "day_label",
    "fit_lines",
    "format_duration",
    "word_count",
]
