# Geist Typography and Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Roboto with bundled Geist Sans/Mono typography and add restrained, interruptible toggle, button, model-progress, and status animations.

**Architecture:** Register pinned Geist v1.7.2 static TTF faces through the existing design-font boundary. Add a shared application-level button event filter, keep component-owned animations in `ToggleSwitch`, `ModelManagerWidget`, and `StatusBar`, and reuse Qt property animations with centralized duration tokens.

**Tech Stack:** Python 3.11+, PySide6/Qt Widgets, QPropertyAnimation, QGraphicsOpacityEffect, unittest, PyInstaller, official Geist v1.7.2 font assets.

## Global Constraints

- Use Geist for display and body text and Geist Mono only for technical values.
- Bundle font files and the upstream SIL Open Font License; require no system font installation.
- Use 120 ms button feedback, 160 ms toggle/progress interpolation, and 200 ms status/navigation fades.
- Use OutCubic easing for finite micro-interactions.
- Never delay commands, navigation, persistence, cancellation, or downloads.
- Rapid updates must continue from the currently visible state.
- Preserve native keyboard, focus, accessibility, and checked/clicked semantics.
- Keep the recording status pulse as the only looping opacity animation.
- Add no third-party animation dependency and no decorative motion.
- Rebuild and freshly reinstall after implementation.

---

### Task 1: Bundle and Register Geist Typography

**Files:**
- Add: `src/soundflow/assets/fonts/Geist-Regular.ttf`
- Add: `src/soundflow/assets/fonts/Geist-Medium.ttf`
- Add: `src/soundflow/assets/fonts/Geist-SemiBold.ttf`
- Add: `src/soundflow/assets/fonts/Geist-Bold.ttf`
- Add: `src/soundflow/assets/fonts/GeistMono-Regular.ttf`
- Add: `src/soundflow/assets/fonts/GeistMono-Medium.ttf`
- Add: `src/soundflow/assets/fonts/GEIST-OFL.txt`
- Delete: `src/soundflow/assets/fonts/Roboto-Regular.ttf`
- Delete: `src/soundflow/assets/fonts/Roboto-Medium.ttf`
- Delete: `src/soundflow/assets/fonts/Roboto-Bold.ttf`
- Delete: `src/soundflow/assets/fonts/ROBOTO-LICENSE.txt`
- Modify: `src/soundflow/design/fonts.py`
- Test: `tests/test_fonts.py`

**Interfaces:**
- Consumes: official `vercel/geist-font` tag `v1.7.2`, commit `a73329da8fc62afc917f796555202e4997f79b7c`.
- Produces: `DISPLAY_FONT = "Geist"`, `BODY_FONT = "Geist"`, and `MONO_FONT = "Geist Mono"`.
- Produces: `register_application_fonts() -> tuple[int, ...]` registering six static TTF faces.

- [ ] **Step 1: Write failing Geist registration and asset tests**

Replace the Roboto test with:

```python
def test_geist_is_the_bundled_application_font(self):
    font_ids = register_application_fonts()

    self.assertEqual(BODY_FONT, "Geist")
    self.assertEqual(DISPLAY_FONT, "Geist")
    self.assertEqual(MONO_FONT, "Geist Mono")
    self.assertEqual(len(font_ids), 6)
    self.assertIn("Geist", QFontDatabase.families())
    self.assertIn("Geist Mono", QFontDatabase.families())
```

Add an asset-boundary test:

```python
def test_only_geist_font_assets_are_bundled(self):
    font_dir = (
        Path(__file__).resolve().parents[1]
        / "src" / "soundflow" / "assets" / "fonts"
    )
    names = {path.name for path in font_dir.iterdir()}
    self.assertEqual(
        names,
        {
            "GEIST-OFL.txt",
            "Geist-Regular.ttf",
            "Geist-Medium.ttf",
            "Geist-SemiBold.ttf",
            "Geist-Bold.ttf",
            "GeistMono-Regular.ttf",
            "GeistMono-Medium.ttf",
        },
    )
    self.assertFalse(any("Roboto" in name for name in names))
```

- [ ] **Step 2: Run font tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_fonts -v
```

Expected: failures show Roboto constants/assets and missing Geist registrations.

- [ ] **Step 3: Import the pinned official assets**

Use the already inspected official tag, or fetch it if `/tmp/geist-font-v1.7.2` is absent:

```bash
git clone --depth 1 --branch v1.7.2 \
  https://github.com/vercel/geist-font.git /tmp/geist-font-v1.7.2
```

Copy these exact files:

```bash
cp /tmp/geist-font-v1.7.2/fonts/Geist/ttf/Geist-Regular.ttf \
  src/soundflow/assets/fonts/
cp /tmp/geist-font-v1.7.2/fonts/Geist/ttf/Geist-Medium.ttf \
  src/soundflow/assets/fonts/
cp /tmp/geist-font-v1.7.2/fonts/Geist/ttf/Geist-SemiBold.ttf \
  src/soundflow/assets/fonts/
cp /tmp/geist-font-v1.7.2/fonts/Geist/ttf/Geist-Bold.ttf \
  src/soundflow/assets/fonts/
cp /tmp/geist-font-v1.7.2/fonts/GeistMono/ttf/GeistMono-Regular.ttf \
  src/soundflow/assets/fonts/
cp /tmp/geist-font-v1.7.2/fonts/GeistMono/ttf/GeistMono-Medium.ttf \
  src/soundflow/assets/fonts/
cp /tmp/geist-font-v1.7.2/OFL.txt \
  src/soundflow/assets/fonts/GEIST-OFL.txt
```

Remove the four replaced Roboto assets only after the Geist files exist.

- [ ] **Step 4: Register the six Geist faces**

In `fonts.py`, update the registration loop:

```python
for filename in (
    "Geist-Regular.ttf",
    "Geist-Medium.ttf",
    "Geist-SemiBold.ttf",
    "Geist-Bold.ttf",
    "GeistMono-Regular.ttf",
    "GeistMono-Medium.ttf",
)
```

Set:

```python
DISPLAY_FONT = "Geist"
BODY_FONT = "Geist"
MONO_FONT = "Geist Mono"
```

Update docstrings from Roboto to Geist and retain the cached tuple behavior.

- [ ] **Step 5: Verify typography and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_fonts tests.test_design -v
rg -n "Roboto" src packaging tests
git diff --check
```

Expected: tests pass and the Roboto search returns no matches.

```bash
git add src/soundflow/assets/fonts src/soundflow/design/fonts.py \
  tests/test_fonts.py
git commit -m "Adopt Geist typography"
```

---

### Task 2: Animate Toggle Thumb Movement

**Files:**
- Modify: `src/soundflow/design/spacing.py`
- Modify: `src/soundflow/design/__init__.py`
- Modify: `src/soundflow/ui/widgets/toggle_switch.py`
- Test: `tests/test_toggle_switch.py`

**Interfaces:**
- Produces: `ANIMATION_CONTROL = 160`.
- Produces: Qt property `ToggleSwitch.thumbPosition: float` in the inclusive range `0.0..1.0`.
- Produces: `ToggleSwitch._thumb_animation: QPropertyAnimation`.

- [ ] **Step 1: Write failing toggle motion tests**

Import `QAbstractAnimation`, `QEasingCurve`, `QTest`, and `ANIMATION_CONTROL`. Add:

```python
def test_visible_switch_animates_thumb_to_checked_endpoint(self):
    switch = ToggleSwitch("Auto-save transcripts")
    switch.show()
    self.app.processEvents()

    switch.setChecked(True)

    self.assertEqual(switch._thumb_animation.duration(), ANIMATION_CONTROL)
    self.assertEqual(
        switch._thumb_animation.easingCurve().type(),
        QEasingCurve.Type.OutCubic,
    )
    self.assertEqual(
        switch._thumb_animation.state(),
        QAbstractAnimation.State.Running,
    )
    QTest.qWait(ANIMATION_CONTROL + 30)
    self.assertAlmostEqual(switch.thumbPosition, 1.0)
```

Add an interruption test that checks the thumb is between endpoints, toggles back, waits, and asserts `0.0`. Retain the mouse and Space-key native-state test.

- [ ] **Step 2: Run toggle tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_toggle_switch -v
```

Expected: missing animation token/property failures.

- [ ] **Step 3: Add the shared control duration**

Set `ANIMATION_CONTROL = 160` beside the existing duration constants and export it from `soundflow.design`.

- [ ] **Step 4: Implement the animated property**

Use:

```python
from PySide6.QtCore import (
    Property, QEasingCurve, QPropertyAnimation, QSize, Qt
)
```

Initialize:

```python
self._thumb_position = 1.0 if self.isChecked() else 0.0
self._thumb_animation = QPropertyAnimation(
    self, b"thumbPosition", self
)
self._thumb_animation.setDuration(ANIMATION_CONTROL)
self._thumb_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
self.toggled.connect(self._animate_thumb)
```

Expose a clamped property whose setter calls `update()`. `_animate_thumb` must stop the current animation, snap immediately when the widget is not visible, and otherwise animate from the current property value to `1.0` or `0.0`.

Paint the thumb with:

```python
x = 5 + round(18 * self._thumb_position)
```

Keep native state, hit area, focus, palette, and accessibility behavior unchanged.

- [ ] **Step 5: Verify and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_toggle_switch tests.test_general_tab_ui \
  tests.test_shortcuts_tab_ui tests.test_playback_tab_ui -v
git diff --check
git add src/soundflow/design/spacing.py src/soundflow/design/__init__.py \
  src/soundflow/ui/widgets/toggle_switch.py tests/test_toggle_switch.py
git commit -m "Animate preference toggles"
```

---

### Task 3: Add Shared Button Press Feedback

**Files:**
- Create: `src/soundflow/design/motion.py`
- Modify: `src/soundflow/design/__init__.py`
- Modify: `src/soundflow/app.py`
- Create: `tests/test_button_motion.py`

**Interfaces:**
- Produces: `ButtonMotionFilter(QObject)`.
- Produces: `install_button_motion(application: QApplication) -> ButtonMotionFilter`.
- Consumes: `ANIMATION_FAST = 120`.

- [ ] **Step 1: Write failing button motion tests**

Create Qt offscreen tests that install the filter on the test application. For an enabled `QPushButton`, send a mouse click and assert:

```python
self.assertEqual(button_clicks, [True])
animation = motion.animation_for(button)
self.assertIsNotNone(animation)
self.assertEqual(animation.duration(), ANIMATION_FAST)
self.assertEqual(
    animation.easingCurve().type(),
    QEasingCurve.Type.OutCubic,
)
```

Wait `ANIMATION_FAST + 30`, then assert the temporary graphics effect is removed. Add a disabled-button test asserting no click and no animation. Add rapid double-click coverage asserting the newest animation replaces the prior one without suppressing either click.

- [ ] **Step 2: Run tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_button_motion -v
```

Expected: import failure because the shared motion module does not exist.

- [ ] **Step 3: Implement the event-filter helper**

`ButtonMotionFilter.eventFilter` must return `False` for every event. On enabled `QPushButton` mouse release or Space/Return key release:

1. stop and detach the prior animation/effect for that button;
2. attach a new `QGraphicsOpacityEffect` at opacity `0.72`;
3. animate opacity to `1.0` over `ANIMATION_FAST` with OutCubic;
4. remove the effect and per-button references on finish.

Use dictionaries keyed by button for active animations/effects and connect `destroyed` to cleanup. Expose `animation_for(button)` only as a read-only testable query.

`install_button_motion` parents one filter to the application, installs it once, and returns the existing instance on repeated calls.

- [ ] **Step 4: Install motion at application startup**

After font registration in `app.main`, call:

```python
from soundflow.design import install_button_motion
install_button_motion(application)
```

No page or button business logic changes.

- [ ] **Step 5: Verify and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_button_motion tests.test_ui_runtime_contracts \
  tests.test_modular_ui -v
git diff --check
git add src/soundflow/design/motion.py src/soundflow/design/__init__.py \
  src/soundflow/app.py tests/test_button_motion.py
git commit -m "Add subtle button motion feedback"
```

---

### Task 4: Smooth Model Download Progress

**Files:**
- Modify: `src/soundflow/preferences/model_manager.py`
- Modify: `tests/test_model_manager_ui.py`

**Interfaces:**
- Consumes: `ANIMATION_CONTROL = 160`.
- Produces: one `QPropertyAnimation` per `_ModelRow`, targeting its progress bar `value`.
- Preserves: immediate `downloaded MB / total MB` text.

- [ ] **Step 1: Write failing determinate and interruption tests**

After showing `225.0 MB / 500.0 MB`, assert:

```python
animation = widget._rows["tiny"].progress_animation
self.assertEqual(animation.duration(), ANIMATION_CONTROL)
self.assertEqual(
    animation.state(), QAbstractAnimation.State.Running
)
self.assertEqual(progress.format(), "225.0 MB / 500.0 MB")
```

Wait for completion and assert `progress.value() == 45`. Add a rapid `45 -> 80` update and assert the animation ends at 80. For unknown totals, Verifying, error, cancellation, and success, assert the animation is stopped before range/hide changes.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_manager_ui.ModelManagerUiTests.test_progress_and_errors_are_inline \
  -v
```

Expected: `_ModelRow` has no progress animation and values jump immediately.

- [ ] **Step 3: Add row-owned progress animations**

Add `progress_animation: QPropertyAnimation` to `_ModelRow`. Create it with the progress bar as target and parent:

```python
animation = QPropertyAnimation(progress, b"value", progress)
animation.setDuration(ANIMATION_CONTROL)
animation.setEasingCurve(QEasingCurve.Type.OutCubic)
```

For determinate Downloading updates, stop the current animation, set its start value to the visible bar value and end value to the newest clamped fill, update the MB format immediately, then start. For non-download phases and unknown totals, stop the animation before changing range/value/format. Stop it before success, cancellation, or error hides the bar.

- [ ] **Step 4: Verify and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_model_manager_ui tests.test_model_service \
  tests.test_design -v
git diff --check
git add src/soundflow/preferences/model_manager.py \
  tests/test_model_manager_ui.py
git commit -m "Smooth model download progress"
```

---

### Task 5: Fade New Persistent Status Messages

**Files:**
- Modify: `src/soundflow/ui/widgets/status_bar.py`
- Modify: `tests/test_motion_ui.py`

**Interfaces:**
- Consumes: `ANIMATION_NORMAL = 200`.
- Produces: `StatusBar._label_effect: QGraphicsOpacityEffect`.
- Produces: `StatusBar._label_animation: QPropertyAnimation`.

- [ ] **Step 1: Write failing status fade tests**

After changing status text, assert:

```python
self.assertEqual(status._label_animation.duration(), ANIMATION_NORMAL)
self.assertEqual(
    status._label_animation.easingCurve().type(),
    QEasingCurve.Type.OutCubic,
)
self.assertEqual(
    status._label_animation.state(),
    QAbstractAnimation.State.Running,
)
```

Change the message again before completion, wait, and assert the second text remains and opacity ends at `1.0`. Calling `set_status` with unchanged text must not restart the label fade. Existing recording pulse assertions must remain unchanged.

- [ ] **Step 2: Run motion tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_motion_ui -v
```

Expected: the label fade effect and animation do not exist.

- [ ] **Step 3: Implement status-label fade**

Attach a dedicated opacity effect to `_status_label` and configure a finite OutCubic animation. In `set_status`, only when the text changes:

```python
running = (
    self._label_animation.state()
    == QPropertyAnimation.State.Running
)
start = self._label_effect.opacity() if running else 0.55
self._label_animation.stop()
self._status_label.setText(label)
self._label_animation.setStartValue(start)
self._label_animation.setEndValue(1.0)
self._label_animation.start()
```

Keep the status-dot pulse on its separate effect. Repeated state-only changes update the dot without restarting the text fade.

- [ ] **Step 4: Verify and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_motion_ui tests.test_ui_runtime_contracts -v
git diff --check
git add src/soundflow/ui/widgets/status_bar.py tests/test_motion_ui.py
git commit -m "Fade persistent status updates"
```

---

### Task 6: Regression, Packaging, Installation, and Visual Review

**Files:**
- Verify: `src/soundflow/assets/fonts/`
- Verify: `src/soundflow/design/`
- Verify: `src/soundflow/ui/widgets/`
- Verify: `src/soundflow/preferences/model_manager.py`
- Verify: `tests/`

**Interfaces:**
- Produces: a tested and freshly installed Soundflow application with Geist typography and restrained motion.

- [ ] **Step 1: Run focused typography and motion coverage**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_fonts tests.test_toggle_switch tests.test_button_motion \
  tests.test_motion_ui tests.test_model_manager_ui tests.test_design -v
```

Expected: all invoked tests pass.

- [ ] **Step 2: Run every non-audio module independently**

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

- [ ] **Step 3: Compile, inspect assets, and validate the diff**

```bash
PYTHONPATH=.vendor/python:src python3 -m compileall -q src tests
rg -n "Roboto" src packaging tests
find src/soundflow/assets/fonts -maxdepth 1 -type f -printf '%f\n' | sort
git diff --check
```

Expected: no Roboto matches, exactly seven Geist font/license assets, and no whitespace errors.

- [ ] **Step 4: Build and freshly reinstall**

```bash
PYTHONPATH=.vendor/python python3 -m PyInstaller \
  --noconfirm packaging/soundflow.spec
./uninstall-linux.sh
./install-linux.sh
systemctl --user is-enabled soundflow.service
systemctl --user is-active soundflow.service
sha256sum dist/Soundflow/Soundflow \
  "$HOME/.local/share/soundflow/Soundflow"
```

Expected: build succeeds, the service is `enabled` and `active`, and executable hashes match.

- [ ] **Step 5: Capture and inspect both themes**

Capture light- and dark-theme screenshots of Preferences, History, Dictation, and the model-download row. Confirm Geist hierarchy, readable mono technical values, compact layout, and no clipping.

Exercise navigation, toggle, button, status, and download-progress interactions. Confirm motion is subtle, ends at the correct state, and remains smooth during rapid repeated input.

- [ ] **Step 6: Preserve user files and report the final state**

```bash
git status --short
git log -8 --oneline
```

Expected: only the user's existing `5db20f0e-b172-4f45-a323-c99fbc5d68df.png` and `screenshots/` remain untracked.
