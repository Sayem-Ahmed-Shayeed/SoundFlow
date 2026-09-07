"""Focused dictation home surface with a single recorder action."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from soundflow.design import (
    BODY_FONT,
    CONTROL_HEIGHT_SM,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_SMALL,
    FONT_TINY,
    FONT_TITLE,
    ANIMATION_FAST,
    MONO_FONT,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    SPACE_6,
    SPACE_8,
    serif_font,
)
from soundflow.hotkeys import display_hotkey
from soundflow.ui.widgets import WaveformRing, WindowChrome

HERO_IDLE = "Ready to dictate"
HERO_RECORDING = "Listening"
HERO_DRAINING = "Transcribing"


class DictationPage(QWidget):
    """Redesigned Dictation home page."""

    language_changed = Signal(str)
    dictation_toggled = Signal()
    history_requested = Signal()

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
        self._eyebrow = QLabel("PRIVATE VOICE INPUT")
        self._eyebrow.setObjectName("dictationEyebrow")
        self._eyebrow.setFont(QFont(BODY_FONT, FONT_TINY))
        identity.addWidget(self._eyebrow)

        self._prompt = QLabel("Dictation")
        prompt_font = QFont(serif_font(), 40)
        prompt_font.setWeight(QFont.Weight.Normal)
        self._prompt.setFont(prompt_font)
        self._prompt.setObjectName("dictationTitle")
        identity.addWidget(self._prompt)

        self._intro = QLabel(
            "Fast, private speech-to-text that works wherever you type."
        )
        self._intro.setObjectName("mutedText")
        self._intro.setFont(QFont(BODY_FONT, FONT_BODY))
        identity.addWidget(self._intro)
        header.addLayout(identity)
        header.addStretch(1)

        self._state_badge = QLabel("●  READY")
        self._state_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._state_badge.setObjectName("dictationStateBadge")
        self._state_badge.setProperty("state", "idle")

        side = QVBoxLayout()
        side.setSpacing(SPACE_1)
        side.addWidget(
            self._state_badge, 0, Qt.AlignmentFlag.AlignRight
        )

        language_label = QLabel("LANGUAGE")
        language_label.setObjectName("dictationMetaLabel")
        language_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        side.addWidget(language_label, 0, Qt.AlignmentFlag.AlignRight)

        self._language = QComboBox()
        self._language.setObjectName("languagePicker")
        self._language.setAccessibleName("Dictation language")
        self._language.setCursor(Qt.CursorShape.PointingHandCursor)
        self._language.setFixedHeight(CONTROL_HEIGHT_SM)
        self._language.setMinimumWidth(150)
        self._language.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._language.addItem("Auto detect", "auto")
        self._language.addItem("English", "en")
        self._language.addItem("বাংলা", "bn")
        self._language.addItem("Hindi", "hi")
        self._language.addItem("Spanish", "es")
        self._language.addItem("French", "fr")
        self._language.addItem("German", "de")
        self._language.addItem("Japanese", "ja")
        self._language.currentIndexChanged.connect(self._emit_language)
        side.addWidget(self._language, 0, Qt.AlignmentFlag.AlignRight)
        header.addLayout(side)

        outer.addLayout(header)

        # --- Recorder stage ---------------------------------------------
        self._hero_panel = QWidget()
        self._hero_panel.setObjectName("dictationStage")
        self._hero_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        hero = QVBoxLayout(self._hero_panel)
        hero.setContentsMargins(SPACE_8, SPACE_4, SPACE_8, SPACE_4)
        hero.setSpacing(SPACE_2)
        hero.addStretch(1)

        self._stage_status = QLabel("On-device microphone ready")
        self._stage_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stage_status.setObjectName("mutedText")
        self._stage_status.setFont(QFont(BODY_FONT, FONT_SMALL))
        hero.addWidget(self._stage_status)

        self._hero = QLabel(HERO_IDLE)
        hero_font = QFont(serif_font(), 30)
        hero_font.setWeight(QFont.Weight.Normal)
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

        supporting = QLabel(
            "Hold the shortcut, speak naturally, then release to insert."
        )
        supporting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        supporting.setObjectName("mutedText")
        supporting.setFont(QFont(BODY_FONT, FONT_SMALL))
        hero.addWidget(supporting)
        self._hint = supporting

        keys_row = QHBoxLayout()
        keys_row.setSpacing(SPACE_1)
        keys_row.addStretch(1)
        self._keys_label = QLabel("Push-to-talk")
        self._keys_label.setObjectName("mutedText")
        self._keys_label.setFont(QFont(BODY_FONT, FONT_SMALL))
        keys_row.addWidget(self._keys_label)
        self._keys_box = QHBoxLayout()
        self._keys_box.setSpacing(SPACE_1)
        keys_row.addLayout(self._keys_box)
        keys_row.addStretch(1)
        hero.addLayout(keys_row)
        self._rebuild_keycaps()

        self._interim = QLabel("")
        self._interim.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._interim.setObjectName("dictationInterim")
        interim_font = QFont(BODY_FONT, FONT_BODY)
        interim_font.setItalic(True)
        self._interim.setFont(interim_font)
        self._interim.setWordWrap(True)
        self._interim.setMinimumHeight(24)
        self._interim.hide()
        hero.addWidget(self._interim)
        hero.addStretch(1)

        outer.addWidget(self._hero_panel, 1)

        # --- Flat stats strip -------------------------------------------
        strip_holder = QWidget()
        strip_holder.setObjectName("dictationStrip")
        strip = QHBoxLayout(strip_holder)
        strip.setContentsMargins(SPACE_4, SPACE_3, SPACE_4, SPACE_3)
        strip.setSpacing(SPACE_4)

        today_stack = QVBoxLayout()
        today_stack.setSpacing(SPACE_1)
        today_stack.addWidget(self._strip_label("TODAY"))
        self._today_value = QLabel("0 words")
        self._today_value.setObjectName("dashValue")
        self._today_value.setFont(QFont(BODY_FONT, 20))
        today_stack.addWidget(self._today_value)
        self._today_sub = QLabel("No dictations yet")
        self._today_sub.setObjectName("mutedText")
        self._today_sub.setFont(QFont(BODY_FONT, FONT_SMALL))
        today_stack.addWidget(self._today_sub)
        strip.addLayout(today_stack, 1)
        strip.addWidget(self._vdivider())

        last_stack = QVBoxLayout()
        last_stack.setSpacing(SPACE_1)
        last_stack.addWidget(self._strip_label("LAST DICTATION"))
        self._last_value = QLabel("Nothing dictated yet today.")
        self._last_value.setObjectName("dashPreview")
        self._last_value.setFont(QFont(BODY_FONT, FONT_BODY))
        self._last_value.setWordWrap(True)
        last_stack.addWidget(self._last_value)
        self._last_sub = QLabel("")
        self._last_sub.setObjectName("mutedText")
        self._last_sub.setFont(QFont(BODY_FONT, FONT_SMALL))
        last_stack.addWidget(self._last_sub)
        strip.addLayout(last_stack, 2)
        strip.addWidget(self._vdivider())

        engine_stack = QVBoxLayout()
        engine_stack.setSpacing(SPACE_1)
        engine_stack.addWidget(self._strip_label("ENGINE"))
        self._model_value = QLabel("Loading model details…")
        self._model_value.setObjectName("dashValue")
        self._model_value.setFont(QFont(BODY_FONT, 20))
        self._model_value.setWordWrap(True)
        engine_stack.addWidget(self._model_value)
        self._engine_sub = QLabel("")
        self._engine_sub.setObjectName("mutedText")
        self._engine_sub.setFont(QFont(BODY_FONT, FONT_SMALL))
        engine_stack.addWidget(self._engine_sub)
        strip.addLayout(engine_stack, 1)

        outer.addWidget(strip_holder)

        self._elapsed = 0
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)

    def _strip_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("dictationMetaLabel")
        return label

    def _vdivider(self) -> QFrame:
        line = QFrame()
        line.setObjectName("stripDivider")
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        return line

    def set_stats(self, words: int, dictations: int) -> None:
        self._today_value.setText(f"{words} words")
        if dictations <= 0:
            self._today_sub.setText("No dictations yet")
        elif dictations == 1:
            self._today_sub.setText("1 dictation")
        else:
            self._today_sub.setText(f"{dictations} dictations")

    def set_last(self, preview: str, meta: str = "") -> None:
        cleaned = " ".join((preview or "").split())
        if not cleaned:
            self._last_value.setText("Nothing dictated yet today.")
            self._last_sub.setText("")
        elif len(cleaned) > 140:
            self._last_value.setText(cleaned[:140].rstrip() + "…")
            self._last_sub.setText(meta)
        else:
            self._last_value.setText(cleaned)
            self._last_sub.setText(meta)

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        if state == "recording":
            self._state_badge.setText("●  Listening")
            self._state_badge.setProperty("state", "recording")
            self._stage_status.setText("Microphone active")
            self._hint.setText("Release to transcribe · Esc to cancel")
            self._elapsed = 0
            self._hero.setText(HERO_RECORDING)
            self._tick.start()
        elif state == "draining":
            self._state_badge.setText("●  Transcribing")
            self._state_badge.setProperty("state", "draining")
            self._stage_status.setText("Creating your transcript")
            self._hint.setText("Hold on…")
            self._hero.setText(HERO_DRAINING)
            self._tick.stop()
        else:
            self._state_badge.setText("●  Ready")
            self._state_badge.setProperty("state", "idle")
            self._stage_status.setText("On-device microphone ready")
            self._hint.setText(
                "Hold the shortcut, speak naturally, then release to insert."
            )
            self._hero.setText(HERO_IDLE)
            self._tick.stop()
            self.clear_interim()
        self._state_badge.style().unpolish(self._state_badge)
        self._state_badge.style().polish(self._state_badge)
        self._hero_animation.stop()
        self._hero_animation.start()
        self._ring.set_state(state)

    def _on_tick(self) -> None:
        self._elapsed += 1
        minutes, seconds = divmod(self._elapsed, 60)
        self._hero.setText(f"{HERO_RECORDING} · {minutes:02d}:{seconds:02d}")

    def push_level(self, level: float) -> None:
        self._ring.push_level(level)

    def set_interim(self, text: str) -> None:
        cleaned = " ".join(text.split())
        if cleaned and cleaned != self._interim.text().lstrip("… "):
            self._interim.setText(f"… {cleaned}")
            self._interim.show()

    def clear_interim(self) -> None:
        if self._interim.text():
            self._interim.setText("")

    def set_meta(self, text: str) -> None:
        self._model_value.setText(text)

    def set_engine_sub(self, text: str) -> None:
        self._engine_sub.setText(text)

    def set_shortcut(self, shortcut: str) -> None:
        try:
            self._shortcut_display = display_hotkey(shortcut)
        except ValueError:
            self._shortcut_display = "Ctrl + Alt + SPACE"
        self._rebuild_keycaps()

    def _rebuild_keycaps(self) -> None:
        while self._keys_box.count():
            item = self._keys_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        parts = [part.strip() for part in self._shortcut_display.split("+")]
        for index, part in enumerate(parts):
            if index > 0:
                plus = QLabel("+")
                plus.setObjectName("mutedText")
                plus.setFont(QFont(BODY_FONT, FONT_SMALL))
                self._keys_box.addWidget(plus)
            label = part.capitalize() if part.isupper() else part
            cap = QLabel(label)
            cap.setObjectName("keyCap")
            cap.setFont(QFont(MONO_FONT, FONT_SMALL))
            self._keys_box.addWidget(cap)

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
