"""Focused dictation home surface with a single recorder action."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import (
    BODY_FONT,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_SMALL,
    FONT_TINY,
    FONT_TITLE,
    HOME_DISPLAY_FONT,
    ANIMATION_FAST,
    MONO_FONT,
    SPACE_1,
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
        self._state = "idle"
        self._shortcut_display = "Ctrl + Alt + SPACE"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_8, SPACE_2, SPACE_8, SPACE_6)
        outer.setSpacing(SPACE_6)

        # --- Page identity and live state -------------------------------
        header = QHBoxLayout()
        header.setSpacing(SPACE_6)

        identity = QVBoxLayout()
        identity.setSpacing(SPACE_1)
        self._eyebrow = QLabel("VOICE DICTATION")
        self._eyebrow.setObjectName("dictationEyebrow")
        self._eyebrow.setFont(QFont(BODY_FONT, FONT_TINY))
        identity.addWidget(self._eyebrow)

        self._prompt = QLabel("Turn speech into text")
        prompt_font = QFont(HOME_DISPLAY_FONT, FONT_DISPLAY)
        prompt_font.setWeight(QFont.Weight.Bold)
        self._prompt.setFont(prompt_font)
        self._prompt.setObjectName("dictationTitle")
        identity.addWidget(self._prompt)

        self._intro = QLabel("Speak naturally. Soundflow types wherever you work.")
        self._intro.setObjectName("mutedText")
        self._intro.setFont(QFont(BODY_FONT, FONT_BODY))
        identity.addWidget(self._intro)
        header.addLayout(identity)
        header.addStretch(1)

        self._state_badge = QLabel("●  READY")
        self._state_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_badge.setObjectName("dictationStateBadge")
        self._state_badge.setProperty("state", "idle")
        header.addWidget(self._state_badge, 0, Qt.AlignmentFlag.AlignTop)

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

        # --- Recorder stage ---------------------------------------------
        self._hero_panel = QWidget()
        self._hero_panel.setObjectName("dictationStage")
        self._hero_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hero = QVBoxLayout(self._hero_panel)
        hero.setContentsMargins(SPACE_8, SPACE_4, SPACE_8, SPACE_4)
        hero.setSpacing(SPACE_2)
        hero.addStretch(1)

        self._hero = QLabel("Click the microphone or press Space")
        hero_font = QFont(HOME_DISPLAY_FONT, FONT_TITLE)
        hero_font.setWeight(QFont.Weight.DemiBold)
        self._hero.setFont(hero_font)
        self._hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hero.setObjectName("dictationInstruction")
        hero.addWidget(self._hero)
        self._hero_effect = QGraphicsOpacityEffect(self._hero)
        self._hero_effect.setOpacity(1.0)
        self._hero.setGraphicsEffect(self._hero_effect)
        self._hero_animation = QPropertyAnimation(
            self._hero_effect, b"opacity", self
        )
        self._hero_animation.setDuration(ANIMATION_FAST)
        self._hero_animation.setStartValue(0.25)
        self._hero_animation.setEndValue(1.0)
        self._hero_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

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

        supporting = QLabel("Release the shortcut to transcribe and insert.")
        supporting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        supporting.setObjectName("mutedText")
        supporting.setFont(QFont(BODY_FONT, FONT_SMALL))
        hero.addWidget(supporting)
        hero.addStretch(1)

        outer.addWidget(self._hero_panel, 1)

        # --- Compact technical rail ------------------------------------
        rail = QWidget()
        rail.setObjectName("dictationMetaRail")
        rail.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        meta_row = QHBoxLayout(rail)
        meta_row.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_3)
        meta_row.setSpacing(SPACE_8)

        shortcut_stack = QVBoxLayout()
        shortcut_stack.setSpacing(SPACE_1)
        shortcut_label = QLabel("GLOBAL SHORTCUT")
        shortcut_label.setObjectName("dictationMetaLabel")
        shortcut_stack.addWidget(shortcut_label)
        self._shortcut_value = QLabel(self._shortcut_display)
        self._shortcut_value.setObjectName("dictationMetaValue")
        self._shortcut_value.setFont(QFont(MONO_FONT, FONT_SMALL))
        shortcut_stack.addWidget(self._shortcut_value)
        meta_row.addLayout(shortcut_stack)

        meta_row.addStretch(1)

        model_stack = QVBoxLayout()
        model_stack.setSpacing(SPACE_1)
        model_label = QLabel("ACTIVE MODEL")
        model_label.setObjectName("dictationMetaLabel")
        model_stack.addWidget(model_label)
        self._model_value = QLabel("Loading model details…")
        self._model_value.setObjectName("dictationMetaValue")
        self._model_value.setFont(QFont(MONO_FONT, FONT_SMALL))
        model_stack.addWidget(self._model_value)
        meta_row.addLayout(model_stack)
        outer.addWidget(rail)

        self._shortcut_value.setText(self._shortcut_display)

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        if state == "recording":
            self._state_badge.setText("●  LIVE")
            self._state_badge.setProperty("state", "recording")
            self._prompt.setText("Speak naturally")
            self._hero.setText(HERO_RECORDING)
        elif state == "draining":
            self._state_badge.setText("✦  PROCESSING")
            self._state_badge.setProperty("state", "draining")
            self._prompt.setText("Creating your transcript")
            self._hero.setText(HERO_DRAINING)
        else:
            self._state_badge.setText("●  READY")
            self._state_badge.setProperty("state", "idle")
            self._prompt.setText("Turn speech into text")
            self._hero.setText(
                f"Click the microphone or hold {self._shortcut_display}"
            )
        self._state_badge.style().unpolish(self._state_badge)
        self._state_badge.style().polish(self._state_badge)
        self._hero_animation.stop()
        self._hero_animation.start()
        self._ring.set_state(state)

    def push_level(self, level: float) -> None:
        self._ring.push_level(level)

    def set_meta(self, text: str) -> None:
        self._model_value.setText(text)

    def set_shortcut(self, shortcut: str) -> None:
        try:
            self._shortcut_display = display_hotkey(shortcut)
        except ValueError:
            self._shortcut_display = "Ctrl + Alt + SPACE"
        self._shortcut_value.setText(self._shortcut_display)
        if self._state == "idle":
            self._hero.setText(
                f"Click the microphone or hold {self._shortcut_display}"
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
