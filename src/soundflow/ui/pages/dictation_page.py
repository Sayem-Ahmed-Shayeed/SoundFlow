"""Dictation page — redesigned home surface.

Layout (top to bottom):

* Page header — ``Dictation`` title + ``English ▾`` language picker +
  :class:`WindowChrome` for inline min/max/close.
* Hero — large centered text:

    - idle:       "Start speaking"
    - recording:  "I'm listening…"
    - draining:   "Almost done…"

* :class:`WaveformRing` driven by ``UiBridge.level``.
* Footer hint — ``Press [Space] to start/stop`` + subtle model/device row.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import (
    BODY_FONT,
    DISPLAY_FONT,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_SMALL,
    FONT_TITLE,
    MONO_FONT,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SPACE_8,
)
from soundflow.hotkeys import display_hotkey
from soundflow.ui.widgets import WaveformRing, WindowChrome

HERO_IDLE = "Start speaking"
HERO_RECORDING = "I'm listening\u2026"
HERO_DRAINING = "Almost done\u2026"


class DictationPage(QWidget):
    """Redesigned Dictation home page."""

    language_changed = Signal(str)
    dictation_toggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dictationPage")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_8, SPACE_4, SPACE_8, SPACE_6)
        outer.setSpacing(SPACE_4)

        # --- Header row -------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(SPACE_3)

        header.addStretch(1)

        self._language = QComboBox()
        self._language.setObjectName("languagePicker")
        self._language.addItem("Auto detect", "auto")
        self._language.addItem("English", "en")
        self._language.addItem("\u09AC\u09BE\u0982\u09B2\u09BE", "bn")
        self._language.addItem("Hindi", "hi")
        self._language.addItem("Spanish", "es")
        self._language.addItem("French", "fr")
        self._language.addItem("German", "de")
        self._language.addItem("Japanese", "ja")
        self._language.currentIndexChanged.connect(self._emit_language)
        self._language.hide()

        outer.addLayout(header)

        # --- Hero block -------------------------------------------------
        hero = QVBoxLayout()
        hero.setSpacing(SPACE_4)

        prompt = QLabel("Start speaking")
        prompt.setFont(QFont(DISPLAY_FONT, FONT_TITLE))
        prompt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prompt.setObjectName("headingText")
        hero.addWidget(prompt)

        self._hero = QLabel("Press Space or hold Ctrl + Alt + Space")
        hero_font = QFont(DISPLAY_FONT, FONT_DISPLAY)
        self._hero.setFont(hero_font)
        self._hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hero.setObjectName("displayText")
        hero.addWidget(self._hero)

        self._ring = WaveformRing()
        self._ring.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ring.setAccessibleName("Start or stop dictation")
        self._ring.setAccessibleDescription(
            "Press Space or activate this microphone control."
        )
        self._ring.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._ring.installEventFilter(self)
        self._ring.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        hero.addWidget(self._ring)

        outer.addLayout(hero)

        # --- Shortcut hint ---------------------------------------------
        hint_row = QHBoxLayout()
        hint_row.setSpacing(SPACE_2)

        hint_row.addStretch(1)
        hint_label = QLabel("Press")
        hint_label.setFont(QFont(BODY_FONT, FONT_BODY))
        hint_label.setObjectName("mutedText")
        hint_row.addWidget(hint_label)

        keycap = QLabel("Space")
        keycap.setObjectName("keyCap")
        keycap.setFont(QFont(MONO_FONT, FONT_SMALL))
        hint_row.addWidget(keycap)

        tail = QLabel("to start/stop")
        tail.setFont(QFont(BODY_FONT, FONT_BODY))
        tail.setObjectName("mutedText")
        hint_row.addWidget(tail)
        hint_row.addStretch(1)

        outer.addLayout(hint_row)

        # --- Subtle model/device row -----------------------------------
        meta_row = QHBoxLayout()
        meta_row.setSpacing(SPACE_4)
        meta_row.addStretch(1)

        self._meta = QLabel("")
        self._meta.setObjectName("dimText")
        self._meta.setFont(QFont(BODY_FONT, FONT_SMALL))
        meta_row.addWidget(self._meta)

        meta_row.addStretch(1)
        outer.addLayout(meta_row)

        outer.addStretch(1)

        self._state = "idle"
        self._shortcut_display = "Ctrl + Alt + SPACE"

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        if state == "recording":
            self._hero.setText(HERO_RECORDING)
        elif state == "draining":
            self._hero.setText(HERO_DRAINING)
        else:
            self._hero.setText(
                f"Press Space or hold {self._shortcut_display}"
            )
        self._ring.set_state(state)

    def push_level(self, level: float) -> None:
        self._ring.push_level(level)

    def set_meta(self, text: str) -> None:
        self._meta.setText(text)

    def set_shortcut(self, shortcut: str) -> None:
        try:
            self._shortcut_display = display_hotkey(shortcut)
        except ValueError:
            self._shortcut_display = "Ctrl + Alt + SPACE"
        if self._state == "idle":
            self._hero.setText(
                f"Press Space or hold {self._shortcut_display}"
            )

    def set_language(self, language: str) -> None:
        index = self._language.findData(language)
        self._language.blockSignals(True)
        self._language.setCurrentIndex(max(0, index))
        self._language.blockSignals(False)

    @property
    def language_picker(self) -> QComboBox:
        return self._language

    def eventFilter(self, watched, event) -> bool:
        if (
            watched is self._ring
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.dictation_toggled.emit()
            return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event) -> None:
        if (
            event.key() == Qt.Key.Key_Space
            and not event.isAutoRepeat()
            and not self._language.hasFocus()
        ):
            self.dictation_toggled.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    def _emit_language(self, _index: int) -> None:
        self.language_changed.emit(self._language.currentData() or "auto")

__all__ = ["DictationPage"]
