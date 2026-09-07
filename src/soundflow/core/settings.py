from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


APP_NAME = "Soundflow"
SHORTCUT_SCHEMA_VERSION = 2
DEFAULT_PUSH_TO_TALK = "ctrl+alt+space"


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
    shortcut_schema_version: int = SHORTCUT_SCHEMA_VERSION
    appearance: str = "dark"
    model_path: str = ""
    language: str = "auto"
    inference_device: str = "cpu"
    compute_type: str = "int8"
    microphone: int | None = None
    global_hotkeys: bool = True
    show_shortcut_hint: bool = False
    toggle_hotkey: str = "ctrl+d"
    push_to_talk_hotkey: str = DEFAULT_PUSH_TO_TALK
    hotkey_authorized: bool = False
    insert_hotkey: str = "ctrl+i"
    silence_threshold: float = 0.012
    silence_duration_ms: int = 700
    min_speech_ms: int = 250
    max_speech_s: int = 20
    auto_copy: bool = False
    auto_insert: bool = True
    terminal_paste: bool = False
    show_dictation_widget: bool = True
    auto_save_transcripts: bool = True
    start_minimized: bool = False
    remote_desktop_restore_token: str = ""
    ai_cleanup_enabled: bool = False
    ai_auto_clean: bool = False
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    ai_preset: str = "clean"
    ai_custom_instruction: str = ""

    def normalized(self) -> "Settings":
        from soundflow.hotkeys import canonical_hotkey

        self.shortcut_schema_version = SHORTCUT_SCHEMA_VERSION
        if self.appearance not in {"light", "dark"}:
            self.appearance = "dark"
        self.language = self.language.strip() or "auto"
        self.inference_device = (
            self.inference_device if self.inference_device in {"cpu", "cuda"} else "cpu"
        )
        self.compute_type = "int8"
        self.toggle_hotkey = self.toggle_hotkey.lower()
        self.insert_hotkey = self.insert_hotkey.lower()
        try:
            self.push_to_talk_hotkey = canonical_hotkey(
                self.push_to_talk_hotkey
            )
        except ValueError:
            self.push_to_talk_hotkey = DEFAULT_PUSH_TO_TALK
            self.hotkey_authorized = False
        self.silence_threshold = min(max(float(self.silence_threshold), 0.001), 0.5)
        self.silence_duration_ms = min(max(int(self.silence_duration_ms), 200), 3000)
        self.min_speech_ms = min(max(int(self.min_speech_ms), 100), 3000)
        self.max_speech_s = min(max(int(self.max_speech_s), 5), 60)
        self.openrouter_api_key = self.openrouter_api_key.strip()
        self.openrouter_model = self.openrouter_model.strip()
        self.gemini_api_key = self.gemini_api_key.strip()
        self.gemini_model = (self.gemini_model.strip() or "gemini-2.5-flash")[:120]
        if self.ai_provider not in {"gemini", "openrouter"}:
            self.ai_provider = "gemini"
        if self.ai_preset not in {"clean", "concise", "custom"}:
            self.ai_preset = "clean"
        self.ai_custom_instruction = self.ai_custom_instruction.strip()[:2000]
        if not self.ai_cleanup_enabled:
            self.ai_auto_clean = False
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
            settings = Settings(**known)
            stored_schema = int(payload.get("shortcut_schema_version", 0))
            migrated = stored_schema < SHORTCUT_SCHEMA_VERSION
            if migrated:
                settings.push_to_talk_hotkey = DEFAULT_PUSH_TO_TALK
                settings.hotkey_authorized = False
                settings.shortcut_schema_version = SHORTCUT_SCHEMA_VERSION
            settings.normalized()
            if migrated:
                self.save(settings)
            return settings
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
