"""Playback tab — auto-insert, show dictation widget, auto-save."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)
from soundflow.ui.widgets import PreferenceToggleRow

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

        for attr, label, description, value in (
            (
                "_auto_insert",
                "Insert text automatically at the cursor",
                "Paste completed dictation into the focused application.",
                getattr(settings, "auto_insert", True),
            ),
            (
                "_show_widget",
                "Show floating dictation widget while recording",
                "Display recording and transcription status above other apps.",
                getattr(settings, "show_dictation_widget", True),
            ),
            (
                "_auto_save",
                "Auto-save transcripts to History",
                "Keep completed dictations locally so they can be reviewed.",
                getattr(settings, "auto_save_transcripts", True),
            ),
        ):
            row = PreferenceToggleRow(
                label, description, checked=bool(value)
            )
            setattr(self, attr, row.switch)
            layout.addWidget(row)
        outer.addWidget(card)
        outer.addStretch(1)

    def write_back(self, settings) -> None:
        settings.auto_insert = self._auto_insert.isChecked()
        settings.show_dictation_widget = self._show_widget.isChecked()
        settings.auto_save_transcripts = self._auto_save.isChecked()


__all__ = ["PlaybackTab"]
