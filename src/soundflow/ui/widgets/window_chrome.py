"""Inline window chrome — min / max / close buttons.

Replaces the OS title bar for the Dictation panel so the design language
is consistent. Emits three signals: ``minimize``, ``maximize``, ``close``.
The host window connects them to its own handlers.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from soundflow.design import (
    BODY_FONT,
    FONT_BODY,
    FG_CREAM,
    FG_MUTED,
    SPACE_2,
)


class WindowChrome(QWidget):
    """Three inline window controls."""

    minimize = Signal()
    maximize = Signal()
    close = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("windowChrome")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)

        self._min = self._make_button("\u2014", "minimize")  # em-dash
        self._max = self._make_button("\u25A1", "maximize")  # square
        self._close = self._make_button("\u00D7", "close")  # multiplication sign
        self._close.setObjectName("windowChrome:close")

        layout.addWidget(self._min)
        layout.addWidget(self._max)
        layout.addWidget(self._close)

    def _make_button(self, glyph: str, slot: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setObjectName(f"windowChrome:{slot}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(28, 28)
        btn.setFont(__import__("PySide6.QtGui", fromlist=["QFont"]).QFont(BODY_FONT, FONT_BODY))
        if slot == "minimize":
            btn.clicked.connect(self.minimize)
        elif slot == "maximize":
            btn.clicked.connect(self.maximize)
        elif slot == "close":
            btn.clicked.connect(self.close)
        return btn


__all__ = ["WindowChrome"]