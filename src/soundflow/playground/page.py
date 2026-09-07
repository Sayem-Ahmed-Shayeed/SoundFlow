"""Playground page — command input + quick-action cards."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

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
from soundflow.injector import TextInjector
from soundflow.playground.actions import format_text, smart_rewrite


class _QuickCard(QPushButton):
    """Quick-action card. Shows an icon glyph, title, and short hint."""

    def __init__(
        self,
        icon: str,
        title: str,
        hint: str,
        enabled: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("quickActionCard")
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ForbiddenCursor
        )
        self.setEnabled(enabled)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(52)
        self.setMinimumWidth(160)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(SPACE_2)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont(BODY_FONT, 18))
        icon_lbl.setObjectName("quickActionIcon")
        layout.addWidget(icon_lbl)

        copy = QVBoxLayout()
        copy.setSpacing(1)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont(BODY_FONT, FONT_HEADING))
        title_lbl.setObjectName("headingText")
        copy.addWidget(title_lbl)

        hint_lbl = QLabel(hint)
        hint_lbl.setFont(QFont(BODY_FONT, FONT_SMALL))
        hint_lbl.setObjectName("mutedText")
        copy.addWidget(hint_lbl)
        layout.addLayout(copy, 1)


class PlaygroundPage(QWidget):
    """Playground page."""

    insert_requested = Signal(str)
    transformation_failed = Signal(str)

    def __init__(
        self,
        injector: TextInjector | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("playgroundPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._injector = injector

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_8, SPACE_4, SPACE_8, SPACE_6)
        outer.setSpacing(SPACE_4)

        # Header
        header = QVBoxLayout()
        header.setSpacing(SPACE_2)
        title = QLabel("Playground")
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        title.setObjectName("displayText")
        header.addWidget(title)

        subtitle = QLabel(
            "Practice Soundflow commands before using them in other applications."
        )
        subtitle.setFont(QFont(BODY_FONT, FONT_BODY))
        subtitle.setObjectName("mutedText")
        header.addWidget(subtitle)
        outer.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(SPACE_8)

        left = QVBoxLayout()
        left.setSpacing(SPACE_3)

        left_head = QLabel("Try a command")
        left_head.setFont(QFont(BODY_FONT, FONT_HEADING))
        left_head.setObjectName("headingText")
        left.addWidget(left_head)
        left_sub = QLabel("Choose a template or write your own instruction.")
        left_sub.setFont(QFont(BODY_FONT, FONT_SMALL))
        left_sub.setObjectName("mutedText")
        left.addWidget(left_sub)

        # Quick actions row
        cards = QHBoxLayout()
        cards.setSpacing(SPACE_3)

        self._insert_card = _QuickCard(
            "\u2702", "Insert Text", "Put clean text at the cursor.", enabled=True
        )
        self._insert_card.clicked.connect(self._run_insert)
        cards.addWidget(self._insert_card)

        self._format_card = _QuickCard(
            "A", "Format Text", "Transform text into a clearer structure.",
            enabled=True,
        )
        self._format_card.clicked.connect(self._run_format)
        cards.addWidget(self._format_card)

        self._rewrite_card = _QuickCard(
            "\u2728", "Smart Rewrite", "Improve clarity while preserving meaning.",
            enabled=True,
        )
        self._rewrite_card.clicked.connect(self._run_smart_rewrite)
        cards.addWidget(self._rewrite_card)
        left.addLayout(cards)

        input_label = QLabel("Input")
        input_label.setFont(QFont(BODY_FONT, FONT_SMALL))
        input_label.setObjectName("mutedText")
        left.addWidget(input_label)

        # Command input
        self._command = QPlainTextEdit()
        self._command.setObjectName("playgroundCommand")
        self._command.setPlaceholderText(
            "Paste or dictate text to rewrite…"
        )
        self._command.setFont(QFont(BODY_FONT, FONT_BODY))
        self._command.setMinimumHeight(132)
        self._command.setMaximumHeight(220)
        self._command.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        left.addWidget(self._command)

        # Ctrl+Enter submits
        submit = QShortcut(QKeySequence("Ctrl+Return"), self._command)
        submit.activated.connect(self._on_submit)

        run_row = QHBoxLayout()
        run_row.setSpacing(SPACE_3)
        local_note = QLabel("Runs locally unless AI Polish is explicitly used.")
        local_note.setFont(QFont(BODY_FONT, FONT_SMALL))
        local_note.setObjectName("mutedText")
        run_row.addWidget(local_note, 1)
        self._run_button = QPushButton("Run command  →")
        self._run_button.setObjectName("primaryButton")
        self._run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_button.clicked.connect(self._on_submit)
        run_row.addWidget(self._run_button)
        left.addLayout(run_row)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(SPACE_3)
        right_head = QLabel("Preview")
        right_head.setFont(QFont(BODY_FONT, FONT_HEADING))
        right_head.setObjectName("headingText")
        right.addWidget(right_head)
        right_sub = QLabel("See the result before using it elsewhere.")
        right_sub.setFont(QFont(BODY_FONT, FONT_SMALL))
        right_sub.setObjectName("mutedText")
        right.addWidget(right_sub)
        self._preview = QLabel("Your result will appear here.")
        self._preview.setObjectName("playgroundPreview")
        self._preview.setFont(QFont(BODY_FONT, FONT_BODY))
        self._preview.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._preview.setWordWrap(True)
        right.addWidget(self._preview, 1)
        columns.addLayout(right, 2)

        outer.addLayout(columns, 1)

    # ------------------------------------------------------------------
    def _on_submit(self) -> None:
        text = self._command.toPlainText().strip()
        if not text:
            return
        self._command.clear()
        self._run_insert_with(text)

    def _run_insert(self) -> None:
        self._run_insert_with(self._command.toPlainText())

    def _run_insert_with(self, text: str) -> None:
        text = text.strip()
        if text:
            self.insert_requested.emit(text)

    def _run_smart_rewrite(self) -> None:
        self._run_transform(smart_rewrite)

    def _run_format(self) -> None:
        self._run_transform(format_text)

    def _run_transform(self, transform) -> None:
        original = self._command.toPlainText()

        def run() -> None:
            try:
                result = transform(original)
                self._command.setPlainText(result)
                self._preview.setText(result if len(result) <= 600 else result[:600] + "…")
            except Exception as exc:
                self._command.setPlainText(original)
                self.transformation_failed.emit(str(exc))

        QTimer.singleShot(0, run)

    def set_injector(self, injector: TextInjector | None) -> None:
        self._injector = injector


__all__ = ["PlaygroundPage"]
