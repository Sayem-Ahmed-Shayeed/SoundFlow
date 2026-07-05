"""Persistent application sidebar used by every Soundflow page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class AppSidebar(QFrame):
    page_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideBar")
        self.setFixedWidth(176)
        self._buttons: dict[str, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(8)

        brand_row = QHBoxLayout()
        mark = QLabel("⌁")
        mark.setObjectName("brandMark")
        brand = QLabel("Soundflow")
        brand.setObjectName("brand")
        brand_row.addWidget(mark)
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(28)

        for key, glyph, label in (
            ("dictation", "♩", "Dictation"),
            ("history", "◷", "History"),
            ("playground", "♧", "Playground"),
            ("preferences", "⚙", "Preferences"),
        ):
            button = QPushButton(f"{glyph}   {label}")
            button.setObjectName("sideNavButton")
            button.setProperty("active", False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, selected=key: self.page_requested.emit(selected)
            )
            self._buttons[key] = button
            layout.addWidget(button)

        layout.addStretch(1)
        privacy = QFrame()
        privacy.setObjectName("privacyCard")
        privacy_layout = QVBoxLayout(privacy)
        privacy_layout.setContentsMargins(12, 12, 12, 12)
        heading = QLabel("◉  100% Private")
        heading.setObjectName("privacyPill")
        copy = QLabel("All processing happens\noffline on your device.")
        copy.setObjectName("railCaption")
        copy.setWordWrap(True)
        privacy_layout.addWidget(heading)
        privacy_layout.addWidget(copy)
        layout.addWidget(privacy)
        self.select("dictation")

    def select(self, key: str) -> None:
        for token, button in self._buttons.items():
            button.setProperty("active", token == key)
            button.style().unpolish(button)
            button.style().polish(button)


__all__ = ["AppSidebar"]
