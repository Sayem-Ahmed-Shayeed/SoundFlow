"""Read-only local readiness checks for the Preferences System tab."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from soundflow.audio import AudioCapture
from soundflow.core.settings import default_model_path


@dataclass(frozen=True)
class SystemCheckResult:
    model_ready: bool
    microphone_ready: bool
    hotkey_ready: bool
    paste_ready: bool
    effective_device: str

    @property
    def ready(self) -> bool:
        return self.model_ready and self.microphone_ready


def _cuda_devices() -> int:
    try:
        import ctranslate2
        return int(ctranslate2.get_cuda_device_count())
    except (ImportError, RuntimeError, OSError):
        return 0


def run_system_check(
    settings,
    *,
    list_inputs: Callable[[], list[tuple[int, str]]] = AudioCapture.list_input_devices,
    cuda_devices: Callable[[], int] = _cuda_devices,
) -> SystemCheckResult:
    model = Path(settings.model_path or default_model_path())
    try:
        microphones = list_inputs()
    except Exception:
        microphones = []
    effective = settings.inference_device
    if effective == "cuda" and cuda_devices() < 1:
        effective = "cpu"
    return SystemCheckResult(
        model_ready=model.is_dir(),
        microphone_ready=bool(microphones),
        hotkey_ready=not settings.global_hotkeys or settings.hotkey_authorized,
        paste_ready=bool(settings.remote_desktop_restore_token),
        effective_device=effective,
    )


__all__ = ["SystemCheckResult", "run_system_check"]
