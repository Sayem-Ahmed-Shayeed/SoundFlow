"""Shortcuts tab — push-to-talk, toggle, insert, hotkey status."""

from __future__ import annotations

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
    CONTROL_HEIGHT_SM,
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
from soundflow.ui.widgets import PreferenceToggleRow, ShortcutPicker


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
        self._original_shortcut = settings.push_to_talk_hotkey

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

        chip_row = QHBoxLayout()
        chip_row.setSpacing(SPACE_2)
        self._summary_caps: list[QLabel] = []
        self._summary_pluses: list[QLabel] = []
        for index in range(3):
            cap = _keycap("")
            cap.setObjectName("shortcutSummaryCap")
            self._summary_caps.append(cap)
            chip_row.addWidget(cap)
            if index < 2:
                plus = QLabel("+")
                plus.setObjectName("mutedText")
                self._summary_pluses.append(plus)
                chip_row.addWidget(plus)
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
        ol.setContentsMargins(SPACE_2, SPACE_2, SPACE_2, SPACE_2)
        ol.setSpacing(4)
        ol.addWidget(self._heading("Other shortcuts"))

        form = QFormLayout()
        form.setHorizontalSpacing(SPACE_2)
        form.setVerticalSpacing(4)

        self._picker = ShortcutPicker(settings.push_to_talk_hotkey)
        self._picker.setMaximumHeight(CONTROL_HEIGHT_SM)
        self._picker.modifiers.setObjectName("compactShortcutField")
        self._picker.modifiers.setFixedSize(128, CONTROL_HEIGHT_SM)
        self._picker.key.setObjectName("compactShortcutField")
        self._picker.key.setFixedSize(112, CONTROL_HEIGHT_SM)
        self._picker.modifiers.currentIndexChanged.connect(
            self._sync_shortcut_summary
        )
        self._picker.key.currentIndexChanged.connect(
            self._sync_shortcut_summary
        )
        self._sync_shortcut_summary()
        form.addRow("Hold to dictate", self._picker)

        toggle_row = PreferenceToggleRow(
            "Listen for shortcuts while Soundflow is in the background",
            "Enables push-to-talk even when another app is focused.",
            checked=bool(settings.global_hotkeys),
        )
        self._toggle = toggle_row.switch
        form.addRow(toggle_row)

        ol.addLayout(form)
        outer.addWidget(other_card)

        # Reset
        reset_btn = QPushButton("Reset to default")
        reset_btn.setObjectName("textActionButton")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._reset)
        outer.addWidget(reset_btn, 0, Qt.AlignmentFlag.AlignLeft)

        outer.addStretch(1)

    def _heading(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont(BODY_FONT, FONT_HEADING))
        lbl.setObjectName("headingText")
        return lbl

    def write_back(self, settings) -> None:
        settings.global_hotkeys = self._toggle.isChecked()
        shortcut = self._picker.shortcut()
        if shortcut != self._original_shortcut:
            settings.hotkey_authorized = False
        settings.push_to_talk_hotkey = shortcut
        self._original_shortcut = shortcut

    def _sync_shortcut_summary(self, *_args) -> None:
        try:
            tokens = display_hotkey(self._picker.shortcut()).split(" + ")
        except ValueError:
            tokens = ["Ctrl", "Alt", "Space"]
        for index, cap in enumerate(self._summary_caps):
            visible = index < len(tokens)
            cap.setVisible(visible)
            if visible:
                cap.setText(tokens[index])
        for index, plus in enumerate(self._summary_pluses):
            plus.setVisible(index < len(tokens) - 1)

    def _reset(self) -> None:
        self._picker.set_shortcut("ctrl+alt+space")
        self._toggle.setChecked(True)


__all__ = ["ShortcutsTab"]
