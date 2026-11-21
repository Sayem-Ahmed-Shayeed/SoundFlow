from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QTimer,
    Qt,
    QVariantAnimation,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QPainter,
    QPen,
    QRadialGradient,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from soundflow.audio import AudioCapture, AudioCaptureError
from soundflow.core.export import ExportError, export_transcript
from soundflow.core.segmenter import SegmenterConfig
from soundflow.core.settings import Settings, SettingsStore, default_model_path
from soundflow.core.state import DictationState, DictationStateMachine, StateChange
from soundflow.design import BODY_FONT, apply_stylesheet, stylesheet as design_stylesheet
from soundflow.design.theme import resolved_dark as _resolved_dark
from soundflow.hotkeys import (
    HotkeyError,
    canonical_hotkey,
    create_global_hotkeys,
    display_hotkey,
    hotkey_parts,
)
from soundflow.injector import InjectionError, create_text_injector
from soundflow.transcription import (
    DemoTranscriber,
    DictationPipeline,
    FasterWhisperTranscriber,
)


class UiBridge(QObject):
    text_ready = Signal(str)
    interim_ready = Signal(str)
    finished = Signal()
    error = Signal(str)
    level = Signal(float)
    audio = Signal(bytes)
    ptt_down_requested = Signal()
    ptt_up_requested = Signal()
    restore_token_ready = Signal(str)
    hotkey_ready = Signal(str)
    hotkey_error = Signal(str)
    injector_ready = Signal()
    injector_error = Signal(str)


def preferred_font(candidates: tuple[str, ...]) -> str:
    if QApplication.instance() is None:
        return candidates[-1]
    installed = set(QFontDatabase.families())
    return next((family for family in candidates if family in installed), "Sans Serif")


DISPLAY_FONT = preferred_font(("Lato Heavy", "Lato", "Noto Sans Display", "Segoe UI"))
BODY_FONT = preferred_font(("Lato", "Noto Sans", "Segoe UI", "Cantarell"))
MONO_FONT = preferred_font(("JetBrains Mono", "Cascadia Mono", "Noto Sans Mono", "DejaVu Sans Mono"))


def resolved_dark_appearance(appearance: str) -> bool:
    # Legacy shim — appearance is now restricted to "dark" / "light" by the
    # design module. Any value other than "light" resolves to dark.
    return _resolved_dark(appearance)


def macos_style_sheet(dark: bool) -> str:
    """Legacy shim — returns the centralised stylesheet from
    :mod:`soundflow.design`. New code should import
    :func:`soundflow.design.stylesheet` directly.
    """
    return design_stylesheet(dark)


class AnimatedRecordButton(QPushButton):
    """A restrained pulse used only while the microphone is active."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("recordButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(62)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setOffset(0, 8)
        self._shadow.setBlurRadius(24)
        self._shadow.setColor(QColor(99, 102, 241, 55))
        self.setGraphicsEffect(self._shadow)
        self._pulse = QVariantAnimation(self)
        self._pulse.setStartValue(0.0)
        self._pulse.setEndValue(1.0)
        self._pulse.setDuration(1250)
        self._pulse.setLoopCount(-1)
        self._pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse.valueChanged.connect(self._animate_shadow)

    def set_recording(self, recording: bool) -> None:
        self.setProperty("recording", recording)
        self.style().unpolish(self)
        self.style().polish(self)
        if recording:
            self._pulse.start()
        else:
            self._pulse.stop()
            self._shadow.setBlurRadius(24)
            self._shadow.setColor(QColor(99, 102, 241, 55))

    def _animate_shadow(self, value: object) -> None:
        amount = float(value)
        alpha = round(60 + 80 * (1.0 - abs(0.5 - amount) * 2.0))
        self._shadow.setBlurRadius(22 + 14 * amount)
        self._shadow.setColor(QColor(244, 91, 105, alpha))


class ActionButton(QPushButton):
    def __init__(
        self,
        text: str,
        handler,
        *,
        accent: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "accent" if accent else "quiet")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(handler)


class ShortcutPicker(QWidget):
    MODIFIER_CHORDS = (
        ("Ctrl", "ctrl"),
        ("Alt", "alt"),
        ("Shift", "shift"),
        ("Super", "cmd"),
        ("Ctrl + Alt", "ctrl+alt"),
        ("Ctrl + Shift", "ctrl+shift"),
        ("Alt + Shift", "alt+shift"),
        ("Ctrl + Super", "ctrl+cmd"),
    )
    KEYS = (
        ("Space", "space"),
        ("D", "d"),
        ("R", "r"),
        ("F", "f"),
        ("V", "v"),
        ("B", "b"),
        ("Return", "enter"),
        ("Tab", "tab"),
        ("F8", "f8"),
        ("F9", "f9"),
    )

    def __init__(self, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.modifiers = QComboBox()
        self.key = QComboBox()
        for label, token in self.MODIFIER_CHORDS:
            self.modifiers.addItem(label, token)
        for label, token in self.KEYS:
            self.key.addItem(label, token)
        layout.addWidget(self.modifiers)
        plus = QLabel("+")
        plus.setObjectName("shortcutPlus")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(plus)
        layout.addWidget(self.key)
        layout.addStretch(1)
        self.set_shortcut(value)

    def set_shortcut(self, value: str) -> None:
        try:
            parts = hotkey_parts(value)
        except ValueError:
            parts = hotkey_parts("ctrl+alt+space")
        modifier_set = set(parts[:-1])
        modifiers = next(
            (
                token
                for _, token in self.MODIFIER_CHORDS
                if set(token.split("+")) == modifier_set
            ),
            "ctrl+alt",
        )
        key = parts[-1]
        modifier_index = self.modifiers.findData(modifiers)
        key_index = self.key.findData(key)
        self.modifiers.setCurrentIndex(max(0, modifier_index))
        self.key.setCurrentIndex(max(0, key_index))

    def shortcut(self) -> str:
        return canonical_hotkey(
            f"{self.modifiers.currentData()}+{self.key.currentData()}"
        )


class WaveformWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self._level = 0.15
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._level = 0.15
        self.update()

    def set_level(self, level: float) -> None:
        self._level = 0.68 * self._level + 0.32 * max(0.08, min(level, 1.0))

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 12
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        from soundflow.design.theme import current_palette

        painter.setBrush(QColor(current_palette()["record"]))
        bar_width = 3
        gap = 3
        center = self.height() / 2
        for index in range(7):
            wave = abs(((index + self._phase) % 8) - 3.5) / 3.5
            height = 4 + self._level * (17 - 8 * wave)
            x = index * (bar_width + gap) + 1
            painter.drawRoundedRect(
                int(x),
                int(center - height / 2),
                bar_width,
                max(2, int(height)),
                2,
                2,
            )


class VoiceOrb(QWidget):
    """Low-cost microphone visualizer shared by all dictation states."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.setMaximumHeight(190)
        self._level = 0.08
        self._phase = 0.0
        self._state = "idle"
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self._timer.stop()

    def set_level(self, level: float) -> None:
        self._level = 0.72 * self._level + 0.28 * max(0.04, min(level, 1.0))

    def set_state(self, state: str) -> None:
        self._state = state
        if state not in {"recording", "draining"}:
            self._level = 0.08
        self.update()

    def _tick(self) -> None:
        if not self.isVisible():
            return
        self._phase = (self._phase + 0.025) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        base = min(self.width(), self.height()) * 0.27
        pulse = 3.0 * abs(0.5 - self._phase) if self._state == "idle" else 0.0
        amplitude = self._level * 15 if self._state == "recording" else pulse
        accent = QColor("#d94d62" if self._state == "recording" else "#7367f0")
        if self._state == "draining":
            accent = QColor("#5b93f5")

        glow = QRadialGradient(center, base + 28)
        glow.setColorAt(0.2, QColor(accent.red(), accent.green(), accent.blue(), 65))
        glow.setColorAt(1.0, QColor(accent.red(), accent.green(), accent.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(center, int(base + 32 + amplitude), int(base + 32 + amplitude))

        for ring in range(3):
            radius = base + 12 + ring * 10 + amplitude * (0.35 + ring * 0.2)
            color = QColor(accent)
            color.setAlpha(145 - ring * 35)
            pen = QPen(color, 2 if ring == 0 else 1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, int(radius), int(radius))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(center, int(base), int(base))
        ink = QColor("#29292f")
        stem = int(base * 0.42)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ink)
        painter.drawRoundedRect(
            int(center.x() - 7),
            int(center.y() - stem),
            14,
            int(stem * 1.35),
            7,
            7,
        )
        painter.setPen(QPen(ink, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(
            int(center.x() - stem),
            int(center.y() - stem // 3),
            stem * 2,
            stem * 2,
            180 * 16,
            180 * 16,
        )
        painter.drawLine(center.x(), center.y() + stem, center.x(), center.y() + stem + 10)
        painter.drawLine(
            center.x() - 9,
            center.y() + stem + 10,
            center.x() + 9,
            center.y() + stem + 10,
        )


class RecordingOverlay(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.setObjectName("recordingOverlay")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(284, 48)
        panel = QFrame(self)
        panel.setObjectName("overlayPanel")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel.setGeometry(0, 0, 284, 48)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(12, 7, 11, 7)
        layout.setSpacing(9)
        self.waveform = WaveformWidget()
        self.label = QLabel("Listening")
        self.label.setObjectName("overlayTitle")
        self.hint = QLabel("Release to insert")
        self.hint.setObjectName("overlayHint")
        words = QVBoxLayout()
        words.setSpacing(0)
        words.addWidget(self.label)
        words.addWidget(self.hint)
        layout.addWidget(self.waveform)
        layout.addLayout(words)
        self.keycap = QLabel("CTRL + SPACE")
        self.keycap.setObjectName("overlayKeycap")
        self.keycap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.keycap)
        # Shown by a shortcut many times a day, so it appears and leaves
        # instantly; no opacity effect (which would also force offscreen
        # rendering of a translucent always-on-top window).
        self._opacity = QGraphicsOpacityEffect(self)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(150)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hide_after_fade = False
        self._fade.finished.connect(self._fade_finished)

    def show_recording(self, shortcut: str) -> None:
        self.label.setText("Listening")
        self.hint.setText("Release to insert")
        try:
            self.keycap.setText(display_hotkey(shortcut))
        except ValueError:
            self.keycap.setText(shortcut)
        self.waveform.start()
        self._show_near_cursor_screen()

    def show_processing(self) -> None:
        self.label.setText("Transcribing")
        self.hint.setText("One moment…")
        self.waveform.stop()

    def set_level(self, level: float) -> None:
        self.waveform.set_level(level)

    def hide_animated(self) -> None:
        self.waveform.stop()
        self._fade.stop()
        self._hide_after_fade = False
        self.hide()

    def _show_near_cursor_screen(self) -> None:
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(
            area.x() + (area.width() - self.width()) // 2,
            area.y() + area.height() - self.height() - 48,
        )
        self._hide_after_fade = False
        self._fade.stop()
        self.show()
        self.raise_()

    def _fade_finished(self) -> None:
        if self._hide_after_fade:
            self.hide()
            self._hide_after_fade = False


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: Settings,
        parent: QWidget | None = None,
        on_appearance_change: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("Preferences · Soundflow")
        self.setMinimumSize(820, 610)
        self.resize(900, 650)
        self.settings = settings
        self.on_appearance_change = on_appearance_change
        self.original_appearance = settings.appearance
        self.original_shortcut = settings.push_to_talk_hotkey
        title = QLabel("Preferences")
        title.setObjectName("dialogTitle")
        intro = QLabel("Choose how Soundflow looks, listens, and behaves.")
        intro.setObjectName("mutedText")
        self.tabs = QStackedWidget()
        self.tabs.addWidget(self._general_tab())
        self.tabs.addWidget(self._recognition_tab())
        self.tabs.addWidget(self._hotkeys_tab())
        settings_sidebar = QFrame()
        settings_sidebar.setObjectName("settingsSidebar")
        settings_sidebar.setFixedWidth(165)
        nav = QVBoxLayout(settings_sidebar)
        nav.setContentsMargins(10, 12, 10, 12)
        nav.setSpacing(6)
        self.settings_nav_group = QButtonGroup(self)
        self.settings_nav_group.setExclusive(True)
        self.settings_nav_buttons: list[QPushButton] = []
        for index, label in enumerate(("General", "Recognition", "Shortcuts")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName("navActive" if index == 0 else "navButton")
            button.clicked.connect(
                lambda checked=False, page=index: self._select_settings_page(page)
            )
            self.settings_nav_group.addButton(button, index)
            self.settings_nav_buttons.append(button)
            nav.addWidget(button)
        self.settings_nav_buttons[0].setChecked(True)
        nav.addStretch(1)
        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(settings_sidebar)
        body.addWidget(self.tabs, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Save changes")
        save_button.setProperty("role", "accent")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addSpacing(12)
        layout.addLayout(body, 1)
        layout.addSpacing(10)
        layout.addWidget(buttons)

    def _select_settings_page(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)
        for button_index, button in enumerate(self.settings_nav_buttons):
            button.setObjectName(
                "navActive" if button_index == index else "navButton"
            )
            button.style().unpolish(button)
            button.style().polish(button)

    def _general_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 8, 14)
        layout.setSpacing(14)

        appearance_card = QFrame()
        appearance_card.setObjectName("settingsCard")
        appearance_layout = QVBoxLayout(appearance_card)
        appearance_layout.setContentsMargins(20, 18, 20, 18)
        appearance_layout.setSpacing(8)
        heading = QLabel("Appearance")
        heading.setObjectName("sectionTitle")
        hint = QLabel("Choose a theme or match your system.")
        hint.setObjectName("mutedText")
        self.appearance = QComboBox()
        self.appearance.setObjectName("appearancePicker")
        for label, value in (
            ("Light", "light"),
            ("Dark", "dark"),
        ):
            self.appearance.addItem(label, value)
        self.appearance.setCurrentIndex(
            max(0, self.appearance.findData(self.settings.appearance))
        )
        self.appearance.currentIndexChanged.connect(self._preview_appearance)
        appearance_layout.addWidget(heading)
        appearance_layout.addWidget(hint)
        appearance_layout.addWidget(self.appearance)
        layout.addWidget(appearance_card)

        behavior_card = QFrame()
        behavior_card.setObjectName("settingsCard")
        form = QFormLayout(behavior_card)
        self._prepare_form(form)
        self.silence = QSpinBox()
        self.silence.setRange(200, 3000)
        self.silence.setSuffix(" ms")
        self.silence.setValue(self.settings.silence_duration_ms)
        self.silence.setMaximumWidth(180)
        form.addRow("Finish after silence", self.silence)
        self.auto_copy = QCheckBox("Copy every completed phrase")
        self.auto_copy.setChecked(self.settings.auto_copy)
        form.addRow(self.auto_copy)
        self.start_minimized = QCheckBox("Start in the system tray")
        self.start_minimized.setChecked(self.settings.start_minimized)
        form.addRow(self.start_minimized)
        layout.addWidget(behavior_card)
        layout.addStretch(1)
        return page

    def _recognition_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        form = QFormLayout(page)
        self._prepare_form(form)
        self.model_path = QLineEdit(self.settings.model_path or str(default_model_path()))
        self.model_path.setClearButtonEnabled(True)
        browse = QPushButton("Browse")
        browse.setProperty("role", "quiet")
        browse.clicked.connect(self._browse_model)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.model_path, 1)
        row.addWidget(browse)
        form.addRow("Model directory", row)

        self.language = QLineEdit(self.settings.language)
        self.language.setPlaceholderText("auto, en, bn, …")
        self.language.setMaximumWidth(240)
        form.addRow("Language", self.language)

        self.device = QComboBox()
        self.device.addItems(["cpu", "cuda"])
        self.device.setCurrentText(self.settings.inference_device)
        self.device.setMaximumWidth(240)
        form.addRow("Processing", self.device)

        precision = QLabel("INT8")
        precision.setObjectName("fixedValue")
        precision.setToolTip("Soundflow uses INT8 for reliable CPU performance")
        form.addRow("Precision", precision)

        self.microphone = QComboBox()
        self.microphone.addItem("System default", None)
        for index, name in AudioCapture.list_input_devices():
            self.microphone.addItem(name, index)
            if index == self.settings.microphone:
                self.microphone.setCurrentIndex(self.microphone.count() - 1)
        form.addRow("Microphone", self.microphone)
        note = QLabel("The bundled small model is a good balance of speed and accuracy.")
        note.setObjectName("formHint")
        note.setWordWrap(True)
        form.addRow("", note)
        return page

    def _hotkeys_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        form = QFormLayout(page)
        self._prepare_form(form)
        self.hotkeys_enabled = QCheckBox(
            "Listen for shortcuts while Soundflow is in the background"
        )
        self.hotkeys_enabled.setChecked(self.settings.global_hotkeys)
        form.addRow(self.hotkeys_enabled)
        self.ptt_picker = ShortcutPicker(self.settings.push_to_talk_hotkey)
        form.addRow("Hold to dictate", self.ptt_picker)
        note = QLabel(
            "Choose a modifier chord and one trigger key. On Wayland, your desktop "
            "will ask once for permission to use this system-wide shortcut."
        )
        note.setObjectName("formHint")
        note.setWordWrap(True)
        form.addRow("", note)
        return page

    @staticmethod
    def _prepare_form(form: QFormLayout) -> None:
        form.setContentsMargins(4, 20, 4, 16)
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(16)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _browse_model(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose faster-whisper model")
        if selected:
            self.model_path.setText(selected)

    def _preview_appearance(self) -> None:
        appearance = str(self.appearance.currentData())
        self.settings.appearance = appearance
        if self.on_appearance_change:
            self.on_appearance_change(appearance)

    def reject(self) -> None:
        self.settings.appearance = self.original_appearance
        if self.on_appearance_change:
            self.on_appearance_change(self.original_appearance)
        super().reject()

    def _save(self) -> None:
        self.settings.appearance = str(self.appearance.currentData())
        self.settings.model_path = self.model_path.text().strip()
        self.settings.language = self.language.text().strip() or "auto"
        self.settings.inference_device = self.device.currentText()
        self.settings.compute_type = "int8"
        self.settings.microphone = self.microphone.currentData()
        self.settings.global_hotkeys = self.hotkeys_enabled.isChecked()
        shortcut = self.ptt_picker.shortcut()
        if shortcut != self.original_shortcut:
            self.settings.hotkey_authorized = False
        self.settings.push_to_talk_hotkey = shortcut
        self.settings.silence_duration_ms = self.silence.value()
        self.settings.auto_copy = self.auto_copy.isChecked()
        self.settings.start_minimized = self.start_minimized.isChecked()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Settings,
        store: SettingsStore,
        demo_mode: bool = False,
        no_hotkeys: bool = False,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.store = store
        self.demo_mode = demo_mode
        self.no_hotkeys = no_hotkeys
        self.hotkeys = None
        self._hotkey_is_ready = False
        # Ask the desktop for the shortcut at launch instead of waiting for a
        # click; the desktop shows its own one-time approval prompt.
        self._hotkey_setup_requested = bool(
            settings.global_hotkeys and not no_hotkeys and not demo_mode
        )
        self._injector_started = False
        self._injector_is_ready = False
        self._setup_retry_target = "hotkey"
        self.pipeline: DictationPipeline | None = None
        self._auto_insert_after_drain = False
        self._session_fragments: list[str] = []
        self.bridge = UiBridge()
        self.state = DictationStateMachine(self._state_changed)
        self._build_ui()
        self.apply_appearance(self.settings.appearance)
        color_scheme_changed = getattr(
            QGuiApplication.styleHints(), "colorSchemeChanged", None
        )
        if color_scheme_changed is not None:
            color_scheme_changed.connect(self._system_appearance_changed)
        self._connect_bridge()
        self.portal_parent_window = (
            f"x11:{int(self.winId()):x}"
            if QApplication.platformName().lower() == "xcb"
            else ""
        )
        self.injector = create_text_injector(
            self.settings.remote_desktop_restore_token,
            self.bridge.restore_token_ready.emit,
            self.bridge.injector_error.emit,
            self.bridge.injector_ready.emit,
            self.portal_parent_window,
        )
        self._build_tray()
        self._apply_state(DictationState.IDLE, "Ready")
        QTimer.singleShot(0, self._rebuild_runtime)

    def _build_ui(self) -> None:
        self.setWindowTitle("Soundflow · Private Dictation")
        self.setMinimumSize(860, 600)
        self.resize(1080, 700)
        QApplication.instance().setFont(QFont(BODY_FONT, 10, QFont.Weight.Normal))

        container = QWidget()
        container.setObjectName("mainSurface")
        shell = QHBoxLayout(container)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(216)
        rail = QVBoxLayout(sidebar)
        rail.setContentsMargins(24, 28, 24, 24)
        rail.setSpacing(8)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_mark = QLabel("S")
        brand_mark.setObjectName("brandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("soundflow")
        brand.setObjectName("brand")
        brand_row.addWidget(brand_mark)
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        rail.addLayout(brand_row)
        rail.addSpacing(34)

        home_nav = QPushButton("  Home")
        home_nav.setObjectName("navActive")
        home_nav.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        home_nav.setCursor(Qt.CursorShape.PointingHandCursor)
        rail.addWidget(home_nav)
        settings_nav = QPushButton("  Preferences")
        settings_nav.setObjectName("navButton")
        settings_nav.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        settings_nav.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_nav.clicked.connect(self.open_settings)
        rail.addWidget(settings_nav)
        rail.addStretch(1)

        privacy_card = QFrame()
        privacy_card.setObjectName("privacyCard")
        privacy_layout = QVBoxLayout(privacy_card)
        privacy_layout.setContentsMargins(14, 13, 14, 13)
        privacy_layout.setSpacing(4)
        privacy = QLabel("●  PRIVATE & OFFLINE")
        privacy.setObjectName("privacyPill")
        privacy.setToolTip("Audio and transcripts never leave this device")
        privacy_copy = QLabel("Your voice stays on this computer.")
        privacy_copy.setObjectName("railCaption")
        privacy_copy.setWordWrap(True)
        privacy_layout.addWidget(privacy)
        privacy_layout.addWidget(privacy_copy)
        rail.addWidget(privacy_card)
        shell.addWidget(sidebar)

        workspace = QWidget()
        workspace.setObjectName("workspace")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title = QLabel("Dictation")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Speak naturally. Soundflow types for you.")
        subtitle.setObjectName("mutedText")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        header.addLayout(title_stack)
        header.addStretch(1)
        language_label = QLabel("LANGUAGE")
        language_label.setObjectName("fieldLabel")
        header.addWidget(language_label)
        self.language_picker = QComboBox()
        for label, code in (
            ("Auto detect", "auto"),
            ("English", "en"),
            ("বাংলা", "bn"),
            ("Hindi", "hi"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de"),
            ("Japanese", "ja"),
        ):
            self.language_picker.addItem(label, code)
        language_index = self.language_picker.findData(self.settings.language)
        self.language_picker.setCurrentIndex(max(0, language_index))
        self.language_picker.setAccessibleName("Dictation language")
        self.language_picker.currentIndexChanged.connect(self._home_language_changed)
        header.addWidget(self.language_picker)
        layout.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(18)

        control = QFrame()
        control.setObjectName("controlPanel")
        control.setFixedWidth(360)
        hero_layout = QVBoxLayout(control)
        hero_layout.setContentsMargins(26, 22, 26, 22)
        hero_layout.setSpacing(12)

        self.voice_orb = VoiceOrb()
        hero_layout.addWidget(self.voice_orb, 0, Qt.AlignmentFlag.AlignHCenter)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setProperty("state", "idle")
        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status, 1)
        hero_layout.addLayout(status_row)

        self.status_caption = QLabel("Hold your shortcut or click to start.")
        self.status_caption.setObjectName("mutedText")
        self.status_caption.setWordWrap(True)
        hero_layout.addWidget(self.status_caption)
        hero_layout.addStretch(1)

        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setFixedHeight(4)
        self.meter.setAccessibleName("Microphone input level")
        hero_layout.addWidget(self.meter)

        self.record_button = AnimatedRecordButton("●   Start listening")
        self.record_button.clicked.connect(self.toggle_dictation)
        hero_layout.addWidget(self.record_button)

        shortcut_card = QFrame()
        shortcut_card.setObjectName("shortcutCard")
        shortcut_layout = QVBoxLayout(shortcut_card)
        shortcut_layout.setContentsMargins(12, 10, 12, 10)
        shortcut_layout.setSpacing(5)
        shortcut_title = QLabel("Hold anywhere to dictate")
        shortcut_title.setObjectName("fieldLabel")
        shortcut_layout.addWidget(shortcut_title)
        shortcut_row = QHBoxLayout()
        shortcut_row.setSpacing(6)
        self.ptt_keycaps: list[QLabel] = []
        self.ptt_pluses: list[QLabel] = []
        for index in range(3):
            keycap = QLabel(("CTRL", "ALT", "SPACE")[index])
            keycap.setObjectName("keycap")
            shortcut_row.addWidget(keycap)
            self.ptt_keycaps.append(keycap)
            if index < 2:
                plus = QLabel("+")
                plus.setObjectName("shortcutPlus")
                shortcut_row.addWidget(plus)
                self.ptt_pluses.append(plus)
        shortcut_row.addStretch(1)
        shortcut_layout.addLayout(shortcut_row)
        hero_layout.addWidget(shortcut_card)

        self.hotkey_indicator = QLabel("●  STARTING GLOBAL SHORTCUT…")
        self.hotkey_indicator.setObjectName("hotkeyIndicator")
        self.hotkey_indicator.setProperty("state", "connecting")
        self.hotkey_indicator.setWordWrap(True)
        hero_layout.addWidget(self.hotkey_indicator)
        self.hotkey_retry_button = QPushButton("Set up global shortcut")
        self.hotkey_retry_button.setObjectName("hotkeyRetry")
        self.hotkey_retry_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hotkey_retry_button.clicked.connect(self.retry_setup)
        self.hotkey_retry_button.hide()
        hero_layout.addWidget(self.hotkey_retry_button)
        content.addWidget(control)

        transcript = QFrame()
        transcript.setObjectName("transcriptPanel")
        transcript_layout = QVBoxLayout(transcript)
        transcript_layout.setContentsMargins(22, 20, 22, 18)
        transcript_layout.setSpacing(12)
        transcript_header = QHBoxLayout()
        transcript_header.setSpacing(8)
        transcript_title = QLabel("Transcript")
        transcript_title.setObjectName("sectionTitle")
        self.word_count = QLabel("0 words")
        self.word_count.setObjectName("wordCount")
        transcript_header.addWidget(transcript_title)
        transcript_header.addStretch(1)
        transcript_header.addWidget(self.word_count)
        transcript_layout.addLayout(transcript_header)

        self.editor = QTextEdit()
        self.editor.setObjectName("transcriptEditor")
        self.editor.setPlaceholderText("Your words will appear here…")
        self.editor.setAcceptRichText(False)
        self.editor.setAccessibleName("Transcript editor")
        self.editor.setFont(QFont(BODY_FONT, 12))
        self.editor.textChanged.connect(self._update_word_count)
        transcript_layout.addWidget(self.editor, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(ActionButton("Copy", self.copy_text))
        actions.addWidget(ActionButton("Export", self.save_text))
        actions.addStretch(1)
        actions.addWidget(ActionButton("Clear", self.clear_text))
        actions.addWidget(ActionButton("Insert text", self.insert_text, accent=True))
        transcript_layout.addLayout(actions)
        content.addWidget(transcript, 1)
        layout.addLayout(content, 1)

        system_row = QHBoxLayout()
        system_row.setSpacing(16)
        model_name = Path(
            self.settings.model_path or default_model_path()
        ).name.replace("faster-whisper-", "").replace("-", " ").title()
        self.model_status = QLabel(f"◈  {model_name or 'Whisper Small'} · INT8")
        self.model_status.setObjectName("mutedText")
        self.device_status = QLabel(f"▣  {self.settings.inference_device.upper()}")
        self.device_status.setObjectName("mutedText")
        self.microphone_status = QLabel("♩  System microphone")
        self.microphone_status.setObjectName("mutedText")
        system_row.addStretch(1)
        system_row.addWidget(self.model_status)
        system_row.addWidget(self.device_status)
        system_row.addWidget(self.microphone_status)
        system_row.addStretch(1)
        layout.addLayout(system_row)
        shell.addWidget(workspace, 1)
        self.setCentralWidget(container)

        self.level_animation = QPropertyAnimation(self.meter, b"value", self)
        self.level_animation.setDuration(110)
        self.level_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        status_opacity = QGraphicsOpacityEffect(self.status)
        self.status.setGraphicsEffect(status_opacity)
        self.status_animation = QPropertyAnimation(status_opacity, b"opacity", self)
        self.status_animation.setDuration(220)
        self.status_animation.setStartValue(0.35)
        self.status_animation.setEndValue(1.0)
        self.status_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        QApplication.instance().setStyleSheet(
            f"""
            QMainWindow, QDialog#settingsDialog {{ background: #0d0e12; }}
            QWidget {{
                color: #f1f3f5;
                font-family: "{BODY_FONT}";
                font-size: 13px;
            }}
            QWidget#mainSurface, QWidget#workspace {{ background: #0d0e12; }}
            QFrame#sidebar {{
                background: #111216;
                border-right: 1px solid #222329;
            }}
            QLabel#brandMark {{
                color: #111216;
                background: #f0efea;
                border-radius: 10px;
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                font-family: "{DISPLAY_FONT}";
                font-size: 18px;
                font-weight: 900;
            }}
            QLabel#brand {{
                color: #f7f6f2;
                font-family: "{DISPLAY_FONT}";
                font-size: 18px;
                font-weight: 800;
            }}
            QLabel#pageTitle, QLabel#dialogTitle {{
                color: #faf9f5;
                font-family: "{DISPLAY_FONT}";
                font-size: 25px;
                font-weight: 800;
            }}
            QPushButton#navActive, QPushButton#navButton {{
                min-height: 25px;
                padding: 10px 12px;
                text-align: left;
                border: none;
                border-radius: 9px;
                font-weight: 600;
            }}
            QPushButton#navActive {{ color: #f6f5f1; background: #27282e; }}
            QPushButton#navButton {{ color: #888b94; background: transparent; }}
            QPushButton#navButton:hover {{ color: #f6f5f1; background: #1b1c21; }}
            QFrame#privacyCard {{
                background: #171b19;
                border: 1px solid #25332d;
                border-radius: 11px;
            }}
            QLabel#railCaption {{ color: #737c77; font-size: 10px; }}
            QLabel#fieldLabel {{
                color: #6f727c;
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#hotkeyIndicator {{
                color: #b6bac3;
                background: #1a1b20;
                border: 1px solid #2b2c33;
                border-radius: 9px;
                padding: 10px 11px;
                font-family: "{MONO_FONT}";
                font-size: 9px;
                font-weight: 700;
            }}
            QLabel#hotkeyIndicator[state="ready"] {{
                color: #8dd6b5;
                background: #171b19;
                border-color: #294036;
            }}
            QLabel#hotkeyIndicator[state="recording"] {{
                color: #ff9aa4;
                background: #26171a;
                border-color: #573037;
            }}
            QLabel#hotkeyIndicator[state="error"] {{
                color: #f1bd75;
                background: #241d15;
                border-color: #493722;
            }}
            QPushButton#hotkeyRetry {{
                color: #f1bd75;
                background: transparent;
                border-color: #493722;
            }}
            QPushButton#hotkeyRetry:hover {{
                color: #ffe0ae;
                background: #241d15;
            }}
            QLabel#eyebrow {{
                color: #717784;
                font-family: "{MONO_FONT}";
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
            }}
            QLabel#privacyPill {{
                color: #8dd6b5;
                font-family: "{MONO_FONT}";
                font-size: 9px;
                font-weight: 700;
            }}
            QFrame#controlPanel, QFrame#transcriptPanel {{
                background: #141519;
                border: 1px solid #25262d;
                border-radius: 15px;
            }}
            QFrame#shortcutCard {{
                background: #1a1b20;
                border: 1px solid #292a31;
                border-radius: 10px;
            }}
            QLabel#status {{
                color: #ffffff;
                font-family: "{DISPLAY_FONT}";
                font-size: 17px;
                font-weight: 800;
            }}
            QLabel#statusDot {{ color: #8b92a1; font-size: 13px; }}
            QLabel#statusDot[state="recording"] {{ color: #f45b69; }}
            QLabel#statusDot[state="draining"] {{ color: #f2bd5c; }}
            QLabel#statusDot[state="error"] {{ color: #f45b69; }}
            QLabel#mutedText, QLabel#formHint {{
                color: #8b92a1;
                font-size: 12px;
            }}
            QLabel#formHint {{ padding-top: 3px; }}
            QLabel#shortcutHint {{
                color: #666d79;
                font-size: 10px;
                padding-top: 2px;
            }}
            QLabel#keycap, QLabel#overlayKeycap {{
                color: #dce0e8;
                background: #1a1d24;
                border: 1px solid #343945;
                border-radius: 6px;
                padding: 4px 7px;
                font-family: "{MONO_FONT}";
                font-size: 9px;
                font-weight: 700;
            }}
            QLabel#shortcutPlus {{ color: #666d79; font-family: "{MONO_FONT}"; }}
            QLabel#fixedValue {{
                color: #cfd3dc;
                background: #151820;
                border: 1px solid #292d37;
                border-radius: 7px;
                padding: 7px 10px;
                font-family: "{MONO_FONT}";
                font-weight: 700;
            }}
            QFrame#overlayPanel {{
                background: #111318;
                border: 1px solid #30343f;
                border-radius: 18px;
            }}
            QLabel#overlayTitle {{
                color: #ffffff;
                font-family: "{DISPLAY_FONT}";
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#overlayHint {{ color: #858b97; font-size: 10px; }}
            QLabel#sectionTitle {{
                color: #dfe2e8;
                font-family: "{DISPLAY_FONT}";
                font-size: 14px;
                font-weight: 650;
            }}
            QLabel#wordCount {{
                color: #666d79;
                font-family: "{MONO_FONT}";
                font-size: 10px;
            }}
            QPushButton {{
                min-height: 20px;
                background: #151820;
                color: #cbd0da;
                border: 1px solid #292d37;
                border-radius: 9px;
                padding: 9px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #1c2029; color: #ffffff; border-color: #383d49; }}
            QPushButton:pressed {{ background: #101218; }}
            QPushButton[role="accent"] {{
                color: #ffffff;
                background: #5b5ce2;
                border-color: #6a6bf0;
            }}
            QPushButton[role="accent"]:hover {{ background: #6869ea; }}
            QPushButton[role="quiet"] {{ background: transparent; }}
            QPushButton#recordButton {{
                color: #17171a;
                background: #e9e7df;
                border: 1px solid #f8f6ee;
                border-radius: 12px;
                padding: 15px 22px;
                font-family: "{DISPLAY_FONT}";
                font-size: 14px;
                font-weight: 800;
            }}
            QPushButton#recordButton:hover {{ background: #ffffff; }}
            QPushButton#recordButton[recording="true"] {{
                background: #d94d5c;
                border-color: #f06b78;
            }}
            QPushButton#recordButton[recording="true"]:hover {{ background: #e15564; }}
            QPushButton#recordButton:disabled {{
                color: #858b97;
                background: #1c1f26;
                border-color: #292d35;
            }}
            QTextEdit, QLineEdit, QComboBox, QSpinBox {{
                color: #e9ecf1;
                background: #101217;
                border: 1px solid #262a33;
                border-radius: 9px;
                padding: 8px 10px;
                selection-background-color: #5b5ce2;
            }}
            QTextEdit#transcriptEditor {{
                background: transparent;
                border: none;
                border-top: 1px solid #24252b;
                border-radius: 0px;
                padding: 18px 2px;
            }}
            QTextEdit#transcriptEditor:focus {{ border-top-color: #34353d; }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: #5b5ce2; }}
            QComboBox {{
                min-width: 118px;
                padding-right: 22px;
            }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox QAbstractItemView {{
                background: #171a21;
                border: 1px solid #30343e;
                selection-background-color: #5b5ce2;
                padding: 4px;
            }}
            QProgressBar {{ background: #232630; border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: #6b6cf0; border-radius: 2px; }}
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{
                color: #858b97;
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 10px 14px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{ color: #ffffff; border-bottom-color: #6869ea; }}
            QCheckBox {{ spacing: 9px; }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                background: #101217;
                border: 1px solid #3a3f4a;
                border-radius: 4px;
            }}
            QCheckBox::indicator:checked {{ background: #5b5ce2; border-color: #7172ef; }}
            QStatusBar {{
                color: #aeb3bd;
                background: #101217;
                border-top: 1px solid #20232b;
                padding-left: 10px;
            }}
            """
        )
        self.statusBar().setSizeGripEnabled(False)
        self.overlay = RecordingOverlay()

    def apply_appearance(self, appearance: str) -> None:
        self.settings.appearance = (
            appearance if appearance in {"light", "dark"} else "dark"
        )
        dark = resolved_dark_appearance(self.settings.appearance)
        apply_stylesheet(QApplication.instance(), dark)
        self.setProperty("darkAppearance", dark)
        if hasattr(self, "overlay"):
            self.overlay.setProperty("darkAppearance", dark)
            self.overlay.update()

    @Slot()
    def _system_appearance_changed(self, *args) -> None:
        del args
        # "System" appearance is no longer supported; ignore the Qt signal.
        pass

    def _connect_bridge(self) -> None:
        self.bridge.text_ready.connect(self._append_text)
        self.bridge.interim_ready.connect(self._interim_text)
        self.bridge.finished.connect(self._pipeline_finished)
        self.bridge.error.connect(self._show_runtime_error)
        self.bridge.level.connect(self._set_level)
        self.bridge.ptt_down_requested.connect(self._ptt_down)
        self.bridge.ptt_up_requested.connect(self._ptt_up)
        self.bridge.restore_token_ready.connect(self._save_restore_token)
        self.bridge.hotkey_ready.connect(self._hotkey_ready)
        self.bridge.hotkey_error.connect(self._hotkey_failed)
        self.bridge.injector_ready.connect(self._injector_ready)
        self.bridge.injector_error.connect(self._injector_failed)

    def _build_tray(self) -> None:
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        menu = self.tray.contextMenu()
        if menu is None:
            from PySide6.QtWidgets import QMenu

            menu = QMenu()
            self.tray.setContextMenu(menu)
        show_action = QAction("Open Soundflow", self)
        show_action.triggered.connect(self._show_window)
        toggle_action = QAction("Start / stop dictation", self)
        toggle_action.triggered.connect(self.toggle_dictation)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._request_application_quit)
        menu.addAction(show_action)
        menu.addAction(toggle_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.activated.connect(
            lambda reason: self._show_window()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        else:
            QApplication.instance().setQuitOnLastWindowClosed(True)

    def _rebuild_runtime(self, *, force_hotkeys: bool = False) -> None:
        # Keep a working global shortcut when only audio/model settings
        # changed; restarting it re-runs the desktop's portal handshake.
        hotkey_signature = (
            self.settings.global_hotkeys,
            self.settings.push_to_talk_hotkey,
            self.no_hotkeys,
        )
        keep_hotkeys = (
            not force_hotkeys
            and self.hotkeys is not None
            and self._hotkey_is_ready
            and getattr(self, "_hotkey_signature", None) == hotkey_signature
        )
        if self.pipeline:
            self.pipeline.close()
        if not keep_hotkeys:
            self._hotkey_is_ready = False
            if self.hotkeys:
                self.hotkeys.stop()
                self.hotkeys = None

        transcriber = (
            DemoTranscriber()
            if self.demo_mode
            else FasterWhisperTranscriber(
                Path(self.settings.model_path or default_model_path()),
                language=self.settings.language,
                device=self.settings.inference_device,
                compute_type=self.settings.compute_type,
            )
        )
        config = SegmenterConfig(
            threshold=self.settings.silence_threshold,
            silence_ms=self.settings.silence_duration_ms,
            min_speech_ms=self.settings.min_speech_ms,
            max_speech_s=self.settings.max_speech_s,
        )
        self.pipeline = DictationPipeline(
            transcriber,
            config,
            self.bridge.text_ready.emit,
            self.bridge.finished.emit,
            self.bridge.error.emit,
            self.bridge.level.emit,
            self.bridge.interim_ready.emit,
            on_audio=self.bridge.audio.emit,
        )
        self._preload_model(transcriber)
        if keep_hotkeys:
            self._refresh_shortcut_display()
            return
        self._hotkey_signature = hotkey_signature
        should_start_hotkey = (
            self.settings.hotkey_authorized or self._hotkey_setup_requested
        )
        if (
            self.settings.global_hotkeys
            and not self.no_hotkeys
            and should_start_hotkey
        ):
            self._set_hotkey_indicator("connecting", "●  CONNECTING GLOBAL SHORTCUT…")
            try:
                self.hotkeys = create_global_hotkeys(
                    self.settings.push_to_talk_hotkey,
                    self.bridge.ptt_down_requested.emit,
                    self.bridge.ptt_up_requested.emit,
                    self.bridge.hotkey_error.emit,
                    self.bridge.hotkey_ready.emit,
                    self.portal_parent_window,
                )
                self.hotkeys.start()
            except HotkeyError as exc:
                self.hotkeys = None
                QTimer.singleShot(0, lambda message=str(exc): self._hotkey_failed(message))
        elif self.no_hotkeys:
            self._set_hotkey_indicator("error", "●  GLOBAL SHORTCUT DISABLED")
        elif self.settings.global_hotkeys:
            self._set_hotkey_indicator(
                "error",
                "●  SETUP REQUIRED · AUTHORIZE CTRL + ALT + SPACE",
                retry="hotkey",
            )
        else:
            self._set_hotkey_indicator(
                "error", "●  ENABLE SHORTCUTS IN PREFERENCES"
            )
            self._start_injector()
        self._refresh_shortcut_display()

    def _preload_model(self, transcriber) -> None:
        """Load the speech model in the background so the first dictation is instant."""
        preload = getattr(transcriber, "preload", None)
        if not callable(preload):
            return

        def run() -> None:
            try:
                preload()
            except Exception:
                pass  # Reported with a clear message when dictation starts.

        threading.Thread(target=run, name="soundflow-model-preload", daemon=True).start()

    @Slot()
    def toggle_dictation(self) -> None:
        current = self.state.state
        if current in {DictationState.IDLE, DictationState.ERROR}:
            self._start_dictation(auto_insert=False)
        elif current in {DictationState.RECORDING, DictationState.PAUSED}:
            self._stop_dictation()

    def _start_dictation(self, *, auto_insert: bool) -> None:
        if not self.demo_mode:
            model_path = Path(self.settings.model_path or default_model_path())
            required = (model_path / "model.bin", model_path / "config.json")
            if not all(item.is_file() for item in required):
                message = (
                    f"No complete offline model was found at {model_path}. "
                    "Choose a local faster-whisper model in Settings."
                )
                self.state.fail(message)
                self._show_runtime_error(message)
                return
        try:
            assert self.pipeline is not None
            self._auto_insert_after_drain = auto_insert
            self._session_fragments.clear()
            self.pipeline.start(self.settings.microphone)
            self.state.start("user")
        except (AudioCaptureError, RuntimeError) as exc:
            self.state.fail(str(exc))
            self._show_runtime_error(str(exc))

    def _stop_dictation(self) -> None:
        try:
            assert self.pipeline is not None
            self.pipeline.stop()
            self.state.stop("user")
        except RuntimeError as exc:
            self._show_runtime_error(str(exc))

    def _ptt_down(self) -> None:
        if self.state.state in {
            DictationState.IDLE,
            DictationState.ERROR,
        }:
            self._start_dictation(auto_insert=True)

    def _ptt_up(self) -> None:
        if self.state.state is DictationState.RECORDING:
            self._stop_dictation()

    def _state_changed(self, change: StateChange) -> None:
        QTimer.singleShot(0, lambda: self._apply_state(change.current, change.reason))

    def _apply_state(self, state: DictationState, reason: str) -> None:
        del reason
        labels = {
            DictationState.IDLE: (
                "Ready",
                "Start listening",
                "Press start, then speak naturally.",
                "idle",
            ),
            DictationState.RECORDING: (
                "Listening",
                "Stop listening",
                "Speak naturally. A pause will complete each phrase.",
                "recording",
            ),
            DictationState.PAUSED: (
                "Paused",
                "Stop listening",
                "Your microphone is paused.",
                "idle",
            ),
            DictationState.DRAINING: (
                "Refining transcript",
                "Please wait",
                "Turning the latest phrase into text…",
                "draining",
            ),
            DictationState.ERROR: (
                "Check your setup",
                "Try again",
                "Open Preferences if your microphone or model needs attention.",
                "error",
            ),
        }
        status, button, caption, dot_state = labels[state]
        if self.demo_mode:
            caption = "Demo mode · " + caption
        self.status.setText(status)
        self.status_caption.setText(caption)
        self.record_button.setText(button)
        self.record_button.setEnabled(state is not DictationState.DRAINING)
        self.record_button.set_recording(state is DictationState.RECORDING)
        self.status_dot.setProperty("state", dot_state)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        self.status_animation.stop()
        self.status_animation.start()
        self.voice_orb.set_state(dot_state)
        if state is not DictationState.RECORDING:
            self.meter.setValue(0)
        held = state is DictationState.RECORDING
        for keycap in self.ptt_keycaps:
            keycap.setProperty("held", held)
            keycap.style().unpolish(keycap)
            keycap.style().polish(keycap)
        if state is DictationState.RECORDING:
            self._set_hotkey_indicator("recording", "●  RECORDING · RELEASE TO INSERT")
            self.overlay.show_recording(self.settings.push_to_talk_hotkey)
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        elif state is DictationState.DRAINING:
            self._set_hotkey_indicator("recording", "●  TRANSCRIBING…")
            self.overlay.show_processing()
        else:
            if self.hotkeys and self._hotkey_is_ready:
                if self._injector_is_ready:
                    self._set_hotkey_indicator(
                        "ready",
                        f"●  READY · HOLD {display_hotkey(self.settings.push_to_talk_hotkey)}",
                    )
                else:
                    self._set_hotkey_indicator(
                        "connecting",
                        "●  SHORTCUT READY · SETTING UP AUTOMATIC PASTE…",
                    )
            self.overlay.hide_animated()
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    @Slot(float)
    def _set_level(self, level: float) -> None:
        self.level_animation.stop()
        self.level_animation.setStartValue(self.meter.value())
        self.level_animation.setEndValue(round(max(0.0, min(level, 1.0)) * 100))
        self.level_animation.start()
        self.voice_orb.set_level(level)
        self.overlay.set_level(level)

    @Slot()
    def _update_word_count(self) -> None:
        count = len(self.editor.toPlainText().split())
        self.word_count.setText(f"{count} word" if count == 1 else f"{count} words")

    def _refresh_shortcut_display(self) -> None:
        parts = hotkey_parts(self.settings.push_to_talk_hotkey)
        for index, keycap in enumerate(self.ptt_keycaps):
            visible = index < len(parts)
            keycap.setVisible(visible)
            if visible:
                label = "SUPER" if parts[index] == "cmd" else parts[index].upper()
                keycap.setText(label)
        for index, plus in enumerate(self.ptt_pluses):
            plus.setVisible(index < len(parts) - 1)

    @Slot(str)
    def _hotkey_ready(self, shortcut: str) -> None:
        self._hotkey_is_ready = True
        self._hotkey_setup_requested = False
        self.settings.hotkey_authorized = True
        self.store.save(self.settings)
        label = shortcut if shortcut else display_hotkey(
            self.settings.push_to_talk_hotkey
        )
        self._set_hotkey_indicator(
            "connecting", f"●  SHORTCUT READY · HOLD {label} · SETTING UP PASTE…"
        )
        self.statusBar().showMessage(
            "Global shortcut ready; setting up automatic paste", 3500
        )
        self._start_injector()

    @Slot(str)
    def _hotkey_failed(self, message: str) -> None:
        self._hotkey_is_ready = False
        self._hotkey_setup_requested = False
        self.settings.hotkey_authorized = False
        self.store.save(self.settings)
        self._set_hotkey_indicator(
            "error",
            "●  SETUP REQUIRED · GLOBAL SHORTCUT NOT ACTIVE",
            retry="hotkey",
        )
        self.statusBar().showMessage(message, 15_000)
        if not self.isVisible():
            self._show_window()

    def _set_hotkey_indicator(
        self, state: str, text: str, *, retry: str | None = None
    ) -> None:
        self.hotkey_indicator.setText(text)
        self.hotkey_indicator.setProperty("state", state)
        self.hotkey_indicator.style().unpolish(self.hotkey_indicator)
        self.hotkey_indicator.style().polish(self.hotkey_indicator)
        self._setup_retry_target = retry or "hotkey"
        self.hotkey_retry_button.setText(
            "Set up automatic paste"
            if retry == "injector"
            else "Set up global shortcut"
        )
        self.hotkey_retry_button.setVisible(retry is not None)

    @Slot()
    def retry_setup(self) -> None:
        if self._setup_retry_target == "injector":
            self._start_injector(force=True)
            return
        if self.state.state not in {DictationState.IDLE, DictationState.ERROR}:
            self.statusBar().showMessage(
                "Stop dictation before setting up the shortcut", 3000
            )
            return
        self.settings.hotkey_authorized = False
        self.store.save(self.settings)
        self._hotkey_setup_requested = True
        self._set_hotkey_indicator(
            "connecting", "●  WAITING FOR DESKTOP APPROVAL…"
        )
        self._rebuild_runtime(force_hotkeys=True)

    def _start_injector(self, *, force: bool = False) -> None:
        if self.no_hotkeys:
            return
        if force:
            self.injector.stop()
            self._injector_started = False
            self._injector_is_ready = False
            self._set_hotkey_indicator(
                "connecting", "●  SHORTCUT READY · WAITING FOR PASTE APPROVAL…"
            )
        if self._injector_started:
            return
        self._injector_started = True
        self.injector.start()

    @Slot()
    def _injector_ready(self) -> None:
        self._injector_is_ready = True
        self._set_hotkey_indicator(
            "ready",
            f"●  READY · HOLD {display_hotkey(self.settings.push_to_talk_hotkey)}",
        )
        self.statusBar().showMessage(
            "Push-to-talk and automatic paste are ready", 3500
        )

    @Slot(str)
    def _injector_failed(self, message: str) -> None:
        self._injector_started = False
        self._injector_is_ready = False
        self._set_hotkey_indicator(
            "error",
            "●  SHORTCUT READY · AUTOMATIC PASTE NEEDS APPROVAL",
            retry="injector",
        )
        self.statusBar().showMessage(message, 15_000)
        if not self.isVisible():
            self._show_window()

    @Slot(int)
    def _home_language_changed(self, index: int) -> None:
        language = self.language_picker.itemData(index)
        if not language or language == self.settings.language:
            return
        if self.state.state not in {DictationState.IDLE, DictationState.ERROR}:
            self.language_picker.blockSignals(True)
            old_index = self.language_picker.findData(self.settings.language)
            self.language_picker.setCurrentIndex(max(0, old_index))
            self.language_picker.blockSignals(False)
            self.statusBar().showMessage("Stop dictation before changing language", 3000)
            return
        self.settings.language = language
        self.store.save(self.settings)
        self._rebuild_runtime()
        self.statusBar().showMessage("Language preference saved", 2500)

    @Slot(str)
    def _append_text(self, text: str) -> None:
        self._session_fragments.append(text.strip())
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        existing = self.editor.toPlainText()
        if existing and not existing.endswith((" ", "\n")):
            cursor.insertText(" ")
        cursor.insertText(text.strip())
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        if self.settings.auto_copy:
            self.copy_text()

    @Slot(str)
    def _interim_text(self, text: str) -> None:
        del text

    @Slot()
    def _pipeline_finished(self) -> None:
        if self.state.state is DictationState.DRAINING:
            self.state.drained()
        if self._auto_insert_after_drain:
            text = " ".join(fragment for fragment in self._session_fragments if fragment).strip()
            self._auto_insert_after_drain = False
            if text:
                QApplication.clipboard().setText(text)
                QTimer.singleShot(80, self._paste_now)

    @Slot(str)
    def _show_runtime_error(self, message: str) -> None:
        self.statusBar().showMessage(message, 15_000)
        self.overlay.hide_animated()
        self._auto_insert_after_drain = False
        if self.state.state is DictationState.DRAINING:
            self.state.drained()

    def copy_text(self) -> None:
        text = self.editor.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("Transcript copied", 2500)

    def insert_text(self) -> None:
        text = self.editor.toPlainText()
        if not text:
            return
        QApplication.clipboard().setText(text)
        if self.isActiveWindow():
            if self.tray.isVisible():
                self.hide()
            else:
                self.showMinimized()
            QTimer.singleShot(250, self._paste_now)
        else:
            self._paste_now()

    def _paste_now(self) -> None:
        try:
            self.injector.paste(shift=bool(self.settings.terminal_paste))
        except InjectionError as exc:
            self.bridge.error.emit(str(exc))

    @Slot(str)
    def _save_restore_token(self, token: str) -> None:
        self.settings.remote_desktop_restore_token = token
        self.store.save(self.settings)

    def clear_text(self) -> None:
        if not self.editor.toPlainText() or QMessageBox.question(
            self,
            "Clear transcript?",
            "This removes the current transcript from the editor.",
        ) == QMessageBox.StandardButton.Yes:
            self.editor.clear()

    def save_text(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export transcript",
            "transcript.txt",
            "Text (*.txt);;Markdown (*.md);;Word document (*.docx)",
        )
        if not path:
            return
        try:
            export_transcript(Path(path), self.editor.toPlainText())
            self.statusBar().showMessage(f"Saved {path}", 5000)
        except (OSError, ExportError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def open_settings(self) -> None:
        if self.state.state not in {DictationState.IDLE, DictationState.ERROR}:
            QMessageBox.information(
                self, "Dictation active", "Stop dictation before changing settings."
            )
            return
        dialog = SettingsDialog(
            self.settings,
            self,
            on_appearance_change=self.apply_appearance,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.store.save(self.settings)
            self.apply_appearance(self.settings.appearance)
            self._rebuild_runtime()
            self.statusBar().showMessage("Settings saved", 3000)

    def _show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _request_application_quit(self) -> None:
        from soundflow.preferences.model_manager import request_application_quit

        request_application_quit()

    def closeEvent(self, event) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "Soundflow is still running",
                "Use the tray menu to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
        else:
            event.ignore()
            self.hide()
            self._request_application_quit()

    def shutdown(self) -> None:
        if self.hotkeys:
            self.hotkeys.stop()
        if self.pipeline:
            self.pipeline.close()
        self.injector.stop()
        self.overlay.close()
