"""Dictation tab — model path, language, processing device, microphone."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from soundflow.audio import AudioCapture
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
from soundflow.preferences.model_manager import ModelManagerWidget


class DictationTab(QWidget):
    """Dictation preferences tab."""

    model_path_changed = Signal(str)

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dictationTab")
        self._settings = settings

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("dictationScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.viewport().setObjectName("dictationScrollViewport")

        content = QWidget()
        content.setObjectName("dictationContent")
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(SPACE_4, SPACE_4, SPACE_4, SPACE_4)
        content_layout.setSpacing(SPACE_4)
        content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        card = QWidget()
        card.setObjectName("preferencesCard")
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE_3, SPACE_3, SPACE_3, SPACE_3)
        layout.setSpacing(SPACE_2)

        title = QLabel("Recognition")
        title.setFont(QFont(BODY_FONT, FONT_HEADING))
        title.setObjectName("headingText")
        layout.addWidget(title)

        self._model_manager = ModelManagerWidget(settings)
        self._model_manager.model_path_selected.connect(self._model_selected)
        layout.addWidget(self._model_manager)

        form = QFormLayout()
        form.setSpacing(SPACE_2)

        # Model directory
        model_row = QHBoxLayout()
        model_row.setSpacing(SPACE_2)
        self._model = QLineEdit(settings.model_path)
        self._model.setObjectName("compactPathField")
        self._model.setPlaceholderText("Path to faster-whisper model")
        self._model.setFont(QFont(BODY_FONT, FONT_BODY))
        self._model.setFixedHeight(CONTROL_HEIGHT_SM)
        model_row.addWidget(self._model, 1)
        browse = QPushButton("Browse")
        browse.setObjectName("compactBrowseButton")
        browse.setFixedHeight(CONTROL_HEIGHT_SM)
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._browse_model)
        model_row.addWidget(browse)
        form.addRow("Model directory", model_row)

        # Language
        self._language = QComboBox()
        self._language.setObjectName("compactPreferenceField")
        self._language.setFixedHeight(CONTROL_HEIGHT_SM)
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
        self._device.setObjectName("compactPreferenceField")
        self._device.setFixedHeight(CONTROL_HEIGHT_SM)
        for label, value in (("CPU", "cpu"), ("GPU", "cuda")):
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
        self._mic.setObjectName("compactPreferenceField")
        self._mic.setFixedHeight(CONTROL_HEIGHT_SM)
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

        layout.addLayout(form)
        content_layout.addWidget(card)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _browse_model(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose model directory")
        if path:
            self._model.setText(path)
            self._model.editingFinished.emit()

    def _model_selected(self, path: str) -> None:
        self._model.setText(path)
        self._settings.model_path = path
        self.model_path_changed.emit(path)

    def write_back(self, settings) -> None:
        settings.model_path = self._model.text().strip()
        settings.language = self._language.currentData() or "auto"
        settings.inference_device = self._device.currentData() or "auto"
        settings.microphone = self._mic.currentData()

    def shutdown(self) -> None:
        self._model_manager.shutdown()


__all__ = ["DictationTab"]
