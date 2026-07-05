"""Top tab bar — replaces the legacy sidebar navigation.

Four tabs: Dictation · History · Playground · Preferences. Driven by a
``QStackedWidget`` that the host window swaps as the user clicks. Emits
``current_changed(str)`` carrying the tab key so callers don't depend on
tab indices.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from soundflow.design import (
    BODY_FONT,
    FONT_BODY,
    SPACE_2,
    SPACE_4,
)


class TopTabBar(QWidget):
    """Cream-on-black top tab bar."""

    current_changed = Signal(str)

    TABS = (
        ("dictation", "Dictation"),
        ("history", "History"),
        ("playground", "Playground"),
        ("preferences", "Preferences"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topTabBar")
        self.setAttribute(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_4, SPACE_2, SPACE_4, 0)
        layout.setSpacing(SPACE_2)
        layout.addStretch(1)

        self._buttons: dict[str, QPushButton] = {}
        for key, label in self.TABS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
            btn.setFont(__import__("PySide6.QtGui", fromlist=["QFont"]).QFont(BODY_FONT, FONT_BODY))
            btn.setObjectName(f"topTab:{key}")
            btn.clicked.connect(lambda _checked=False, k=key: self.select(k))
            self._buttons[key] = btn
            layout.addWidget(btn)
        layout.addStretch(1)

        self._current = ""
        self.select(self.TABS[0][0])

    # ------------------------------------------------------------------
    def select(self, key: str) -> None:
        if key not in self._buttons or key == self._current:
            return
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)
        self._current = key
        self.current_changed.emit(key)

    @property
    def current(self) -> str:
        return self._current


__all__ = ["TopTabBar"]