"""Bottom status bar — persistent across all pages.

Reference layout:

    ● System Ready · ✦ Offline Mode · English (US) · ⚙

Uses the design tokens from :mod:`soundflow.design`. Exposes a small API
to update each segment; segments with no updater stay at their default
text.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from soundflow.design import (
    BODY_FONT,
    FONT_SMALL,
    SPACE_3,
)


class StatusBar(QWidget):
    """Persistent bottom status bar."""

    gear_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_3)

        font = QFont(BODY_FONT, FONT_SMALL)

        self._status_dot = QLabel("\u25CF")
        self._status_dot.setObjectName("statusDot")
        self._status_dot.setFont(font)
        self._status_dot.setProperty("state", "ready")

        self._status_label = QLabel("System Ready")
        self._status_label.setObjectName("statusBarLabel")
        self._status_label.setFont(font)

        self._offline_dot = QLabel("\u2726")
        self._offline_dot.setObjectName("statusBarAccent")
        self._offline_dot.setFont(font)

        self._offline_label = QLabel("Offline Mode")
        self._offline_label.setObjectName("statusBarLabel")
        self._offline_label.setFont(font)

        self._language = QLabel("English (US)")
        self._language.setObjectName("statusBarLabel")
        self._language.setFont(font)

        self._gear = QPushButton("\u2699")
        self._gear.setObjectName("statusBarGear")
        self._gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gear.setFixedWidth(28)
        self._gear.clicked.connect(self.gear_clicked)

        layout.addWidget(self._status_dot)
        layout.addWidget(self._status_label)
        layout.addSpacing(SPACE_3 * 2)
        layout.addWidget(self._offline_dot)
        layout.addWidget(self._offline_label)
        layout.addStretch(1)
        layout.addWidget(self._language)
        layout.addSpacing(SPACE_3)
        layout.addWidget(self._gear)

    # ------------------------------------------------------------------
    def set_status(self, label: str, state: str = "ready") -> None:
        self._status_label.setText(label)
        self._status_dot.setProperty("state", state)
        # Force re-evaluation of the dynamic property by re-applying stylesheet
        self._status_dot.style().unpolish(self._status_dot)
        self._status_dot.style().polish(self._status_dot)

    def set_language(self, label: str) -> None:
        self._language.setText(label)

    def set_offline(self, label: str = "Offline Mode") -> None:
        self._offline_label.setText(label)


__all__ = ["StatusBar"]
