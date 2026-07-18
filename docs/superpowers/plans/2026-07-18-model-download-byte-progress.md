# Model Download Byte Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the misleading model-download percentage label with a live aggregate `downloaded MB / total MB` tracker.

**Architecture:** Ask `snapshot_download(..., dry_run=True)` for exact required sizes and cache state, then use Hugging Face Hub's aggregate byte-oriented tqdm bar to report live completed bytes against that fixed total. Extend the worker signal with byte counts while retaining compatibility with two-argument progress calls from injected services, and render decimal megabytes inside the existing progress bar.

**Tech Stack:** Python 3.11+, huggingface_hub, tqdm, PySide6, Qt progress bars, unittest, PyInstaller.

## Global Constraints

- Display decimal megabytes using `1 MB = 1,000,000 bytes` and one decimal place.
- Count cached files as already downloaded.
- Aggregate all required files into one model-level counter.
- Never display a percentage to the user.
- Fall back to an indeterminate download bar when exact metadata is unavailable.
- Preserve Preparing, Verifying, Ready, Cancelled, and error behavior.
- Do not add speed, time-remaining, pause, or resume UI.
- Rebuild, freshly reinstall, verify the service, and visually inspect both themes.

---

### Task 1: Exact Aggregate Byte Accounting

**Files:**
- Modify: `src/soundflow/models/service.py:19-127`
- Test: `tests/test_model_service.py`

**Interfaces:**
- Consumes: `snapshot_download(repo_id, local_dir, allow_patterns, max_workers, dry_run, tqdm_class)`.
- Produces: `ProgressCallback(phase: str, fill: int, downloaded_bytes: int, total_bytes: int)`.
- Produces: `_download_snapshot(spec, target, progress, cancel_event)`, which emits exact aggregate byte events when metadata is available and zero byte fields when it is not.

- [ ] **Step 1: Write failing tests for cached and live bytes**

Add a helper that patches `huggingface_hub.snapshot_download`. Its dry-run call returns:

```python
[
    SimpleNamespace(file_size=100_000_000, is_cached=True, will_download=False),
    SimpleNamespace(file_size=400_000_000, is_cached=False, will_download=True),
]
```

For the real call, construct the supplied `tqdm_class` with `total=0`, `unit="B"`, and `disable=True`; set its dynamic total to `400_000_000`; then call `update(125_000_000)` and `update(275_000_000)`. Assert that download events include:

```python
("Downloading", 45, 225_000_000, 500_000_000)
("Downloading", 100, 500_000_000, 500_000_000)
```

Also assert that the dry run and real call use identical repository, local directory, and allow-pattern values.

- [ ] **Step 2: Write failing edge-case tests**

Add focused tests proving:

```python
# A malformed over-report is clamped.
assert events[-1][2:] == (500_000_000, 500_000_000)

# A dry-run exception still permits the real transfer.
assert ("Downloading", 0, 0, 0) in events

# Cancellation before or during either call raises ModelDownloadCancelled.
with self.assertRaises(ModelDownloadCancelled):
    model_service._download_snapshot(
        spec, target, lambda *args: events.append(args), cancel
    )
```

The unknown-metadata fake must raise only on its `dry_run=True` call and complete normally on its real call.

- [ ] **Step 3: Run the service tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src python3 -m unittest tests.test_model_service -v
```

Expected: the new assertions fail because the current tqdm adapter calculates a per-growing-total percentage and emits no byte counts.

- [ ] **Step 4: Implement fixed-total byte accounting**

Change the progress callback type to four fields:

```python
ProgressCallback = Callable[[str, int, int, int], None]
```

In `_download_snapshot`, run a guarded dry run before the real call:

```python
download_args = {
    "repo_id": spec.repo_id,
    "local_dir": target,
    "allow_patterns": list(ALLOW_PATTERNS),
    "max_workers": 1,
}
try:
    files = snapshot_download(**download_args, dry_run=True)
except ModelDownloadCancelled:
    raise
except Exception:
    files = []

total_bytes = sum(max(0, int(item.file_size)) for item in files)
cached_bytes = sum(
    max(0, int(item.file_size))
    for item in files
    if item.is_cached or not item.will_download
)
```

After cancellation checks, make `ReportingTqdm` process only the aggregate byte bar:

```python
class ReportingTqdm(tqdm):
    def update(self, amount=1):
        result = super().update(amount)
        _raise_if_cancelled(cancel_event)
        if total_bytes > 0 and getattr(self, "unit", None) == "B":
            completed = min(total_bytes, max(0, cached_bytes + int(self.n)))
            fill = min(100, int(completed * 100 / total_bytes))
            progress("Downloading", fill, completed, total_bytes)
        elif getattr(self, "unit", None) == "B":
            progress("Downloading", 0, 0, 0)
        return result
```

Emit the cached starting state before the real call when the total is known, emit the unknown state otherwise, and call:

```python
snapshot_download(**download_args, tqdm_class=ReportingTqdm)
```

Use `_raise_if_cancelled` before dry-run discovery, after discovery, during updates, and after the real call. Keep the existing partial-directory cleanup behavior.

- [ ] **Step 5: Normalize service lifecycle events**

Update `ModelService.install` lifecycle events to four fields:

```python
progress("Preparing", 0, 0, 0)
progress("Verifying", 100, 0, 0)
progress("Ready", 100, 0, 0)
```

Update direct service-test callbacks and injected downloaders to accept `*args` where their test does not inspect byte values. Keep explicit four-field assertions where byte behavior is under test.

- [ ] **Step 6: Run service tests and commit**

```bash
PYTHONPATH=.vendor/python:src python3 -m unittest tests.test_model_service -v
git add src/soundflow/models/service.py tests/test_model_service.py
git commit -m "Track aggregate model download bytes"
```

Expected: all service tests pass and the commit contains only the service and its tests.

---

### Task 2: Worker Transport and MB Progress UI

**Files:**
- Modify: `src/soundflow/preferences/model_manager.py:166-205`
- Modify: `src/soundflow/preferences/model_manager.py:330-488`
- Test: `tests/test_model_manager_ui.py:108-133`
- Test: `tests/test_model_manager_ui.py:685-720`

**Interfaces:**
- Consumes: four-field service progress calls and legacy two-field injected-service calls.
- Produces: `ModelDownloadThread.phase_changed = Signal(str, int, int, int)`.
- Produces: `ModelManagerWidget._show_progress(model_id, phase, fill, downloaded_bytes=0, total_bytes=0)`.
- Produces: `_format_megabytes(value: int) -> str`.

- [ ] **Step 1: Write failing worker transport tests**

Change the existing worker expectation so a legacy fake remains supported:

```python
progress("Downloading", 37)
self.assertEqual(result["phase"], [("Downloading", 37, 0, 0)])
```

Add a second fake service that calls:

```python
progress("Downloading", 45, 225_000_000, 500_000_000)
```

Assert that the worker emits the same four-field event.

- [ ] **Step 2: Write failing UI formatting tests**

Replace percentage assertions in `test_progress_and_errors_are_inline` with:

```python
widget._show_progress(
    "tiny", "Downloading", 45, 225_000_000, 500_000_000
)
self.assertEqual(progress.value(), 45)
self.assertEqual(progress.format(), "225.0 MB / 500.0 MB")
self.assertNotIn("%", progress.text())
```

Also assert:

```python
widget._show_progress("tiny", "Downloading", 0, 0, 0)
self.assertEqual((progress.minimum(), progress.maximum()), (0, 0))
self.assertEqual(progress.format(), "")

widget._show_progress("tiny", "Verifying", 100, 0, 0)
self.assertEqual((progress.minimum(), progress.maximum()), (0, 100))
self.assertEqual(progress.format(), "")
```

- [ ] **Step 3: Run focused tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_manager_ui.ModelManagerUiTests.test_progress_and_errors_are_inline \
  tests.test_model_manager_ui.ModelDownloadThreadTests -v
```

Expected: failures show that the signal has two fields and the bar still renders `%p%`.

- [ ] **Step 4: Implement backward-compatible worker transport**

Change the signal and wrap the callback passed to the service:

```python
phase_changed = Signal(str, int, int, int)

def report_progress(
    phase: str,
    fill: int,
    downloaded_bytes: int = 0,
    total_bytes: int = 0,
) -> None:
    self.phase_changed.emit(
        phase,
        int(fill),
        max(0, int(downloaded_bytes)),
        max(0, int(total_bytes)),
    )

path = self._service.install(
    self._model_id,
    progress=report_progress,
    cancel_event=self._cancel_event,
)
```

This wrapper is the compatibility boundary for two-argument injected services.

- [ ] **Step 5: Render decimal MB without percentages**

Initialize the progress bar with an empty format:

```python
progress.setRange(0, 100)
progress.setFormat("")
progress.setTextVisible(True)
```

Extend the worker slot and `_show_progress` signature with byte fields. For a valid downloading total:

```python
row.progress.setRange(0, 100)
row.progress.setValue(max(0, min(100, int(fill))))
completed = min(total_bytes, max(0, downloaded_bytes))
row.progress.setFormat(
    f"{completed / 1_000_000:.1f} MB / "
    f"{total_bytes / 1_000_000:.1f} MB"
)
```

For `phase == "Downloading"` with an unknown total, use `setRange(0, 0)` and `setFormat("")`. For all other phases, restore `setRange(0, 100)`, set the clamped fill, and keep the format empty. Preserve the existing adjacent phase label and inline error behavior.

- [ ] **Step 6: Run focused UI tests and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_manager_ui tests.test_design -v
git add src/soundflow/preferences/model_manager.py tests/test_model_manager_ui.py
git commit -m "Show live model download megabytes"
```

Expected: all focused UI tests pass and no progress text contains `%`.

---

### Task 3: Regression, Package, Install, and Visual Verification

**Files:**
- Verify: `src/soundflow/models/service.py`
- Verify: `src/soundflow/preferences/model_manager.py`
- Verify: `tests/test_model_service.py`
- Verify: `tests/test_model_manager_ui.py`

**Interfaces:**
- Consumes: the completed service and UI changes from Tasks 1 and 2.
- Produces: a tested, packaged, freshly installed Soundflow application.

- [ ] **Step 1: Run focused regression tests**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_service tests.test_model_manager_ui tests.test_design -v
```

Expected: all invoked tests pass.

- [ ] **Step 2: Run every non-audio test module independently**

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

Expected: every invoked module passes.

- [ ] **Step 3: Compile and validate the diff**

```bash
PYTHONPATH=.vendor/python:src python3 -m compileall -q src tests
git diff --check
```

Expected: both commands exit successfully.

- [ ] **Step 4: Build and freshly reinstall**

```bash
PYTHONPATH=.vendor/python python3 -m PyInstaller --noconfirm packaging/soundflow.spec
./uninstall-linux.sh
./install-linux.sh
systemctl --user is-enabled soundflow.service
systemctl --user is-active soundflow.service
sha256sum dist/Soundflow/Soundflow "$HOME/.local/share/soundflow/Soundflow"
```

Expected: PyInstaller reports a successful build, installation succeeds, the service is `enabled` and `active`, and both executable hashes match.

- [ ] **Step 5: Capture and inspect both themes**

Launch the installed application, open Settings, start a model download or drive the widget with a deterministic byte-progress fixture, and capture light- and dark-theme screenshots. Verify:

- the counter reads in the form `225.0 MB / 500.0 MB`;
- the value changes as byte events arrive;
- no percentage appears;
- the counter remains legible in both themes; and
- the row keeps its compact height.

- [ ] **Step 6: Final verification commit**

If verification required no source changes, record no empty commit. If a correction was needed, rerun the affected tests and commit only the correction:

```bash
git add src/soundflow/models/service.py \
  src/soundflow/preferences/model_manager.py \
  tests/test_model_service.py tests/test_model_manager_ui.py
git commit -m "Polish model byte download progress"
```

Confirm that the user's existing untracked screenshots remain untouched:

```bash
git status --short
```
