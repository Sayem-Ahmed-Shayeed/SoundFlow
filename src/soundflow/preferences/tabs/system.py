"""System tab for local readiness and application data."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from soundflow.core.settings import data_directory, default_model_path
from soundflow.design import (
    BODY_FONT,
    CONTROL_HEIGHT_SM,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    FONT_TINY,
    MONO_FONT,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)
from soundflow.preferences.system_check import run_system_check
from soundflow.utils import open_data_folder


class SystemTab(QWidget):
    """Show the local components Soundflow needs for dictation."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("systemTab")
        self._settings = settings
        self._status_labels: dict[str, QLabel] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("systemScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.viewport().setObjectName("systemScrollViewport")

        content = QWidget()
        content.setObjectName("systemContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        content_layout.setSpacing(SPACE_4)

        readiness = self._card()
        readiness_layout = readiness.layout()
        readiness_layout.addLayout(self._readiness_header())

        for key, title, description in (
            ("model", "Model files", "Bundled Whisper model is available locally."),
            ("microphone", "Microphone", "An audio input is available for dictation."),
            ("shortcut", "Global shortcut", "Push-to-talk can work outside Soundflow."),
            ("insertion", "Text insertion", "Completed speech can be pasted at the cursor."),
            ("device", "Processing device", "Recognition runs locally on this device."),
        ):
            readiness_layout.addWidget(
                self._status_row(key, title, description)
            )

        readiness_layout.addWidget(self._path_block(
            "Model location",
            str(Path(settings.model_path or default_model_path())),
            "systemModelPath",
        ))

        action_row = QHBoxLayout()
        action_row.setSpacing(SPACE_3)
        self._check_button = QPushButton("Run system check")
        self._check_button.setObjectName("systemCheckButton")
        self._check_button.setFixedHeight(CONTROL_HEIGHT_SM)
        self._check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_button.clicked.connect(self.run_check)
        action_row.addWidget(self._check_button)

        self._last_checked = QLabel("Not checked yet")
        self._last_checked.setObjectName("systemLastChecked")
        self._last_checked.setFont(QFont(BODY_FONT, FONT_TINY))
        self._last_checked.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        action_row.addWidget(
            self._last_checked, 0, Qt.AlignmentFlag.AlignVCenter
        )
        action_row.addStretch(1)
        readiness_layout.addLayout(action_row)
        content_layout.addWidget(readiness)

        data_card = self._card()
        data_card.setObjectName("localDataCard")
        data_layout = data_card.layout()
        data_layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        data_layout.setSpacing(SPACE_2)
        data_layout.addWidget(self._heading("Local data"))

        data_description = QLabel(
            "Settings, models, and saved transcripts stay on this device."
        )
        data_description.setObjectName("mutedText")
        data_description.setFont(QFont(BODY_FONT, FONT_SMALL))
        data_description.setWordWrap(True)
        data_layout.addWidget(data_description)

        data_path = str(data_directory())
        folder_row = QHBoxLayout()
        folder_row.setSpacing(SPACE_2)

        path_field = QLineEdit(data_path)
        path_field.setObjectName("systemDataPath")
        path_field.setReadOnly(True)
        path_field.setFixedHeight(CONTROL_HEIGHT_SM)
        path_field.setFont(QFont(MONO_FONT, FONT_SMALL))
        path_field.setCursorPosition(0)
        folder_row.addWidget(path_field, 1)

        open_button = QPushButton("Open folder")
        open_button.setObjectName("systemSecondaryButton")
        open_button.setFixedHeight(CONTROL_HEIGHT_SM)
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(open_data_folder)
        folder_row.addWidget(
            open_button, 0, Qt.AlignmentFlag.AlignVCenter
        )
        data_layout.addLayout(folder_row)
        content_layout.addWidget(data_card)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("preferencesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        layout.setSpacing(SPACE_3)
        return card

    def _readiness_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(SPACE_3)

        copy = QVBoxLayout()
        copy.setSpacing(SPACE_2)
        copy.addWidget(self._heading("System readiness"))
        subtitle = QLabel(
            "Check the components Soundflow needs for private, offline dictation."
        )
        subtitle.setObjectName("mutedText")
        subtitle.setFont(QFont(BODY_FONT, FONT_SMALL))
        subtitle.setWordWrap(True)
        copy.addWidget(subtitle)
        row.addLayout(copy, 1)

        self._overall_status = QLabel("Not checked")
        self._overall_status.setObjectName("systemStatusPill")
        self._overall_status.setProperty("state", "neutral")
        self._overall_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overall_status.setFont(QFont(BODY_FONT, FONT_SMALL))
        row.addWidget(self._overall_status, 0, Qt.AlignmentFlag.AlignTop)
        return row

    def _heading(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("headingText")
        label.setFont(QFont(BODY_FONT, FONT_HEADING))
        return label

    def _status_row(self, key: str, title: str, description: str) -> QWidget:
        row = QWidget()
        row.setObjectName("systemCheckRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(SPACE_3, SPACE_2, SPACE_3, SPACE_2)
        layout.setSpacing(SPACE_3)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("systemRowTitle")
        title_label.setFont(QFont(BODY_FONT, FONT_BODY))
        copy.addWidget(title_label)

        detail = QLabel(description)
        detail.setObjectName("mutedText")
        detail.setFont(QFont(BODY_FONT, FONT_TINY))
        detail.setWordWrap(True)
        copy.addWidget(detail)
        layout.addLayout(copy, 1)

        status = QLabel("Not checked")
        object_suffix = {
            "model": "Model",
            "microphone": "Microphone",
            "shortcut": "Shortcut",
            "insertion": "Insertion",
            "device": "Device",
        }[key]
        status.setObjectName(f"systemStatus{object_suffix}")
        status.setProperty("state", "neutral")
        status.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        status.setFont(QFont(BODY_FONT, FONT_SMALL))
        status.setMinimumWidth(130)
        layout.addWidget(status)
        self._status_labels[key] = status
        return row

    def _path_block(self, title: str, path: str, object_name: str) -> QWidget:
        block = QWidget()
        block.setObjectName("systemPathBlock")
        layout = QVBoxLayout(block)
        layout.setContentsMargins(SPACE_3, SPACE_2, SPACE_3, SPACE_2)
        layout.setSpacing(2)

        caption = QLabel(title)
        caption.setObjectName("dimText")
        caption.setFont(QFont(BODY_FONT, FONT_TINY))
        layout.addWidget(caption)

        value = QLineEdit(path)
        value.setObjectName(object_name)
        value.setProperty("role", "path")
        value.setReadOnly(True)
        value.setFont(QFont(MONO_FONT, FONT_SMALL))
        value.setFixedHeight(CONTROL_HEIGHT_SM)
        value.setCursorPosition(0)
        layout.addWidget(value)
        return block

    def write_back(self, settings) -> None:
        """The System tab exposes read-only diagnostics."""

    def _set_status(self, key: str, text: str, state: str) -> None:
        label = self._status_labels[key]
        label.setText(text)
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)

    def run_check(self) -> None:
        self._check_button.setEnabled(False)
        self._check_button.setText("Checking…")
        try:
            result = run_system_check(self._settings)
            self._set_status(
                "model",
                "Ready" if result.model_ready else "Missing",
                "ready" if result.model_ready else "error",
            )
            self._set_status(
                "microphone",
                "Ready" if result.microphone_ready else "Unavailable",
                "ready" if result.microphone_ready else "error",
            )
            self._set_status(
                "shortcut",
                "Ready" if result.hotkey_ready else "Permission needed",
                "ready" if result.hotkey_ready else "warning",
            )
            self._set_status(
                "insertion",
                "Ready" if result.paste_ready else "Permission needed",
                "ready" if result.paste_ready else "warning",
            )

            requested_device = self._settings.inference_device.lower()
            fell_back = (
                requested_device == "cuda"
                and result.effective_device.lower() != "cuda"
            )
            device_text = (
                "CPU · CUDA unavailable"
                if fell_back
                else result.effective_device.upper()
            )
            self._set_status(
                "device",
                device_text,
                "warning" if fell_back else "ready",
            )

            all_ready = (
                result.model_ready
                and result.microphone_ready
                and result.hotkey_ready
                and result.paste_ready
                and not fell_back
            )
            self._overall_status.setText(
                "Ready" if all_ready else "Needs attention"
            )
            self._overall_status.setProperty(
                "state", "ready" if all_ready else "warning"
            )
            self._overall_status.style().unpolish(self._overall_status)
            self._overall_status.style().polish(self._overall_status)
            self._last_checked.setText("Last checked just now")
        finally:
            self._check_button.setText("Run system check")
            self._check_button.setEnabled(True)


__all__ = ["SystemTab"]
