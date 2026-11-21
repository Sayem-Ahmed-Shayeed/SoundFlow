"""Speech model tab: the installed models, where they run, and an optional folder."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QPushButton, QToolButton, QVBoxLayout, QWidget

from soundflow.preferences.model_manager import ModelManagerWidget
from soundflow.preferences.widgets import PreferenceTab, SettingsCard, SettingsRow
from soundflow.ui.widgets import SegmentedControl

DEVICE_OPTIONS = (
    ("auto", "Automatic"),
    ("cuda", "GPU"),
    ("cpu", "Processor"),
)
DEVICE_DESCRIPTIONS = {
    "auto": "Uses your NVIDIA GPU when it’s available, and the processor otherwise.",
    "cuda": "Fastest. Needs an NVIDIA GPU with CUDA.",
    "cpu": "Works on every computer. Slower with the larger models.",
}
FOLDER_HINT = "For a faster-whisper model you converted yourself."


class SpeechModelTab(PreferenceTab):
    """Speech model preferences tab."""

    model_path_changed = Signal(str)

    def __init__(self, settings, parent: QWidget | None = None) -> None:
        super().__init__("speechModelTab", "Speech model", parent)
        self._settings = settings

        self._model_manager = ModelManagerWidget(settings)
        self._model_manager.model_path_selected.connect(self.model_path_changed)
        models = self.add_group(
            note="Models run on this computer. Your voice is never sent anywhere.",
        )
        models.add_row(self._model_manager)

        processing = self.add_group("Processing")
        self._device = SegmentedControl(
            DEVICE_OPTIONS,
            settings.inference_device,
            accessible_name="Run the model on",
        )
        self._device.changed.connect(self._sync_device_text)
        self._device_row = SettingsRow(
            "Run the model on",
            DEVICE_DESCRIPTIONS.get(settings.inference_device, DEVICE_DESCRIPTIONS["auto"]),
            self._device,
        )
        processing.add_row(self._device_row)

        self._advanced_toggle = QToolButton()
        self._advanced_toggle.setObjectName("disclosureButton")
        self._advanced_toggle.setText("Advanced")
        self._advanced_toggle.setCheckable(True)
        self._advanced_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._advanced_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self._advanced_toggle.setAutoRaise(True)
        self._advanced_toggle.toggled.connect(self._toggle_advanced)
        self._advanced_body = QWidget()
        self._advanced_body.setVisible(False)
        advanced_layout = QVBoxLayout(self._advanced_body)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(8)
        folder_card = SettingsCard()
        self._choose = QPushButton("Choose folder")
        self._choose.setObjectName("quietButton")
        self._choose.setCursor(Qt.CursorShape.PointingHandCursor)
        self._choose.clicked.connect(self._browse_model)
        self._folder_row = SettingsRow("Use a model from a folder", FOLDER_HINT, self._choose)
        folder_card.add_row(self._folder_row)
        advanced_layout.addWidget(folder_card)

        self.body.addSpacing(24)
        self.body.addWidget(self._advanced_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self.body.addWidget(self._advanced_body)
        self._refresh_folder_text()
        self.finish()

    # -- behaviour ----------------------------------------------------------
    def _sync_device_text(self, value: str) -> None:
        self._device_row.set_description(DEVICE_DESCRIPTIONS.get(value, ""))

    def _toggle_advanced(self, expanded: bool) -> None:
        self._advanced_body.setVisible(bool(expanded))
        self._advanced_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def _is_managed(self, path: str) -> bool:
        if not path:
            return True
        try:
            managed_root = self._model_manager._service.root
            return Path(path).expanduser().is_relative_to(managed_root)
        except (OSError, ValueError):
            return False

    def _refresh_folder_text(self) -> None:
        path = self._settings.model_path or ""
        if path and not self._is_managed(path):
            self._folder_row.set_description(f"Using {path}")
        else:
            self._folder_row.set_description(FOLDER_HINT)

    def _browse_model(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose model folder")
        if not path:
            return
        self._settings.model_path = path
        self._refresh_folder_text()
        self._model_manager._refresh_rows()
        self.model_path_changed.emit(path)

    def shutdown(self) -> None:
        self._model_manager.shutdown()

    # -- settings -----------------------------------------------------------
    def write_back(self, settings) -> None:
        settings.inference_device = self._device.value()

    def refresh_from_settings(self, settings=None) -> None:
        source = settings if settings is not None else self._settings
        self._device.set_value(source.inference_device)
        self._sync_device_text(source.inference_device)
        self._refresh_folder_text()
        self._model_manager._refresh_rows()


__all__ = ["SpeechModelTab"]
