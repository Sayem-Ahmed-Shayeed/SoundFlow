"""Dictation tab — model path, language, processing device, microphone."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from soundflow.audio import AudioCapture
from soundflow.design import (
    BODY_FONT,
    FONT_BODY,
    FONT_HEADING,
    FONT_SMALL,
    SPACE_2,
    SPACE_3,
    SPACE_4,
)


class DictationTab(QWidget):
    """Dictation preferences tab."""

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dictationTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        outer.setSpacing(SPACE_4)

        card = QWidget()
        card.setObjectName("preferencesCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)

        title = QLabel("Recognition")
        title.setFont(QFont(BODY_FONT, FONT_HEADING))
        title.setObjectName("headingText")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(SPACE_2)

        # Model directory
        model_row = QHBoxLayout()
        model_row.setSpacing(SPACE_2)
        self._model = QLineEdit(settings.model_path)
        self._model.setPlaceholderText("Path to faster-whisper model")
        self._model.setFont(QFont(BODY_FONT, FONT_BODY))
        model_row.addWidget(self._model, 1)
        browse = QPushButton("Browse")
        browse.setObjectName("primaryButton")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._browse_model)
        model_row.addWidget(browse)
        form.addRow("Model directory", model_row)

        # Language
        self._language = QComboBox()
        for label, value in (
            ("Auto detect", "auto"),
            ("English", "en"),
            ("\u09AC\u09BE\u0982\u09B2\u09BE", "bn"),
            ("Hindi", "hi"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de"),
            ("Japanese", "ja"),
        ):
            self._language.addItem(label, value)
        idx = next(
            (i for i in range(self._language.count())
             if self._language.itemData(i) == settings.language),
            0,
        )
        self._language.setCurrentIndex(idx)
        form.addRow("Language", self._language)

        # Processing device
        self._device = QComboBox()
        for label, value in (("Auto", "auto"), ("CPU", "cpu"), ("GPU", "cuda")):
            self._device.addItem(label, value)
        idx = next(
            (i for i in range(self._device.count())
             if self._device.itemData(i) == settings.inference_device),
            0,
        )
        self._device.setCurrentIndex(idx)
        form.addRow("Processing", self._device)

        # Microphone
        self._mic = QComboBox()
        self._mic.addItem("System default", None)
        try:
            for idx, name in AudioCapture.list_input_devices():
                self._mic.addItem(name, idx)
        except Exception:
            pass
        if settings.microphone is not None:
            for i in range(self._mic.count()):
                if self._mic.itemData(i) == settings.microphone:
                    self._mic.setCurrentIndex(i)
                    break
        form.addRow("Microphone", self._mic)

        # Mic level meter (decorative)
        self._level = QProgressBar()
        self._level.setRange(0, 100)
        self._level.setValue(0)
        self._level.setTextVisible(False)
        form.addRow("Input level", self._level)

        layout.addLayout(form)
        outer.addWidget(card)
        outer.addStretch(1)

    def _browse_model(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose model directory")
        if path:
            self._model.setText(path)

    def write_back(self, settings) -> None:
        settings.model_path = self._model.text().strip()
        settings.language = self._language.currentData() or "auto"
        settings.inference_device = self._device.currentData() or "auto"
        settings.microphone = self._mic.currentData()


__all__ = ["DictationTab"]
