"""Playground page — command input + quick-action cards."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from soundflow.playground.actions import InsertTextAction, SmartRewriteAction


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
        self.setMinimumHeight(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_3)
        layout.setSpacing(SPACE_2)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont(BODY_FONT, 22))
        icon_lbl.setObjectName("quickActionIcon")
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont(BODY_FONT, FONT_HEADING))
        title_lbl.setObjectName("headingText")
        layout.addWidget(title_lbl)

        hint_lbl = QLabel(hint)
        hint_lbl.setFont(QFont(BODY_FONT, FONT_SMALL))
        hint_lbl.setObjectName("mutedText")
        layout.addWidget(hint_lbl)


class PlaygroundPage(QWidget):
    """Playground page."""

    insert_text_triggered = Signal()
    smart_rewrite_triggered = Signal()

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
        self._command = QLineEdit()
        self._command.setObjectName("playgroundCommand")
        self._command.setPlaceholderText(
            "Start typing a command or run a shortcut\u2026"
        )
        self._command.setFont(QFont(BODY_FONT, FONT_BODY))
        self._command.setMinimumHeight(44)
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

        self._rewrite_card = _QuickCard(
            "\u270E", "Smart Rewrite", "Improve writing", enabled=False
        )
        self._rewrite_card.clicked.connect(self._run_smart_rewrite)
        cards.addWidget(self._rewrite_card)

        cards.addStretch(1)
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
        text = self._command.text().strip()
        if not text:
            return
        self._command.clear()
        self._run_insert_with(text)

    def _run_insert(self) -> None:
        self._run_insert_with(self._command.text())

    def _run_insert_with(self, text: str) -> None:
        action = InsertTextAction(text=text, injector=self._injector)
        action.run()
        self.insert_text_triggered.emit()

    def _run_smart_rewrite(self) -> None:
        # Always disabled for now.
        self.smart_rewrite_triggered.emit()


__all__ = ["PlaygroundPage"]
