"""General tab — appearance, silence timeout, auto-copy, start-minimized."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from soundflow.ui.widgets import AppearanceSelector, PreferenceToggleRow

from soundflow.design import (
    BODY_FONT,
    CONTROL_HEIGHT_SM,
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

    appearance_changed = Signal(str)

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("generalTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("generalScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.viewport().setObjectName("generalScrollViewport")

        content = QWidget()
        content.setObjectName("generalContent")
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        content_layout.setSpacing(SPACE_4)
        content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        # Appearance
        appearance_card = self._make_card("Appearance")
        appearance_row = QHBoxLayout()
        appearance_row.setContentsMargins(0, 0, 0, 0)
        appearance_row.setSpacing(SPACE_3)
        theme_label = QLabel("Theme")
        theme_label.setFont(QFont(BODY_FONT, FONT_BODY))
        self._theme = AppearanceSelector(settings.appearance)
        self._theme.setMaximumWidth(190)
        self._theme.changed.connect(self.appearance_changed)
        appearance_row.addWidget(theme_label)
        appearance_row.addWidget(self._theme, 1)
        appearance_row.addStretch(1)
        appearance_card.layout().addLayout(appearance_row)
        content_layout.addWidget(appearance_card)

        # Dictation
        dictation_card = self._make_card("Dictation")
        dictation_layout = dictation_card.layout()
        silence_title = QLabel("Silence timeout")
        silence_title.setFont(QFont(BODY_FONT, FONT_BODY))
        dictation_layout.addWidget(silence_title)

        # Preset chips
        chip_row = QHBoxLayout()
        chip_row.setSpacing(SPACE_2)
        chip_row.setContentsMargins(0, 0, 0, 0)
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
        dictation_layout.addLayout(chip_row)

        self._silence = QSlider(Qt.Orientation.Horizontal)
        self._silence.setMinimum(300)
        self._silence.setMaximum(1500)
        self._silence.setSingleStep(50)
        self._silence.setValue(int(settings.silence_duration_ms))
        dictation_layout.addWidget(self._silence)

        self._silence_label = QLabel(f"{self._silence.value()} ms")
        self._silence_label.setObjectName("mutedText")
        self._silence_label.setFont(QFont(BODY_FONT, FONT_SMALL))
        dictation_layout.addWidget(self._silence_label)
        self._silence.valueChanged.connect(self._on_slider)

        content_layout.addWidget(dictation_card)

        # Behavior
        behavior_card = self._make_card("Behavior")
        bform = QVBoxLayout()
        bform.setSpacing(SPACE_2)
        bform.setContentsMargins(0, 0, 0, 0)

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
        content_layout.addWidget(behavior_card)

        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Initial preset highlight
        self._highlight_preset(int(settings.silence_duration_ms))

    # ------------------------------------------------------------------
    def _make_card(self, title: str) -> QWidget:
        card = QWidget()
        card.setObjectName("preferencesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
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
        settings.appearance = self._theme.value()
        settings.silence_duration_ms = int(self._silence.value())
        settings.auto_copy = self._auto_copy.isChecked()
        settings.start_minimized = self._start_minimized.isChecked()


__all__ = ["GeneralTab"]
