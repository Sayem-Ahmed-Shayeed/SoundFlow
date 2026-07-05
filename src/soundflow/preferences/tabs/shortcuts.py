"""Shortcuts tab — push-to-talk, toggle, insert, hotkey status."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
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
    MONO_FONT,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)
from soundflow.hotkeys import (
    canonical_hotkey,
    display_hotkey,
)


def _keycap(text: str) -> QLabel:
    cap = QLabel(text)
    cap.setObjectName("keyCap")
    cap.setFont(QFont(MONO_FONT, FONT_SMALL))
    cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return cap


class ShortcutsTab(QWidget):
    """Shortcuts preferences tab."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("shortcutsTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        outer.setSpacing(SPACE_4)

        # Push-to-talk card
        ptt_card = QWidget()
        ptt_card.setObjectName("preferencesCard")
        pl = QVBoxLayout(ptt_card)
        pl.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        pl.setSpacing(SPACE_2)

        title = QLabel("Push-to-talk")
        title.setFont(QFont(BODY_FONT, FONT_HEADING))
        title.setObjectName("headingText")
        pl.addWidget(title)

        try:
            display = display_hotkey(settings.push_to_talk_hotkey)
        except ValueError:
            display = settings.push_to_talk_hotkey
        chip_row = QHBoxLayout()
        chip_row.setSpacing(SPACE_2)
        for token in display.split(" + "):
            chip_row.addWidget(_keycap(token))
        chip_row.addStretch(1)
        pl.addLayout(chip_row)

        note = QLabel(
            "On Wayland, your desktop will ask once for permission to use this"
            " system-wide shortcut."
        )
        note.setObjectName("mutedText")
        note.setFont(QFont(BODY_FONT, FONT_SMALL))
        note.setWordWrap(True)
        pl.addWidget(note)

        outer.addWidget(ptt_card)

        # Other shortcuts
        other_card = QWidget()
        other_card.setObjectName("preferencesCard")
        ol = QVBoxLayout(other_card)
        ol.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        ol.setSpacing(SPACE_2)
        ol.addWidget(self._heading("Other shortcuts"))

        form = QFormLayout()
        form.setSpacing(SPACE_2)

        self._toggle = QCheckBox("Listen for shortcuts while Soundflow is in the background")
        self._toggle.setChecked(bool(settings.global_hotkeys))
        form.addRow(self._toggle)

        ol.addLayout(form)
        outer.addWidget(other_card)

        # Reset
        reset_btn = QPushButton("Reset to default")
        reset_btn.setObjectName("quietButton")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        outer.addWidget(reset_btn, 0, Qt.AlignmentFlag.AlignLeft)

        outer.addStretch(1)

    def _heading(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont(BODY_FONT, FONT_HEADING))
        lbl.setObjectName("headingText")
        return lbl

    def write_back(self, settings) -> None:
        settings.global_hotkeys = self._toggle.isChecked()


__all__ = ["ShortcutsTab"]
