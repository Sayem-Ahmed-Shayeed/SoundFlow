from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from soundflow.core.settings import data_directory


@dataclass(frozen=True, slots=True)
class WhisperModelSpec:
    model_id: str
    display_name: str
    guidance: str
    repo_id: str
    download_size: str
    recommended: bool = False

    @property
    def directory_name(self) -> str:
        return f"faster-whisper-{self.model_id}"


MODEL_CATALOG = (
    WhisperModelSpec(
        "tiny",
        "Tiny",
        "Fastest, lowest resource use",
        "Systran/faster-whisper-tiny",
        "78 MB",
    ),
    WhisperModelSpec(
        "base",
        "Base",
        "Fast and lightweight",
        "Systran/faster-whisper-base",
        "148 MB",
    ),
    WhisperModelSpec(
        "small",
        "Small",
        "Recommended balance",
        "Systran/faster-whisper-small",
        "486 MB",
        True,
    ),
    WhisperModelSpec(
        "medium",
        "Medium",
        "Higher accuracy, heavier",
        "Systran/faster-whisper-medium",
        "1.53 GB",
    ),
    WhisperModelSpec(
        "large-v3-turbo",
        "Large-v3 Turbo",
        "Best quality, highest resource use",
        "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        "1.62 GB",
    ),
)


def model_spec(model_id: str) -> WhisperModelSpec:
    for item in MODEL_CATALOG:
        if item.model_id == model_id:
            return item
    raise KeyError(f"unknown Whisper model: {model_id}")


def managed_models_root(root: Path | None = None) -> Path:
    return root or data_directory() / "models"


def managed_model_path(item: WhisperModelSpec, root: Path | None = None) -> Path:
    return managed_models_root(root) / item.directory_name
