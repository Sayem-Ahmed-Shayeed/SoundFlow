"""General tab — appearance, silence timeout, auto-copy, start-minimized."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from soundflow.ui.widgets import PreferenceToggleRow

from soundflow.design import (
    BODY_FONT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)


_PRESETS = (
    ("Fast", 400),
    ("Balanced", 700),
    ("Patient", 1200),
)


class GeneralTab(QWidget):
    """General preferences tab."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("generalTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        outer.setSpacing(SPACE_4)

        # Appearance
        appearance_card = self._make_card("Appearance")
        aform = QFormLayout()
        aform.setSpacing(SPACE_2)
        aform.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)

        theme_label = QLabel("Theme")
        theme_label.setFont(QFont(BODY_FONT, FONT_BODY))
        self._theme = QComboBox()
        self._theme.addItem("Dark", "dark")
        self._theme.addItem("Light", "light")
        self._theme.setCurrentIndex(0 if settings.appearance == "dark" else 1)
        aform.addRow(theme_label, self._theme)
        appearance_card.layout().addLayout(aform)
        outer.addWidget(appearance_card)

        # Dictation
        dictation_card = self._make_card("Dictation")
        dform = QFormLayout()
        dform.setSpacing(SPACE_2)
        dform.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)

        dform.addRow(QLabel("Silence timeout"))

        # Preset chips
        chip_row = QHBoxLayout()
        chip_row.setSpacing(SPACE_2)
        self._preset_buttons = []
        for label, ms in _PRESETS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("presetChip")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, v=ms: self._apply_preset(v))
            chip_row.addWidget(btn)
            self._preset_buttons.append((ms, btn))
        chip_row.addStretch(1)
        dform.addRow(chip_row)

        self._silence = QSlider(Qt.Orientation.Horizontal)
        self._silence.setMinimum(300)
        self._silence.setMaximum(1500)
        self._silence.setSingleStep(50)
        self._silence.setValue(int(settings.silence_duration_ms))
        dform.addRow(self._silence)

        self._silence_label = QLabel(f"{self._silence.value()} ms")
        self._silence_label.setObjectName("mutedText")
        self._silence_label.setFont(QFont(BODY_FONT, FONT_SMALL))
        dform.addRow(self._silence_label)
        self._silence.valueChanged.connect(self._on_slider)

        dictation_card.layout().addLayout(dform)
        outer.addWidget(dictation_card)

        # Behavior
        behavior_card = self._make_card("Behavior")
        bform = QVBoxLayout()
        bform.setSpacing(SPACE_2)
        bform.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)

        auto_copy_row = PreferenceToggleRow(
            "Copy completed phrases automatically",
            checked=bool(settings.auto_copy),
        )
        self._auto_copy = auto_copy_row.switch
        bform.addWidget(auto_copy_row)
        minimized_row = PreferenceToggleRow(
            "Start in the system tray",
            "Launch Soundflow quietly in the background.",
            checked=bool(settings.start_minimized),
        )
        self._start_minimized = minimized_row.switch
        bform.addWidget(minimized_row)

        behavior_card.layout().addLayout(bform)
        outer.addWidget(behavior_card)

        outer.addStretch(1)

        # Initial preset highlight
        self._highlight_preset(int(settings.silence_duration_ms))

    # ------------------------------------------------------------------
    def _make_card(self, title: str) -> QWidget:
        card = QWidget()
        card.setObjectName("preferencesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_2)
        head = QLabel(title)
        head.setFont(QFont(BODY_FONT, FONT_HEADING))
        head.setObjectName("headingText")
        layout.addWidget(head)
        return card

    def _on_slider(self, value: int) -> None:
        self._silence_label.setText(f"{value} ms")
        self._highlight_preset(value)

    def _apply_preset(self, ms: int) -> None:
        self._silence.setValue(ms)

    def _highlight_preset(self, value: int) -> None:
        for ms, btn in self._preset_buttons:
            btn.setChecked(abs(ms - value) < 50)

    # ------------------------------------------------------------------
    def write_back(self, settings) -> None:
        settings.appearance = self._theme.currentData() or "dark"
        settings.silence_duration_ms = int(self._silence.value())
        settings.auto_copy = self._auto_copy.isChecked()
        settings.start_minimized = self._start_minimized.isChecked()


__all__ = ["GeneralTab"]
