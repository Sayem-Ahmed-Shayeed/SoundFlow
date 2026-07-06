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
        outer.setContentsMargins(SPACE_8, SPACE_6, SPACE_8, SPACE_6)
        outer.setSpacing(SPACE_4)

        # Header
        header = QVBoxLayout()
        header.setSpacing(SPACE_2)
        title = QLabel("Playground")
        title.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        title.setObjectName("displayText")
        header.addWidget(title)

        subtitle = QLabel("Try commands and shortcuts")
        subtitle.setFont(QFont(BODY_FONT, FONT_BODY))
        subtitle.setObjectName("mutedText")
        header.addWidget(subtitle)
        outer.addLayout(header)

        # Command input
        self._command = QPlainTextEdit()
        self._command.setObjectName("playgroundCommand")
        self._command.setPlaceholderText(
            "Start typing a command or run a shortcut\u2026"
        )
        self._command.setFont(QFont(BODY_FONT, FONT_BODY))
        self._command.setMinimumHeight(132)
        self._command.setMaximumHeight(220)
        self._command.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        outer.addWidget(self._command)

        # Ctrl+Enter submits
        submit = QShortcut(QKeySequence("Ctrl+Return"), self._command)
        submit.activated.connect(self._on_submit)

        # Quick actions row
        cards = QHBoxLayout()
        cards.setSpacing(SPACE_3)

        self._insert_card = _QuickCard(
            "\u2702", "Insert Text", "Insert text at cursor", enabled=True
        )
        self._insert_card.clicked.connect(self._run_insert)
        cards.addWidget(self._insert_card)

        self._format_card = _QuickCard(
            "A", "Format Text", "Format selected text", enabled=True
        )
        self._format_card.clicked.connect(self._run_format)
        cards.addWidget(self._format_card)

        self._rewrite_card = _QuickCard(
            "\u270E", "Smart Rewrite", "Improve writing", enabled=True
        )
        self._rewrite_card.clicked.connect(self._run_smart_rewrite)
        cards.addWidget(self._rewrite_card)

        outer.addLayout(cards)

        outer.addStretch(1)

        # Tip line
        tip = QLabel("\u2728 Tip: Use shortcuts to automate your workflow")
        tip.setObjectName("mutedText")
        tip.setFont(QFont(BODY_FONT, FONT_SMALL))
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(tip)

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
                self._command.setPlainText(transform(original))
            except Exception as exc:
                self._command.setPlainText(original)
                self.transformation_failed.emit(str(exc))

        QTimer.singleShot(0, run)

    def set_injector(self, injector: TextInjector | None) -> None:
        self._injector = injector


__all__ = ["PlaygroundPage"]
