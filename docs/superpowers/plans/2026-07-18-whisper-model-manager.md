# Whisper Model Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact Settings model manager that downloads, activates, and safely deletes Tiny, Base, Small, Medium, and Large-v3 Turbo faster-whisper models.

**Architecture:** A pure-Python catalog and service own model metadata, validated downloads, manifests, cancellation, and filesystem safety. A Qt widget owns a background thread and renders model rows; DictationTab and PreferencesPage route successful selection through the existing settings persistence and deferred runtime-rebuild path.

**Tech Stack:** Python 3.11+, PySide6, faster-whisper, huggingface_hub, unittest, PyInstaller.

## Global Constraints

- Support exactly `tiny`, `base`, `small`, `medium`, and `large-v3-turbo`.
- Preserve the custom model-directory Browse control.
- Run only one download at a time and never block the Qt UI thread.
- Download to a partial directory, validate, create a manifest, then promote atomically.
- Automatically activate a successful download without interrupting active dictation.
- Delete only inactive catalog-managed models; never delete custom or bundled paths.
- Preserve the previous active model after failure or cancellation.
- Rebuild and freshly reinstall Soundflow after implementation, then verify the service.

---

## File Map

- Create `src/soundflow/models/{__init__,catalog,service}.py` for the non-Qt domain layer.
- Create `src/soundflow/preferences/model_manager.py` for rows and the download thread.
- Modify `src/soundflow/preferences/tabs/dictation.py`, `src/soundflow/preferences/page.py`, and `src/soundflow/ui/main_window.py` for persistence/runtime integration and clean shutdown.
- Modify `src/soundflow/design/theme.py` for compact light/dark styles.
- Modify `packaging/soundflow.spec` and `README.md` for distribution and documentation.
- Create `tests/test_model_catalog.py`, `tests/test_model_service.py`, and `tests/test_model_manager_ui.py`.
- Modify `tests/test_dictation_tab_ui.py`, `tests/test_ui_runtime_contracts.py`, and `tests/test_design.py`.

---

### Task 1: Curated Model Catalog

**Files:**
- Create: `src/soundflow/models/catalog.py`
- Create: `src/soundflow/models/__init__.py`
- Test: `tests/test_model_catalog.py`

**Interfaces:**
- Produces `WhisperModelSpec`, `MODEL_CATALOG`, `model_spec(model_id)`, `managed_models_root(root=None)`, and `managed_model_path(spec, root=None)`.
- Consumes `soundflow.core.settings.data_directory`.

- [ ] **Step 1: Write the failing catalog test**

```python
import tempfile
import unittest
from pathlib import Path

from soundflow.models.catalog import MODEL_CATALOG, managed_model_path, model_spec


class ModelCatalogTests(unittest.TestCase):
    def test_catalog_is_curated_and_small_is_recommended(self):
        self.assertEqual(
            [item.model_id for item in MODEL_CATALOG],
            ["tiny", "base", "small", "medium", "large-v3-turbo"],
        )
        self.assertEqual(
            [item.model_id for item in MODEL_CATALOG if item.recommended],
            ["small"],
        )
        self.assertEqual(
            model_spec("large-v3-turbo").repo_id,
            "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        )
        self.assertEqual(
            [item.download_size for item in MODEL_CATALOG],
            ["78 MB", "148 MB", "486 MB", "1.53 GB", "1.62 GB"],
        )

    def test_managed_path_is_catalog_derived(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                managed_model_path(model_spec("tiny"), root),
                root / "faster-whisper-tiny",
            )

    def test_unknown_model_is_rejected(self):
        with self.assertRaisesRegex(KeyError, "unknown Whisper model"):
            model_spec("large")
```

- [ ] **Step 2: Run it and verify RED**

```bash
PYTHONPATH=.vendor/python:src python3 -m unittest tests.test_model_catalog -v
```

Expected: `ModuleNotFoundError: No module named 'soundflow.models'`.

- [ ] **Step 3: Implement the catalog**

```python
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
    WhisperModelSpec("tiny", "Tiny", "Fastest, lowest resource use", "Systran/faster-whisper-tiny", "78 MB"),
    WhisperModelSpec("base", "Base", "Fast and lightweight", "Systran/faster-whisper-base", "148 MB"),
    WhisperModelSpec("small", "Small", "Recommended balance", "Systran/faster-whisper-small", "486 MB", True),
    WhisperModelSpec("medium", "Medium", "Higher accuracy, heavier", "Systran/faster-whisper-medium", "1.53 GB"),
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
```

Re-export the five public symbols from `soundflow.models.__init__`.

- [ ] **Step 4: Verify GREEN and commit**

```bash
PYTHONPATH=.vendor/python:src python3 -m unittest tests.test_model_catalog -v
git add src/soundflow/models tests/test_model_catalog.py
git commit -m "Add curated Whisper model catalog"
```

Expected: 3 tests pass and the catalog commit is created.

---

### Task 2: Validated Download and Safe Deletion Service

**Files:**
- Create: `src/soundflow/models/service.py`
- Modify: `src/soundflow/models/__init__.py`
- Test: `tests/test_model_service.py`

**Interfaces:**
- Produces `ModelService`, `ModelManagerError`, `ModelDownloadCancelled`, and `ProgressCallback`.
- Accepts an injected `DownloadFunction(spec, target, progress, cancel_event)` in tests.
- Consumes catalog functions from Task 1 and `default_model_path()` for bundled Small detection.

- [ ] **Step 1: Write failing service tests**

```python
import json
import tempfile
import threading
import unittest
from pathlib import Path

from soundflow.models import ModelDownloadCancelled, ModelManagerError, ModelService


def valid_model(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "model.bin").write_bytes(b"weights")
    (target / "config.json").write_text("{}", encoding="utf-8")
    (target / "tokenizer.json").write_text("{}", encoding="utf-8")


class ModelServiceTests(unittest.TestCase):
    def test_install_manifests_and_promotes_partial_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []

            def downloader(spec, target, progress, cancel_event):
                self.assertEqual(spec.model_id, "tiny")
                self.assertTrue(target.name.endswith(".partial"))
                valid_model(target)
                progress("Downloading", 80)

            service = ModelService(root=root, downloader=downloader)
            installed = service.install(
                "tiny",
                progress=lambda phase, value: events.append((phase, value)),
                cancel_event=threading.Event(),
            )
            self.assertEqual(installed, root / "faster-whisper-tiny")
            self.assertFalse((root / "faster-whisper-tiny.partial").exists())
            manifest = json.loads(
                (installed / "soundflow-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["model"], "tiny")
            self.assertIn("model.bin", manifest["files"])
            self.assertEqual(events[-1], ("Ready", 100))

    def test_cancel_and_validation_failure_clean_partial_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def cancelled(spec, target, progress, cancel_event):
                target.mkdir(parents=True)
                (target / "partial.bin").write_bytes(b"partial")
                raise ModelDownloadCancelled("Download cancelled")

            service = ModelService(root=root, downloader=cancelled)
            with self.assertRaises(ModelDownloadCancelled):
                service.install("base", progress=lambda *_: None)
            self.assertFalse((root / "faster-whisper-base.partial").exists())

            def incomplete(spec, target, progress, cancel_event):
                target.mkdir(parents=True)
                (target / "config.json").write_text("{}", encoding="utf-8")

            service = ModelService(root=root, downloader=incomplete)
            with self.assertRaisesRegex(ModelManagerError, "model.bin"):
                service.install("medium", progress=lambda *_: None)
            self.assertFalse((root / "faster-whisper-medium.partial").exists())

    def test_delete_refuses_active_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "faster-whisper-tiny"
            valid_model(target)
            service = ModelService(root=root)
            with self.assertRaisesRegex(ModelManagerError, "active"):
                service.delete("tiny", active_path=target)
            service.delete("tiny", active_path=root / "faster-whisper-small")
            self.assertFalse(target.exists())
```

- [ ] **Step 2: Run it and verify RED**

```bash
PYTHONPATH=.vendor/python:src python3 -m unittest tests.test_model_service -v
```

Expected: import failure for `ModelService`.

- [ ] **Step 3: Implement service contracts and validation**

```python
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
            if partial.exists():
                shutil.rmtree(partial)
            self.root.mkdir(parents=True, exist_ok=True)
            progress("Preparing", 0)
            if cancel.is_set():
                raise ModelDownloadCancelled("Download cancelled")
            self._downloader(item, partial, progress, cancel)
            if cancel.is_set():
                raise ModelDownloadCancelled("Download cancelled")
            progress("Verifying", 96)
            shutil.rmtree(partial / ".cache", ignore_errors=True)
            _validate_model(partial)
            _write_manifest(partial, item.model_id)
            if final.exists():
                shutil.rmtree(final)
            partial.replace(final)
            completed = True
            progress("Ready", 100)
            return final
        except (ModelDownloadCancelled, ModelManagerError):
            raise
        except OSError as exc:
            raise ModelManagerError(f"Could not install the model: {exc}") from exc
        except Exception as exc:
            raise ModelManagerError("Could not download the model.") from exc
        finally:
            if not completed and partial.exists():
                shutil.rmtree(partial, ignore_errors=True)

    def delete(self, model_id: str, *, active_path: Path) -> None:
        target = managed_model_path(model_spec(model_id), self.root).resolve()
        root = self.root.expanduser().resolve()
        active = active_path.expanduser().resolve()
        if target == active:
            raise ModelManagerError("The active model cannot be deleted.")
        if target.parent != root:
            raise ModelManagerError("Soundflow can only delete managed models.")
        if target.exists():
            shutil.rmtree(target)
```

Use these complete helpers above the class:

```python
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
```

Complete the method bodies as follows:

- `installed_path` validates the managed catalog path; for Small it also checks
  the bundled `default_model_path()` and returns it only when required files exist.
- `install` removes a stale sibling `.partial`, reports `Preparing/0`, invokes
  the downloader, checks cancellation, reports `Verifying/96`, removes the Hub
  `.cache` folder, validates required files, writes `soundflow-manifest.json`
  with top-level file byte counts and SHA-256 digests, renames partial to final,
  and reports `Ready/100`.
- `install` always removes the partial directory on failure and preserves
  `ModelDownloadCancelled` while normalizing network, permission, and disk errors
  to `ModelManagerError`.
- `delete` resolves both paths, rejects the active path, proves the target's
  parent equals the managed root, and deletes only the catalog-derived directory.

- [ ] **Step 4: Implement Hub download progress and cancellation**

```python
def _download_snapshot(spec, target, progress, cancel_event):
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
```

- [ ] **Step 5: Verify GREEN and commit**

```bash
PYTHONPATH=.vendor/python:src python3 -m unittest \
  tests.test_model_catalog tests.test_model_service tests.test_model_integrity -v
git add src/soundflow/models tests/test_model_service.py
git commit -m "Add safe Whisper model installation service"
```

Expected: all focused domain tests pass.

---

### Task 3: Background Worker and Compact Model Rows

**Files:**
- Create: `src/soundflow/preferences/model_manager.py`
- Modify: `src/soundflow/design/theme.py`
- Modify: `tests/test_design.py`
- Test: `tests/test_model_manager_ui.py`

**Interfaces:**
- Produces `ModelDownloadThread` and `ModelManagerWidget.model_path_selected(str)`.
- Consumes a live `Settings` object and injectable `ModelService`.
- Object names are `modelManagerCard`, `modelRow:<id>`, `modelStatus:<id>`,
  `modelAction:<id>`, `modelDelete:<id>`, `modelProgress:<id>`, and `modelError:<id>`.

- [ ] **Step 1: Write failing row-state tests**

```python
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QPushButton
from soundflow.core.settings import Settings
from soundflow.models.catalog import managed_model_path, model_spec
from soundflow.preferences.model_manager import ModelManagerWidget


class FakeService:
    def __init__(self, root, installed=()):
        self.root = Path(root)
        self.installed = set(installed)
        self.deleted = []

    def installed_path(self, model_id):
        if model_id not in self.installed:
            return None
        return managed_model_path(model_spec(model_id), self.root)

    def delete(self, model_id, *, active_path):
        self.deleted.append((model_id, Path(active_path)))
        self.installed.discard(model_id)


class ModelManagerUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_five_rows_map_active_installed_and_missing_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = managed_model_path(model_spec("small"), root)
            widget = ModelManagerWidget(
                Settings(model_path=str(active)),
                service=FakeService(root, ("base", "small")),
            )
            self.assertEqual(
                widget.findChild(QLabel, "modelStatus:small").text(), "Active"
            )
            self.assertEqual(
                widget.findChild(QPushButton, "modelAction:base").text(), "Use"
            )
            self.assertEqual(
                widget.findChild(QPushButton, "modelAction:tiny").text(), "Download"
            )
            self.assertEqual(len(widget.findChildren(QProgressBar)), 5)

    def test_use_selects_installed_path_and_protects_new_active_row(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = FakeService(root, ("base", "small"))
            widget = ModelManagerWidget(Settings(), service=service)
            selected = []
            widget.model_path_selected.connect(selected.append)
            widget.findChild(QPushButton, "modelAction:base").click()
            self.assertEqual(
                selected,
                [str(managed_model_path(model_spec("base"), root))],
            )
            self.assertEqual(
                widget.findChild(QLabel, "modelStatus:base").text(), "Active"
            )

    def test_progress_and_errors_are_inline(self):
        with tempfile.TemporaryDirectory() as directory:
            widget = ModelManagerWidget(
                Settings(), service=FakeService(directory)
            )
            widget._show_progress("tiny", "Downloading", 42)
            progress = widget.findChild(QProgressBar, "modelProgress:tiny")
            self.assertEqual(progress.value(), 42)
            widget._show_error("tiny", "Network unavailable")
            self.assertIn(
                "Network unavailable",
                widget.findChild(QLabel, "modelError:tiny").text(),
            )

    def test_success_automatically_selects_the_downloaded_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = FakeService(root)
            settings = Settings()
            widget = ModelManagerWidget(settings, service=service)
            selected = []
            widget.model_path_selected.connect(selected.append)
            path = managed_model_path(model_spec("tiny"), root)
            service.installed.add("tiny")
            widget._download_succeeded("tiny", str(path))
            self.assertEqual(settings.model_path, str(path))
            self.assertEqual(selected, [str(path)])
```

- [ ] **Step 2: Run it and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_model_manager_ui -v
```

Expected: missing module `soundflow.preferences.model_manager`.

- [ ] **Step 3: Implement the QThread worker**

```python
class ModelDownloadThread(QThread):
    phase_changed = Signal(str, int)
    installed = Signal(str)
    cancelled = Signal()
    failed = Signal(str)

    def __init__(self, service, model_id, parent=None):
        super().__init__(parent)
        self._service = service
        self._model_id = model_id
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def run(self):
        try:
            path = self._service.install(
                self._model_id,
                progress=self.phase_changed.emit,
                cancel_event=self._cancel_event,
            )
        except ModelDownloadCancelled:
            self.cancelled.emit()
        except ModelManagerError as exc:
            self.failed.emit(str(exc))
        except Exception:
            self.failed.emit("The model download failed unexpectedly.")
        else:
            self.installed.emit(str(path))
```

- [ ] **Step 4: Implement `ModelManagerWidget`**

Store each row in this dataclass:

```python
@dataclass(slots=True)
class _ModelRow:
    container: QWidget
    status: QLabel
    action: QPushButton
    delete: QPushButton
    progress: QProgressBar
    phase: QLabel
    error: QLabel
```

The widget must create five compact rows, show each catalog entry's approximate
download size beside its guidance, show Small's `Recommended` badge,
resolve active path from `settings.model_path or default_model_path()`, and map
status/actions as follows:

- Active: `Active`, disabled primary action, hidden Delete.
- Installed managed inactive: `Installed`, `Use`, visible Delete.
- Installed bundled Small inactive: `Installed`, `Use`, hidden Delete.
- Missing: `Not downloaded`, `Download`, hidden Delete.

`Use` updates the live settings object, refreshes rows, and emits
`model_path_selected`. `Download` starts one worker, changes its action to
`Cancel`, disables other actions, and connects progress/failure/cancel/success
signals. Success updates settings and emits the final path. Delete calls the
service with a freshly resolved active path and renders errors inline.
`shutdown()` cancels a running worker and waits up to five seconds for its
thread to finish so Qt cannot destroy an active QThread.

- [ ] **Step 5: Add compact theme rules and assertions**

Add light/dark rules for the declared object names using existing palette
variables. Primary row actions use the 20px compact content height, Delete uses
the semantic error color, and progress bars are 4px tall with violet chunks and
hidden text. Extend `tests/test_design.py` to assert both generated stylesheets
contain the manager, row, progress, focus, and destructive selectors.

- [ ] **Step 6: Verify GREEN and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_manager_ui tests.test_design -v
git add src/soundflow/preferences/model_manager.py src/soundflow/design/theme.py \
  tests/test_model_manager_ui.py tests/test_design.py
git commit -m "Add compact Whisper model manager UI"
```

Expected: UI and theme tests pass without network access.

---

### Task 4: Dictation Settings and Deferred Runtime Integration

**Files:**
- Modify: `src/soundflow/preferences/tabs/dictation.py`
- Modify: `src/soundflow/preferences/page.py`
- Modify: `src/soundflow/ui/main_window.py`
- Modify: `tests/test_dictation_tab_ui.py`
- Modify: `tests/test_ui_runtime_contracts.py`

**Interfaces:**
- Produces `DictationTab.model_path_changed(str)`.
- Consumes `ModelManagerWidget.model_path_selected(str)`.
- Reuses `PreferencesPage.settings_saved` and `MainWindow._preferences_saved`.

- [ ] **Step 1: Write failing integration tests**

Add to `tests/test_dictation_tab_ui.py`:

```python
def test_dictation_tab_embeds_five_model_rows(self):
    with patch(
        "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
        return_value=[],
    ):
        tab = DictationTab(Settings())
    rows = [
        child for child in tab.findChildren(QWidget)
        if child.objectName().startswith("modelRow:")
    ]
    self.assertEqual(len(rows), 5)

def test_model_selection_updates_custom_path_field(self):
    with patch(
        "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
        return_value=[],
    ):
        tab = DictationTab(Settings())
    changes = []
    tab.model_path_changed.connect(changes.append)
    tab._model_manager.model_path_selected.emit("/tmp/faster-whisper-base")
    self.assertEqual(tab._model.text(), "/tmp/faster-whisper-base")
    self.assertEqual(changes, ["/tmp/faster-whisper-base"])
```

Add to `tests/test_ui_runtime_contracts.py`:

```python
def test_model_manager_selection_is_saved_immediately(self):
    with tempfile.TemporaryDirectory() as directory:
        store = SettingsStore(Path(directory) / "settings.json")
        settings = Settings()
        with patch(
            "soundflow.preferences.tabs.dictation.AudioCapture.list_input_devices",
            return_value=[],
        ):
            page = PreferencesPage(settings, store)
        page.dictation_tab.model_path_changed.emit("/tmp/faster-whisper-medium")
        self.assertEqual(store.load().model_path, "/tmp/faster-whisper-medium")

def test_model_switch_defers_rebuild_while_recording(self):
    with tempfile.TemporaryDirectory() as directory:
        store = SettingsStore(Path(directory) / "settings.json")
        window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
        self._windows.append(window)
        window.state.start()
        with patch.object(window, "_rebuild_runtime") as rebuild:
            window.preferences_page.dictation_tab.model_path_changed.emit(
                "/tmp/faster-whisper-base"
            )
            self.assertTrue(window._pending_runtime_rebuild)
            rebuild.assert_not_called()
            window.state.stop()
            window._pipeline_finished()
            rebuild.assert_called_once()
```

- [ ] **Step 2: Run them and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_dictation_tab_ui tests.test_ui_runtime_contracts -v
```

Expected: missing manager/signal/persistence behavior.

- [ ] **Step 3: Embed and persist the manager**

In `DictationTab`, declare `model_path_changed = Signal(str)`, create
`self._model_manager = ModelManagerWidget(settings)` immediately below the
Recognition heading, retain the path/Browse row, and connect selection to:

```python
def _model_selected(self, path: str) -> None:
    self._model.setText(path)
    self._settings.model_path = path
    self.model_path_changed.emit(path)
```

In `PreferencesPage`, keep `self.dictation_tab`, connect the signal, and add:

```python
def _persist_model_path(self, path: str) -> None:
    self._settings.model_path = path
    self._settings.normalized()
    self._store.save(self._settings)
    self.settings_saved.emit()
```

This immediately persists the path and invokes the existing runtime signature
logic, which rebuilds while idle and defers while recording/draining.

Add `ModelManagerWidget.shutdown()` to cancel and wait for an active worker,
delegate through `DictationTab.shutdown()` and `PreferencesPage.shutdown()`, and
call `self.preferences_page.shutdown()` at the start of `MainWindow.shutdown()`.
This prevents a running QThread from being destroyed during application exit.

- [ ] **Step 4: Verify GREEN and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_dictation_tab_ui tests.test_model_manager_ui \
  tests.test_ui_runtime_contracts tests.test_ui tests.test_motion_ui -v
git add src/soundflow/preferences/tabs/dictation.py \
  src/soundflow/preferences/page.py tests/test_dictation_tab_ui.py \
  tests/test_ui_runtime_contracts.py
git commit -m "Connect model manager to Soundflow runtime"
```

Expected: integration and existing runtime/UI tests pass.

---

### Task 5: Packaging, Documentation, Build, and Reinstall

**Files:**
- Modify: `packaging/soundflow.spec`
- Modify: `README.md`

**Interfaces:**
- Includes Hub download dependencies in the distributable.
- Documents in-app downloads and safe custom-directory behavior.

- [ ] **Step 1: Update packaging and README**

Add `huggingface_hub` and `tqdm` to the package collection loop in
`packaging/soundflow.spec`. Replace the README statement that Soundflow never
downloads models with:

```markdown
## Download a Whisper model

Open **Preferences -> Dictation -> Whisper models** and choose Download for
Tiny, Base, Small, Medium, or Large-v3 Turbo. Downloads run in the background,
are validated before use, and become active automatically. Installed inactive
models can be selected with Use or removed with Delete.

For an existing CTranslate2/faster-whisper directory, use **Model directory ->
Browse**. Soundflow never deletes custom model directories.
```

Keep `scripts/prepare_model.py` documented as the offline-installer workflow.

- [ ] **Step 2: Run focused feature verification**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_catalog tests.test_model_service tests.test_model_integrity \
  tests.test_model_manager_ui tests.test_dictation_tab_ui \
  tests.test_ui_runtime_contracts tests.test_design -v
```

Expected: every focused test passes.

- [ ] **Step 3: Run all non-audio modules independently**

```bash
set -e
for path in $(rg --files tests -g 'test_*.py' | sort); do
    module=${path%.py}
    module=${module//\//.}
    if [ "$module" = "tests.test_audio" ]; then
        continue
    fi
    PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
      python3 -m unittest "$module"
done
```

Expected: every invoked module passes. Report the two pre-existing audio mock
failures separately without changing audio behavior.

- [ ] **Step 4: Run static checks and build**

```bash
PYTHONPATH=.vendor/python:src python3 -m compileall -q src tests
git diff --check
PYTHONPATH=.vendor/python python3 -m PyInstaller --noconfirm packaging/soundflow.spec
```

Expected: compile and diff checks exit 0; PyInstaller reports `Build complete!`.

- [ ] **Step 5: Freshly reinstall and verify**

```bash
./uninstall-linux.sh
./install-linux.sh
systemctl --user is-enabled soundflow.service
systemctl --user is-active soundflow.service
sha256sum dist/Soundflow/Soundflow "$HOME/.local/share/soundflow/Soundflow"
```

Expected: service is `enabled` and `active`; both binary hashes match.

- [ ] **Step 6: Capture and inspect light/dark screenshots**

Render Preferences -> Dictation with a fake service and save:

```text
/tmp/soundflow-model-manager-light.png
/tmp/soundflow-model-manager-dark.png
```

Inspect row alignment, status readability, progress, clipping, compact height,
and true-black dark background. If a defect appears, add a failing geometry or
style assertion before correcting it, then rebuild and reinstall again.

- [ ] **Step 7: Commit delivery files and verify repository state**

```bash
git add packaging/soundflow.spec README.md
git commit -m "Package and document in-app model downloads"
git status --short --branch
git log --oneline -7
```

Expected: only the user's existing loose screenshots remain untracked; all
feature files are committed.
