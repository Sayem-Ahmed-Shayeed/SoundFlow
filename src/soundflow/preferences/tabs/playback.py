"""Playback tab — auto-insert, show dictation widget, auto-save."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import (
    BODY_FONT,
    FONT_BODY,
    FONT_HEADING,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)


class PlaybackTab(QWidget):
    """Playback tab."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("playbackTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        outer.setSpacing(SPACE_4)

        card = QWidget()
        card.setObjectName("preferencesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)

        title = QLabel("Playback")
        title.setFont(QFont(BODY_FONT, FONT_HEADING))
        title.setObjectName("headingText")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(SPACE_2)

        self._auto_insert = QCheckBox("Insert text automatically at the cursor")
        self._auto_insert.setChecked(bool(getattr(settings, "auto_insert", True)))
        form.addRow(self._auto_insert)

        self._show_widget = QCheckBox("Show floating dictation widget while recording")
        self._show_widget.setChecked(bool(getattr(settings, "show_dictation_widget", True)))
        form.addRow(self._show_widget)

        self._auto_save = QCheckBox("Auto-save transcripts to History")
        self._auto_save.setChecked(bool(getattr(settings, "auto_save_transcripts", True)))
        form.addRow(self._auto_save)

        layout.addLayout(form)
        outer.addWidget(card)
        outer.addStretch(1)

    def write_back(self, settings) -> None:
        settings.auto_insert = self._auto_insert.isChecked()
        settings.show_dictation_widget = self._show_widget.isChecked()
        settings.auto_save_transcripts = self._auto_save.isChecked()


__all__ = ["PlaybackTab"]