from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


APP_NAME = "Soundflow"


def config_directory() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return root / APP_NAME
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / APP_NAME.lower()


def data_directory() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / APP_NAME
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / APP_NAME.lower()


@dataclass
class Settings:
    model_path: str = ""
    language: str = "auto"
    inference_device: str = "cpu"
    compute_type: str = "int8"
    microphone: int | None = None
    global_hotkeys: bool = True
    toggle_hotkey: str = "ctrl+d"
    push_to_talk_hotkey: str = "ctrl+space"
    insert_hotkey: str = "ctrl+i"
    silence_threshold: float = 0.012
    silence_duration_ms: int = 700
    min_speech_ms: int = 250
    max_speech_s: int = 20
    auto_copy: bool = False
    start_minimized: bool = False
    remote_desktop_restore_token: str = ""

    def normalized(self) -> "Settings":
        self.language = self.language.strip() or "auto"
        self.inference_device = (
            self.inference_device if self.inference_device in {"cpu", "cuda"} else "cpu"
        )
        self.compute_type = "int8"
        legacy_shortcuts = {
            "ctrl+alt+d": "ctrl+d",
            "ctrl+alt+space": "ctrl+space",
            "ctrl+alt+i": "ctrl+i",
        }
        self.toggle_hotkey = legacy_shortcuts.get(
            self.toggle_hotkey.lower(), self.toggle_hotkey.lower()
        )
        self.push_to_talk_hotkey = legacy_shortcuts.get(
            self.push_to_talk_hotkey.lower(), self.push_to_talk_hotkey.lower()
        )
        self.insert_hotkey = legacy_shortcuts.get(
            self.insert_hotkey.lower(), self.insert_hotkey.lower()
        )
        self.silence_threshold = min(max(float(self.silence_threshold), 0.001), 0.5)
        self.silence_duration_ms = min(max(int(self.silence_duration_ms), 200), 3000)
        self.min_speech_ms = min(max(int(self.min_speech_ms), 100), 3000)
        self.max_speech_s = min(max(int(self.max_speech_s), 5), 60)
        return self


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_directory() / "settings.json"

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            known: dict[str, Any] = {
                key: value
                for key, value in payload.items()
                if key in Settings.__dataclass_fields__
            }
            return Settings(**known).normalized()
        except (OSError, ValueError, TypeError):
            return Settings()

    def save(self, settings: Settings) -> None:
        settings.normalized()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(asdict(settings), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


def default_model_path() -> Path:
    configured = os.environ.get("SOUNDFLOW_MODEL_PATH")
    if configured:
        return Path(configured).expanduser()
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    bundled = bundle_root / "models" / "faster-whisper-small"
    if bundled.is_dir():
        return bundled
    return data_directory() / "models" / "faster-whisper-small"
