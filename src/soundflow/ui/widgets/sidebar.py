"""Persistent application sidebar used by every Soundflow page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from soundflow.design import BODY_FONT, FONT_SMALL, FONT_TINY, SPACE_1, SPACE_2


class AppSidebar(QFrame):
    page_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideBar")
        self.setFixedWidth(208)
        self._buttons: dict[str, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(8)

        brand_row = QHBoxLayout()
        mark = QLabel("≋")
        mark.setObjectName("brandMark")
        brand_stack = QVBoxLayout()
        brand_stack.setSpacing(0)
        brand = QLabel("Soundflow")
        brand.setObjectName("brand")
        tagline = QLabel("PRIVATE DICTATION")
        tagline.setObjectName("railSection")
        brand_stack.addWidget(brand)
        brand_stack.addWidget(tagline)
        brand_row.addWidget(mark)
        brand_row.addLayout(brand_stack)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(28)

        section = QLabel("WORKSPACE")
        section.setObjectName("railSection")
        layout.addWidget(section)
        layout.addSpacing(2)

        for key, glyph, label in (
            ("dictation", "◉", "Dictation"),
            ("history", "◷", "History"),
            ("playground", "⌘", "Playground"),
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

        footer = QWidget()
        footer.setObjectName("sideFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(2, SPACE_2, 2, 0)
        footer_layout.setSpacing(SPACE_1)
        status_row = QHBoxLayout()
        status_row.setSpacing(SPACE_1)
        dot = QLabel("●")
        dot.setObjectName("sideFooterTitle")
        dot.setFont(QFont(BODY_FONT, FONT_SMALL))
        status_row.addWidget(dot)
        on_device = QLabel("On-device")
        on_device.setObjectName("sideFooterTitle")
        on_device.setFont(QFont(BODY_FONT, FONT_SMALL))
        status_row.addWidget(on_device)
        status_row.addStretch(1)
        footer_layout.addLayout(status_row)
        caption = QLabel("Audio stays on this machine.")
        caption.setObjectName("railCaption")
        caption.setWordWrap(True)
        caption.setFont(QFont(BODY_FONT, FONT_TINY))
        footer_layout.addWidget(caption)
        layout.addWidget(footer)
        self.select("dictation")

    def select(self, key: str) -> None:
        for token, button in self._buttons.items():
            button.setProperty("active", token == key)
            button.style().unpolish(button)
            button.style().polish(button)


__all__ = ["AppSidebar"]
