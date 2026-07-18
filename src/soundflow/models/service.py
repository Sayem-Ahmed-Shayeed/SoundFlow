from __future__ import annotations

import hashlib
import json
import shutil
import threading
import uuid
from collections.abc import Callable
from pathlib import Path

from soundflow.core.settings import default_model_path
from soundflow.models.catalog import (
    WhisperModelSpec,
    managed_model_path,
    managed_models_root,
    model_spec,
)

ProgressCallback = Callable[[str, int], None]
DownloadFunction = Callable[
    [WhisperModelSpec, Path, ProgressCallback, threading.Event], None
]
REQUIRED_FILES = ("model.bin", "config.json")
ALLOW_PATTERNS = (
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
)


class ModelManagerError(RuntimeError):
    pass


class ModelDownloadCancelled(ModelManagerError):
    pass


def _is_valid_model(path: Path) -> bool:
    return path.is_dir() and all((path / name).is_file() for name in REQUIRED_FILES)


def _validate_model(path: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (path / name).is_file()]
    if missing:
        raise ModelManagerError(
            "Downloaded model is incomplete; missing " + ", ".join(missing)
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_manifest(path: Path, model_id: str) -> None:
    files = {
        item.name: {"bytes": item.stat().st_size, "sha256": _sha256(item)}
        for item in sorted(path.iterdir())
        if item.is_file() and item.name != "soundflow-manifest.json"
    }
    payload = {
        "format": 1,
        "engine": "faster-whisper",
        "model": model_id,
        "files": files,
    }
    (path / "soundflow-manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _download_snapshot(
    spec: WhisperModelSpec,
    target: Path,
    progress: ProgressCallback,
    cancel_event: threading.Event,
) -> None:
    from huggingface_hub import snapshot_download
    from tqdm.auto import tqdm

    highest = 1

    class ReportingTqdm(tqdm):
        def update(self, amount=1):
            nonlocal highest
            if cancel_event.is_set():
                raise ModelDownloadCancelled("Download cancelled")
            result = super().update(amount)
            if self.total:
                highest = max(highest, min(95, int(self.n * 95 / self.total)))
                progress("Downloading", highest)
            return result

    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=spec.repo_id,
        local_dir=target,
        allow_patterns=list(ALLOW_PATTERNS),
        max_workers=1,
        tqdm_class=ReportingTqdm,
    )
    if cancel_event.is_set():
        raise ModelDownloadCancelled("Download cancelled")


class ModelService:
    def __init__(
        self,
        root: Path | None = None,
        downloader: DownloadFunction | None = None,
    ) -> None:
        self.root = managed_models_root(root)
        self._downloader = downloader or _download_snapshot

    def installed_path(self, model_id: str) -> Path | None:
        item = model_spec(model_id)
        managed = managed_model_path(item, self.root)
        if _is_valid_model(managed):
            return managed
        if model_id == "small":
            bundled = default_model_path()
            if (
                bundled.name == item.directory_name
                and bundled != managed
                and _is_valid_model(bundled)
            ):
                return bundled
        return None

    def install(
        self,
        model_id: str,
        *,
        progress: ProgressCallback,
        cancel_event: threading.Event | None = None,
    ) -> Path:
        item = model_spec(model_id)
        cancel = cancel_event or threading.Event()
        final = managed_model_path(item, self.root)
        partial = final.with_name(final.name + ".partial")
        completed = False
        try:
            if _path_exists(partial):
                _remove_path(partial)
            self.root.mkdir(parents=True, exist_ok=True)
            progress("Preparing", 0)
            if cancel.is_set():
                raise ModelDownloadCancelled("Download cancelled")
            if not final.is_symlink() and _is_valid_model(final):
                completed = True
                progress("Ready", 100)
                return final
            self._downloader(item, partial, progress, cancel)
            if cancel.is_set():
                raise ModelDownloadCancelled("Download cancelled")
            progress("Verifying", 96)
            shutil.rmtree(partial / ".cache", ignore_errors=True)
            _validate_model(partial)
            _write_manifest(partial, item.model_id)

            backup = None
            if _path_exists(final):
                backup = final.with_name(f"{final.name}.backup-{uuid.uuid4().hex}")
                final.replace(backup)
            try:
                partial.replace(final)
            except Exception:
                if backup is not None:
                    if _path_exists(final):
                        _remove_path(final)
                    backup.replace(final)
                raise
            completed = True
            if backup is not None:
                _remove_path(backup)
            progress("Ready", 100)
            return final
        except (ModelDownloadCancelled, ModelManagerError):
            raise
        except OSError as exc:
            raise ModelManagerError(f"Could not install the model: {exc}") from exc
        except Exception as exc:
            raise ModelManagerError("Could not download the model.") from exc
        finally:
            if not completed and _path_exists(partial):
                if partial.is_symlink() or partial.is_file():
                    partial.unlink(missing_ok=True)
                else:
                    shutil.rmtree(partial, ignore_errors=True)

    def delete(self, model_id: str, *, active_path: Path) -> None:
        target = managed_model_path(model_spec(model_id), self.root).expanduser()
        root = self.root.expanduser().resolve()
        active = active_path.expanduser().resolve()
        if target.is_symlink() or target.parent.resolve() != root:
            raise ModelManagerError("Soundflow can only delete managed models.")
        if target.resolve() == active:
            raise ModelManagerError("The active model cannot be deleted.")
        if target.exists():
            shutil.rmtree(target)
