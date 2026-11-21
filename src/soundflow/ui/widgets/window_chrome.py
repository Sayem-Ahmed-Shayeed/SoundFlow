"""Inline window chrome — min / max / close buttons.

Replaces the OS title bar for the Dictation panel so the design language
is consistent. Emits three signals: ``minimize``, ``maximize``, ``close``.
The host window connects them to its own handlers.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from soundflow.design import SPACE_1, icon, icon_size

_CHROME_ICON = "#8E8E99"  # mid-grey reads on both themes


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
        layout.setSpacing(SPACE_1)

        self._min = self._make_button("minimize", "minimize")
        self._max = self._make_button("maximize", "maximize")
        self._close = self._make_button("close", "close")
        self._close.setObjectName("windowChrome:close")

        layout.addWidget(self._min)
        layout.addWidget(self._max)
        layout.addWidget(self._close)

    def _make_button(self, glyph: str, slot: str) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(icon(glyph, _CHROME_ICON, 16))
        btn.setIconSize(icon_size(16))
        btn.setToolTip(slot.capitalize())
        btn.setAccessibleName(slot.capitalize())
        btn.setObjectName(f"windowChrome:{slot}")
        btn.setProperty("chrome", True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(30, 28)
        if slot == "minimize":
            btn.clicked.connect(self.minimize)
        elif slot == "maximize":
            btn.clicked.connect(self.maximize)
        elif slot == "close":
            btn.clicked.connect(self.close)
        return btn


__all__ = ["WindowChrome"]
