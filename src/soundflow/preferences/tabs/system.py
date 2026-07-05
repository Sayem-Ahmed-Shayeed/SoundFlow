"""System tab — model status, data folder, reset."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import (
    BODY_FONT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)
from soundflow.utils import open_data_folder


class SystemTab(QWidget):
    """System preferences tab."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("systemTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        outer.setSpacing(SPACE_4)

        # Model card
        model_card = self._card("Model")
        form = QFormLayout()
        form.setSpacing(SPACE_2)

        path_lbl = QLabel(settings.model_path or "Default location")
        path_lbl.setObjectName("mutedText")
        path_lbl.setFont(QFont(BODY_FONT, FONT_SMALL))
        path_lbl.setWordWrap(True)
        form.addRow("Path", path_lbl)

        size_lbl = QLabel("Local Model")
        size_lbl.setObjectName("mutedText")
        size_lbl.setFont(QFont(BODY_FONT, FONT_SMALL))
        form.addRow("Status", size_lbl)

        check_btn = QPushButton("Check system")
        check_btn.setObjectName("primaryButton")
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        form.addRow("", check_btn)

        model_card.layout().addLayout(form)
        outer.addWidget(model_card)

        # Data folder card
        data_card = self._card("Data")
        dlayout = QVBoxLayout()
        dlayout.setSpacing(SPACE_2)
        desc = QLabel(
            "All settings, models, and saved transcripts live under the"
            " application data folder."
        )
        desc.setObjectName("mutedText")
        desc.setFont(QFont(BODY_FONT, FONT_SMALL))
        desc.setWordWrap(True)
        dlayout.addWidget(desc)

        open_btn = QPushButton("Open data folder")
        open_btn.setObjectName("primaryButton")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(open_data_folder)
        dlayout.addWidget(open_btn, 0, Qt.AlignmentFlag.AlignLeft)

        data_card.layout().addLayout(dlayout)
        outer.addWidget(data_card)

        outer.addStretch(1)

    def _card(self, title: str) -> QWidget:
        card = QWidget()
        card.setObjectName("preferencesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)
        head = QLabel(title)
        head.setFont(QFont(BODY_FONT, FONT_HEADING))
        head.setObjectName("headingText")
        layout.addWidget(head)
        return card

    def write_back(self, settings) -> None:
        pass


__all__ = ["SystemTab"]
