"""System tab: readiness checks that run when the page opens, plus local data."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from soundflow import __version__
from soundflow.core.settings import data_directory
from soundflow.design import FONT_SMALL, MONO_FONT
from soundflow.preferences.system_check import run_system_check
from soundflow.preferences.widgets import PreferenceTab, SettingsRow
from soundflow.utils import open_data_folder


class SystemTab(PreferenceTab):
    """Show what Soundflow needs for dictation, and the fix for anything missing."""

    # "dictation" or "speech_model": the page should switch to that tab.
    section_requested = Signal(str)
    # The user asked to allow a global shortcut; the window starts that setup.
    shortcut_permission_requested = Signal()

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__("systemTab", "System", parent)
        self._settings = settings
        self._status_labels: dict[str, QLabel] = {}
        self._fix_buttons: dict[str, QPushButton] = {}
        self._rows: dict[str, SettingsRow] = {}
        self._check_timer = QTimer(self)
        self._check_timer.setSingleShot(True)
        self._check_timer.setInterval(0)
        self._check_timer.timeout.connect(self._run_when_shown)

        ready = self.add_group("Ready to dictate")
        for key, title, object_suffix in (
            ("microphone", "Microphone", "Microphone"),
            ("model", "Speech model", "Model"),
            ("device", "Processing", "Device"),
            ("shortcut", "Shortcut in other apps", "Shortcut"),
            ("insertion", "Pasting", "Insertion"),
        ):
            control = self._status_control(key, object_suffix)
            row = SettingsRow(title, "", control)
            self._rows[key] = row
            ready.add_row(row)
        self._fix_buttons["microphone"].clicked.connect(
            lambda: self.section_requested.emit("dictation")
        )
        self._fix_buttons["model"].clicked.connect(
            lambda: self.section_requested.emit("speech_model")
        )
        self._fix_buttons["shortcut"].clicked.connect(
            self.shortcut_permission_requested
        )

        check_line = QWidget()
        check_layout = QHBoxLayout(check_line)
        check_layout.setContentsMargins(0, 0, 0, 0)
        check_layout.setSpacing(8)
        self._last_checked = QLabel("Checked when you opened this page.")
        self._last_checked.setObjectName("noteText")
        self._check_button = QPushButton("Check again")
        self._check_button.setObjectName("linkButton")
        self._check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_button.clicked.connect(self.run_check)
        check_layout.addWidget(self._last_checked)
        check_layout.addWidget(self._check_button)
        check_layout.addStretch(1)
        ready.parentWidget().layout().addWidget(check_line)

        data = self.add_group("Your data")
        self._open_button = QPushButton("Open folder")
        self._open_button.setObjectName("systemSecondaryButton")
        self._open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_button.clicked.connect(open_data_folder)
        data_row = SettingsRow(
            "Stored on this computer",
            "Settings and speech models stay on this device. Saved transcripts are "
            "kept here and synced to your Soundflow account.",
            self._open_button,
        )
        path_field = QLineEdit(str(data_directory()))
        path_field.setObjectName("systemDataPath")
        path_field.setReadOnly(True)
        path_field.setFixedHeight(36)
        path_field.setFont(QFont(MONO_FONT, FONT_SMALL))
        path_field.setCursorPosition(0)
        data_row.add_below_description(path_field)
        data.add_row(data_row)

        about = self.add_group("About")
        about.add_row(
            SettingsRow(
                f"Soundflow {__version__}",
                "Free and private dictation for Linux.",
            )
        )
        self.finish()

    # -- construction -----------------------------------------------------
    def _status_control(self, key: str, object_suffix: str) -> QWidget:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        status = QLabel("Not checked")
        status.setObjectName(f"systemStatus{object_suffix}")
        status.setProperty("state", "neutral")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setMinimumWidth(128)
        layout.addWidget(status)
        self._status_labels[key] = status
        fix = QPushButton("")
        fix.setObjectName("quietButton")
        fix.setCursor(Qt.CursorShape.PointingHandCursor)
        fix.setFixedHeight(36)
        fix.setVisible(False)
        layout.addWidget(fix)
        self._fix_buttons[key] = fix
        return holder

    # -- behaviour --------------------------------------------------------
    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Checks run whenever the page opens. Deferred so the page paints first.
        self._check_timer.start()

    def _run_when_shown(self) -> None:
        if self.isVisible():
            self.run_check()

    def _set_status(self, key: str, text: str, state: str) -> None:
        label = self._status_labels[key]
        label.setText(text)
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)

    def _set_fix(self, key: str, text: str = "") -> None:
        button = self._fix_buttons[key]
        button.setText(text)
        button.setVisible(bool(text))

    def _set_row(self, key: str, description: str) -> None:
        self._rows[key].set_description(description)

    def run_check(self) -> None:
        self._check_button.setEnabled(False)
        self._check_button.setText("Checking…")
        for key in self._status_labels:
            self._set_status(key, "Checking", "idle")
            self._set_fix(key)
        try:
            result = run_system_check(self._settings)
            self._apply(result)
        finally:
            self._check_button.setText("Check again")
            self._check_button.setEnabled(True)
            self._last_checked.setText("Checked just now.")

    def _apply(self, result) -> None:
        if result.microphone_ready:
            self._set_status("microphone", "Ready", "ready")
            self._set_row("microphone", "An audio input is available.")
        else:
            self._set_status("microphone", "Unavailable", "error")
            self._set_row("microphone", "No microphone was found. Connect one, then check again.")
            self._set_fix("microphone", "Choose microphone")

        if result.model_ready:
            self._set_status("model", "Ready", "ready")
            self._set_row("model", "The selected speech model is installed.")
        else:
            self._set_status("model", "Missing", "error")
            self._set_row("model", "The selected speech model isn’t installed here.")
            self._set_fix("model", "Choose a model")

        self._apply_device(result)

        if not self._settings.global_hotkeys:
            self._set_status("shortcut", "Off", "neutral")
            self._set_row("shortcut", "The shortcut works only while this window is in front.")
        elif result.hotkey_ready:
            self._set_status("shortcut", "Ready", "ready")
            self._set_row("shortcut", "The shortcut works in other apps.")
        else:
            self._set_status("shortcut", "Needs permission", "warning")
            self._set_row(
                "shortcut",
                "Your desktop asks once before an app can use a global shortcut.",
            )
            self._set_fix("shortcut", "Allow")

        if result.paste_ready:
            self._set_status("insertion", "Ready", "ready")
            self._set_row("insertion", "Text can be pasted into the app you are using.")
        else:
            self._set_status("insertion", "Needs permission", "warning")
            self._set_row("insertion", "Pasting needs permission from your desktop.")

    def _apply_device(self, result) -> None:
        requested = self._settings.inference_device
        if result.effective_device == "cuda":
            self._set_status("device", "GPU", "ready")
            self._set_row("device", "Running on your NVIDIA GPU.")
        elif requested == "cuda":
            self._set_status("device", "Processor", "warning")
            self._set_row("device", "CUDA isn’t available, so the processor is used.")
        else:
            self._set_status("device", "Processor", "ready")
            self._set_row("device", "Running on the processor.")

    def write_back(self, settings) -> None:
        """The System tab only reports; it stores nothing."""

    def refresh_from_settings(self, settings=None) -> None:
        if settings is not None:
            self._settings = settings


__all__ = ["SystemTab"]
