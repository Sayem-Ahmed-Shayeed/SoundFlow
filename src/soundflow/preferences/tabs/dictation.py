"""Dictation tab: the shortcut, your voice, and what happens to the text."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QWidget,
)

from soundflow.audio import AudioCapture
from soundflow.core.settings import DEFAULT_PUSH_TO_TALK
from soundflow.hotkeys import display_hotkey
from soundflow.preferences.widgets import (
    ChoiceSet,
    PreferenceTab,
    SettingsRow,
    ShortcutRecorder,
)
from soundflow.ui.widgets import SegmentedControl, ToggleSwitch

LANGUAGES = (
    ("Auto detect", "auto"),
    ("English or বাংলা", "auto:en+bn"),
    ("English or Hindi", "auto:en+hi"),
    ("English", "en"),
    ("বাংলা", "bn"),
    ("Hindi", "hi"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Japanese", "ja"),
)
PAUSES = (("short", "Short", 400), ("medium", "Medium", 700), ("long", "Long", 1200))
FINISH_OPTIONS = (
    ("paste", "Paste it where your cursor is", "The text also stays on your clipboard."),
    ("copy", "Copy it to the clipboard", "Paste it yourself with Ctrl+V."),
)
LOGGER = logging.getLogger(__name__)
_SHORTCUT_IDLE = "Hold the keys in any app, speak, then let go to paste."
_SHORTCUT_RECORDING = "Press the keys you want, then let go. Esc cancels."
_MIC_TEST_TEXT = "Speak. The bar should move."


class _LevelBridge(QObject):
    """Carries microphone levels from the capture thread to the GUI thread."""

    level = Signal(float)
    failed = Signal(str)


def pause_choice(milliseconds: int) -> str:
    """The pause option closest to a stored silence length."""
    return min(PAUSES, key=lambda item: abs(item[2] - int(milliseconds)))[0]


def pause_milliseconds(choice: str) -> int:
    return next((ms for key, _label, ms in PAUSES if key == choice), 700)


def default_shortcut_label() -> str:
    """The default shortcut as words, e.g. "Ctrl Alt Space"."""
    return display_hotkey(DEFAULT_PUSH_TO_TALK).replace(" + ", " ")


class DictationTab(PreferenceTab):
    """Dictation preferences tab."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__("dictationTab", "Dictation", parent)
        self._settings = settings
        self._original_shortcut = settings.push_to_talk_hotkey
        self._capture: AudioCapture | None = None
        self._bridge = _LevelBridge(self)
        self._bridge.level.connect(self._on_level)
        self._bridge.failed.connect(self._on_mic_failed)

        # Shortcut
        shortcut = self.add_group(
            "Shortcut",
            note=(
                "On Wayland, your desktop asks once for permission to use this "
                "shortcut system-wide."
            ),
        )
        self._recorder = ShortcutRecorder(settings.push_to_talk_hotkey)
        self._recorder.changed.connect(self._on_shortcut_changed)
        self._recorder.recording_changed.connect(self._on_recording_changed)
        self._shortcut_row = SettingsRow(
            "Hold to dictate", _SHORTCUT_IDLE, self._recorder
        )
        shortcut.add_row(self._shortcut_row)

        self._reset = QPushButton(f"Go back to {default_shortcut_label()}")
        self._reset.setObjectName("linkButton")
        self._reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset.clicked.connect(self._reset_shortcut)
        self._reset_slot = shortcut.add_row(self._reset_row())

        self._other_apps = ToggleSwitch("Use the shortcut in other apps")
        self._other_apps.setChecked(bool(settings.global_hotkeys))
        self._other_apps.toggled.connect(self._sync_wayland_note)
        shortcut.add_row(
            SettingsRow(
                "Use the shortcut in other apps",
                "Turn off to use it only while this window is in front.",
                self._other_apps,
            )
        )
        self._wayland_note = shortcut.note
        self._sync_shortcut_state(settings.push_to_talk_hotkey)
        self._sync_wayland_note(self._other_apps.isChecked())

        # Your voice
        voice = self.add_group("Your voice")
        self._mic = QComboBox()
        self._mic.setObjectName("compactPreferenceField")
        self._mic.setFixedHeight(36)
        self._mic.addItem("System default", None)
        self._select_microphone(settings.microphone)
        self._test_button = QPushButton("Test")
        self._test_button.setObjectName("quietButton")
        self._test_button.setFixedHeight(36)
        self._test_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._test_button.clicked.connect(self._toggle_mic_test)
        mic_control = QHBoxLayout()
        mic_control.setSpacing(8)
        mic_control.addWidget(self._mic)
        mic_control.addWidget(self._test_button)
        mic_holder = QWidget()
        mic_holder.setLayout(mic_control)
        self._mic_row = SettingsRow("Microphone", "", mic_holder)
        self._meter_line = QWidget()
        meter_layout = QHBoxLayout(self._meter_line)
        meter_layout.setContentsMargins(0, 4, 0, 0)
        meter_layout.setSpacing(10)
        self._meter = QProgressBar()
        self._meter.setObjectName("micLevel")
        self._meter.setRange(0, 100)
        self._meter.setValue(0)
        self._meter.setTextVisible(False)
        self._meter.setFixedSize(120, 6)
        self._meter_text = QLabel(_MIC_TEST_TEXT)
        self._meter_text.setObjectName("mutedText")
        meter_layout.addWidget(self._meter, 0, Qt.AlignmentFlag.AlignVCenter)
        meter_layout.addWidget(self._meter_text, 1)
        self._mic_row.add_below_description(self._meter_line)
        self._meter_line.hide()
        voice.add_row(self._mic_row)

        self._language = QComboBox()
        self._language.setObjectName("compactPreferenceField")
        self._language.setFixedHeight(36)
        for label, value in LANGUAGES:
            self._language.addItem(label, value)
        voice.add_row(
            SettingsRow(
                "Language",
                "The same setting as on the Dictation screen.",
                self._language,
            )
        )

        self._pause = SegmentedControl(
            [(key, label) for key, label, _ms in PAUSES],
            pause_choice(settings.silence_duration_ms),
            accessible_name="Pause length",
        )
        voice.add_row(
            SettingsRow(
                "Pause length",
                "How long you can stop mid-sentence before Soundflow ends the phrase.",
                self._pause,
            )
        )

        # After you speak
        after = self.add_group("After you speak")
        self._finish = ChoiceSet(
            FINISH_OPTIONS,
            "paste" if settings.auto_insert else "copy",
            self,
        )
        self._finish.changed.connect(self._sync_terminal_row)
        for row in self._finish.rows:
            after.add_row(row)
        self._terminal = ToggleSwitch("Paste with Ctrl+Shift+V")
        self._terminal.setChecked(bool(settings.terminal_paste))
        self._terminal_slot = after.add_row(
            SettingsRow(
                "Paste with Ctrl+Shift+V",
                "Terminals need this. Leave it off for other apps.",
                self._terminal,
            )
        )
        self._history = ToggleSwitch("Keep dictations in History")
        self._history.setChecked(bool(settings.auto_save_transcripts))
        after.add_row(
            SettingsRow(
                "Keep dictations in History",
                "So you can search, edit and copy them later.",
                self._history,
            )
        )
        self._sync_terminal_row()
        self._load_choices(settings)
        self.finish()

        self._devices_loaded = False
        self._device_timer = QTimer(self)
        self._device_timer.setSingleShot(True)
        self._device_timer.setInterval(0)
        self._device_timer.timeout.connect(self._load_devices)

    # -- setup helpers ----------------------------------------------------
    def _reset_row(self) -> QWidget:
        holder = QWidget()
        holder.setObjectName("prefsRow")
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.addWidget(self._reset, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return holder

    def _load_choices(self, settings) -> None:
        self._language.setCurrentIndex(
            max(0, self._language.findData(settings.language))
        )
        self._pause.set_value(pause_choice(settings.silence_duration_ms))

    def _select_microphone(self, device) -> None:
        """Select ``device``; keep an unplugged one as its own entry so a
        later save doesn't silently reset it to the system default."""
        index = self._mic.findData(device) if device is not None else 0
        if index < 0:
            self._mic.addItem(f"Unavailable microphone (#{device})", device)
            index = self._mic.count() - 1
        self._mic.blockSignals(True)
        self._mic.setCurrentIndex(index)
        self._mic.blockSignals(False)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._devices_loaded:
            self._devices_loaded = True
            # Listing devices initialises PortAudio, so it waits until this tab
            # is first shown and runs after the frame has painted.
            self._device_timer.start()

    def hideEvent(self, event) -> None:
        self._stop_mic_test()
        super().hideEvent(event)

    def _load_devices(self) -> None:
        try:
            devices = list(AudioCapture.list_input_devices())
        except Exception:
            devices = []
        self._devices_listed(devices)

    def _devices_listed(self, devices: list) -> None:
        current = self._mic.currentData()
        self._mic.blockSignals(True)
        self._mic.clear()
        self._mic.addItem("System default", None)
        for idx, name in devices:
            self._mic.addItem(name, idx)
        self._mic.blockSignals(False)
        self._select_microphone(current)

    # -- shortcut ---------------------------------------------------------
    def _sync_shortcut_state(self, value: str) -> None:
        is_default = value == DEFAULT_PUSH_TO_TALK
        self._reset.setVisible(not is_default and not self._recorder.recording)
        self._reset_slot.setVisible(not is_default and not self._recorder.recording)

    def _on_shortcut_changed(self, value: str) -> None:
        self._sync_shortcut_state(value)

    def _on_recording_changed(self, recording: bool) -> None:
        self._shortcut_row.set_description(_SHORTCUT_RECORDING if recording else _SHORTCUT_IDLE)
        self._sync_shortcut_state(self._recorder.shortcut())

    def _reset_shortcut(self) -> None:
        self._recorder.set_shortcut(DEFAULT_PUSH_TO_TALK)
        self._recorder.changed.emit(DEFAULT_PUSH_TO_TALK)

    def _sync_wayland_note(self, enabled: bool) -> None:
        self._wayland_note.setVisible(bool(enabled))

    # -- finish -----------------------------------------------------------
    def _sync_terminal_row(self, *_args) -> None:
        self._terminal_slot.setVisible(self._finish.value() == "paste")

    # -- microphone test --------------------------------------------------
    def _toggle_mic_test(self) -> None:
        if self._capture is not None:
            self._stop_mic_test()
            return
        self._meter_line.show()
        self._meter_text.setText(_MIC_TEST_TEXT)
        self._test_button.setText("Stop")
        self._mic_row.set_description("")
        try:
            capture = AudioCapture(
                on_frame=lambda _payload: None,
                on_level=self._bridge.level.emit,
                on_error=self._bridge.failed.emit,
            )
            capture.start(self._mic.currentData())
        except Exception as exc:
            self._on_mic_failed(str(exc) or "The microphone could not be opened.")
            return
        self._capture = capture

    def _stop_mic_test(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            try:
                capture.stop()
            except Exception:
                LOGGER.warning("The microphone did not stop cleanly", exc_info=True)
        self._meter.setValue(0)
        self._meter_line.hide()
        self._test_button.setText("Test")

    def _on_level(self, level: float) -> None:
        if self._capture is not None:
            self._meter.setValue(int(max(0.0, min(1.0, level)) * 100))

    def _on_mic_failed(self, message: str) -> None:
        self._stop_mic_test()
        self._mic_row.set_description(f"Microphone unavailable: {message}")

    def shutdown(self) -> None:
        self._stop_mic_test()

    # -- settings ---------------------------------------------------------
    def write_back(self, settings) -> None:
        shortcut = self._recorder.shortcut()
        if shortcut != self._original_shortcut:
            settings.hotkey_authorized = False
        settings.push_to_talk_hotkey = shortcut
        self._original_shortcut = shortcut
        settings.global_hotkeys = self._other_apps.isChecked()
        settings.language = self._language.currentData() or "auto"
        settings.microphone = self._mic.currentData()
        settings.silence_duration_ms = pause_milliseconds(self._pause.value())
        paste = self._finish.value() == "paste"
        settings.auto_insert = paste
        # Copying is always on: "paste" also leaves the text on the clipboard.
        settings.auto_copy = True
        settings.terminal_paste = self._terminal.isChecked()
        settings.auto_save_transcripts = self._history.isChecked()

    def refresh_from_settings(self, settings=None) -> None:
        """Re-read the pickers so changes made on the home page are not clobbered."""
        source = settings if settings is not None else self._settings
        self._original_shortcut = source.push_to_talk_hotkey
        if not self._recorder.recording:
            self._recorder.set_shortcut(source.push_to_talk_hotkey)
        self._sync_shortcut_state(source.push_to_talk_hotkey)
        for switch, value in (
            (self._other_apps, source.global_hotkeys),
            (self._terminal, source.terminal_paste),
            (self._history, source.auto_save_transcripts),
        ):
            switch.blockSignals(True)
            switch.setChecked(bool(value))
            switch.blockSignals(False)
        self._sync_wayland_note(self._other_apps.isChecked())
        self._language.blockSignals(True)
        self._language.setCurrentIndex(max(0, self._language.findData(source.language)))
        self._language.blockSignals(False)
        self._pause.set_value(pause_choice(source.silence_duration_ms))
        self._finish.set_value("paste" if source.auto_insert else "copy")
        self._sync_terminal_row()
        self._select_microphone(source.microphone)


__all__ = ["DictationTab", "pause_choice", "pause_milliseconds"]
