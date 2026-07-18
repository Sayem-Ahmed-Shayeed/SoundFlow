# Model Download Percentage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display the live integer download percentage inside each active Whisper model progress bar.

**Architecture:** Reuse `QProgressBar`'s native `%p%` text rendering so the displayed value stays synchronized with the existing clamped progress value. Expand only the bar within the already-present progress row and add compact high-contrast shared theme rules.

**Tech Stack:** Python 3.11+, PySide6, Qt stylesheets, unittest, PyInstaller.

## Global Constraints

- Keep the existing phase label beside the bar.
- Display only clamped integer values from `0%` through `100%`.
- Hide progress UI after completion, cancellation, or error as before.
- Preserve compact light and true-black dark themes.
- Rebuild and freshly reinstall Soundflow after the code change.

---

### Task 1: Native Percentage Text and Delivery

**Files:**
- Modify: `src/soundflow/preferences/model_manager.py:333-340`
- Modify: `src/soundflow/design/theme.py:420-429`
- Modify: `tests/test_model_manager_ui.py:106-126`
- Modify: `tests/test_design.py:55-73`

**Interfaces:**
- Consumes: `ModelManagerWidget._show_progress(model_id: str, phase: str, percent: int)`.
- Produces: a visible `QProgressBar` native label formatted as `%p%`.

- [ ] **Step 1: Write failing UI and style assertions**

Extend `test_progress_and_errors_are_inline` with:

```python
self.assertTrue(progress.isTextVisible())
self.assertEqual(progress.format(), "%p%")
self.assertEqual(progress.text(), "42%")
widget._show_progress("tiny", "Downloading", 150)
self.assertEqual(progress.text(), "100%")
widget._show_progress("tiny", "Downloading", -5)
self.assertEqual(progress.text(), "0%")
```

In the model-manager stylesheet test, extract the
`QProgressBar[objectName^="modelProgress:"]` rule and assert:

```python
self.assertIn("min-height: 16px;", block)
self.assertIn("max-height: 16px;", block)
self.assertIn("color: #FFFFFF;", block)
self.assertIn("text-align: center;", block)
```

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_manager_ui.ModelManagerUiTests.test_progress_and_errors_are_inline \
  tests.test_design.DesignTokenTests.test_model_manager_rules_cover_rows_progress_focus_and_delete -v
```

Expected: failure because percentage text is hidden and the bar is still 4 px high with transparent text.

- [ ] **Step 3: Enable native percentage rendering**

In `_create_row`, configure the existing progress bar:

```python
progress.setRange(0, 100)
progress.setFormat("%p%")
progress.setTextVisible(True)
```

Keep `_show_progress`'s existing integer conversion and `0–100` clamp unchanged.

Update the model-progress stylesheet rule to:

```css
QProgressBar[objectName^="modelProgress:"] {
    background: {muted};
    border: 0;
    border-radius: 4px;
    min-height: 16px;
    max-height: 16px;
    color: #FFFFFF;
    text-align: center;
    font-size: 10px;
    font-weight: 600;
}
```

Keep the existing accent-colored chunk rule.

- [ ] **Step 4: Verify focused and non-audio tests**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_manager_ui tests.test_design tests.test_dictation_tab_ui -v
```

Expected: all invoked tests pass.

Run every non-audio module independently:

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

- [ ] **Step 5: Build, reinstall, and verify**

```bash
PYTHONPATH=.vendor/python:src python3 -m compileall -q src tests
git diff --check
PYTHONPATH=.vendor/python python3 -m PyInstaller --noconfirm packaging/soundflow.spec
./uninstall-linux.sh
./install-linux.sh
systemctl --user is-enabled soundflow.service
systemctl --user is-active soundflow.service
sha256sum dist/Soundflow/Soundflow "$HOME/.local/share/soundflow/Soundflow"
```

Expected: build and reinstall succeed, service is `enabled` and `active`, and executable hashes match.

- [ ] **Step 6: Commit**

```bash
git add src/soundflow/preferences/model_manager.py src/soundflow/design/theme.py \
  tests/test_model_manager_ui.py tests/test_design.py
git commit -m "Show model download percentage"
```
