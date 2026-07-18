# Geist Typography and Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Roboto with bundled Geist Sans/Mono typography and add short, interruptible toggle, button, model-progress, and status micro-interactions.

**Architecture:** Keep typography centralized in `soundflow.design.fonts`, pin official Geist v1.7.2 assets and license, and retain the existing stylesheet token hierarchy. Build motion with native PySide6 animation primitives: widgets own animations for properties they paint, while one application-level event filter provides shared button feedback.

**Tech Stack:** Python 3.11+, PySide6, Qt property animation and graphics effects, unittest, PyInstaller, Geist v1.7.2.

## Global Constraints

- Use official Geist v1.7.2 from `https://github.com/vercel/geist-font/releases/download/v1.7.2/geist-font-v1.7.2.zip`.
- Verify the release archive SHA-256 is `7fc800d2ac6b92844895196e5041aca55d814c15db70c44f79b3b83ab82b04e2`.
- Bundle the upstream SIL Open Font License.
- Use Geist Sans for display/body and Geist Mono only for technical values.
- Preserve existing font-size tokens and compact UI density.
- Use 120 ms button feedback, 160 ms toggle/progress interpolation, and 200 ms navigation/status fades.
- Use `QEasingCurve.Type.OutCubic` for finite micro-interactions.
- Never delay business actions or alter native keyboard/accessibility semantics.
- Keep the recording status pulse as the only looping opacity animation.
- Do not add third-party animation dependencies or decorative movement.
- Rebuild, freshly reinstall, verify the user service, compare executable hashes, and inspect both themes.

---

### Task 1: Bundle and Register Geist Typography

**Files:**
- Replace: `src/soundflow/assets/fonts/Roboto-Regular.ttf`
- Replace: `src/soundflow/assets/fonts/Roboto-Medium.ttf`
- Replace: `src/soundflow/assets/fonts/Roboto-Bold.ttf`
- Replace: `src/soundflow/assets/fonts/ROBOTO-LICENSE.txt`
- Create: `src/soundflow/assets/fonts/Geist-Regular.ttf`
- Create: `src/soundflow/assets/fonts/Geist-Medium.ttf`
- Create: `src/soundflow/assets/fonts/Geist-SemiBold.ttf`
- Create: `src/soundflow/assets/fonts/Geist-Bold.ttf`
- Create: `src/soundflow/assets/fonts/GeistMono-Regular.ttf`
- Create: `src/soundflow/assets/fonts/GeistMono-Medium.ttf`
- Create: `src/soundflow/assets/fonts/GeistMono-SemiBold.ttf`
- Create: `src/soundflow/assets/fonts/GEIST-OFL.txt`
- Modify: `src/soundflow/design/fonts.py`
- Modify: `tests/test_fonts.py`

**Interfaces:**
- Produces: `DISPLAY_FONT = "Geist"`.
- Produces: `BODY_FONT = "Geist"`.
- Produces: `MONO_FONT = "Geist Mono"`.
- Preserves: `register_application_fonts() -> tuple[int, ...]`.

- [ ] **Step 1: Write failing typography and asset tests**

Replace the Roboto test with assertions:

```python
def test_geist_is_the_shared_bundled_application_font(self):
    font_ids = register_application_fonts()

    self.assertEqual(BODY_FONT, "Geist")
    self.assertEqual(DISPLAY_FONT, "Geist")
    self.assertEqual(MONO_FONT, "Geist Mono")
    self.assertGreaterEqual(len(font_ids), 7)
    self.assertIn("Geist", QFontDatabase.families())
    self.assertIn("Geist Mono", QFontDatabase.families())
```

Add an asset-contract test:

```python
def test_only_geist_font_assets_and_license_are_bundled(self):
    font_dir = Path(fonts.__file__).resolve().parents[1] / "assets" / "fonts"
    names = {item.name for item in font_dir.iterdir()}
    self.assertEqual(
        names,
        {
            "Geist-Regular.ttf",
            "Geist-Medium.ttf",
            "Geist-SemiBold.ttf",
            "Geist-Bold.ttf",
            "GeistMono-Regular.ttf",
            "GeistMono-Medium.ttf",
            "GeistMono-SemiBold.ttf",
            "GEIST-OFL.txt",
        },
    )
    self.assertIn("SIL OPEN FONT LICENSE", (
        font_dir / "GEIST-OFL.txt"
    ).read_text(encoding="utf-8").upper())
```

- [ ] **Step 2: Run the font tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_fonts -v
```

Expected: failures report the current Roboto constants and asset names.

- [ ] **Step 3: Fetch and verify the official release**

```bash
curl -fsSL \
  https://github.com/vercel/geist-font/releases/download/v1.7.2/geist-font-v1.7.2.zip \
  -o /tmp/geist-font-v1.7.2.zip
printf '%s  %s\n' \
  7fc800d2ac6b92844895196e5041aca55d814c15db70c44f79b3b83ab82b04e2 \
  /tmp/geist-font-v1.7.2.zip | sha256sum --check
rm -rf /tmp/soundflow-geist-font
mkdir -p /tmp/soundflow-geist-font
unzip -q /tmp/geist-font-v1.7.2.zip -d /tmp/soundflow-geist-font
```

Expected: checksum verification prints `OK`.

- [ ] **Step 4: Replace the bundled font assets**

Copy these exact upstream files into `src/soundflow/assets/fonts/`:

```text
geist-font/Geist/ttf/Geist-Regular.ttf
geist-font/Geist/ttf/Geist-Medium.ttf
geist-font/Geist/ttf/Geist-SemiBold.ttf
geist-font/Geist/ttf/Geist-Bold.ttf
geist-font/GeistMono/ttf/GeistMono-Regular.ttf
geist-font/GeistMono/ttf/GeistMono-Medium.ttf
geist-font/GeistMono/ttf/GeistMono-SemiBold.ttf
geist-font/OFL.txt
```

Remove the three tracked Roboto TTF files and `ROBOTO-LICENSE.txt`. Rename the copied license to `GEIST-OFL.txt`. Do not copy italic, pixel, webfont, or variable-font files.

- [ ] **Step 5: Register the Geist families**

Update `register_application_fonts` to iterate over:

```python
(
    "Geist-Regular.ttf",
    "Geist-Medium.ttf",
    "Geist-SemiBold.ttf",
    "Geist-Bold.ttf",
    "GeistMono-Regular.ttf",
    "GeistMono-Medium.ttf",
    "GeistMono-SemiBold.ttf",
)
```

Set:

```python
DISPLAY_FONT = "Geist"
BODY_FONT = "Geist"
MONO_FONT = "Geist Mono"
```

Update its docstring to describe bundled Geist families. Keep the application-instance guards and font ID caching unchanged.

- [ ] **Step 6: Run typography tests and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_fonts tests.test_design -v
git add src/soundflow/assets/fonts src/soundflow/design/fonts.py \
  tests/test_fonts.py
git commit -m "Adopt Geist typography"
```

Expected: all invoked tests pass; the commit contains the seven Geist faces, Geist license, registration changes, tests, and Roboto deletions.

---

### Task 2: Animate Toggle Thumb Motion

**Files:**
- Modify: `src/soundflow/design/spacing.py`
- Modify: `src/soundflow/design/__init__.py`
- Modify: `src/soundflow/ui/widgets/toggle_switch.py`
- Modify: `tests/test_toggle_switch.py`

**Interfaces:**
- Produces: `ANIMATION_CONTROL = 160`.
- Produces: `ToggleSwitch.thumb_position: float`, a Qt property from `0.0` to `1.0`.
- Preserves: native `QCheckBox` checked state, signals, focus, mouse, keyboard, and accessibility behavior.

- [ ] **Step 1: Write failing toggle animation tests**

Import `QAbstractAnimation`, `QEasingCurve`, `QTest`, and `ANIMATION_CONTROL`. Add:

```python
def test_visible_switch_animates_thumb_to_checked_endpoint(self):
    switch = ToggleSwitch("Auto-save transcripts")
    switch.show()
    self.app.processEvents()

    switch.setChecked(True)

    self.assertEqual(
        switch._thumb_animation.state(),
        QAbstractAnimation.State.Running,
    )
    self.assertEqual(switch._thumb_animation.duration(), ANIMATION_CONTROL)
    self.assertEqual(
        switch._thumb_animation.easingCurve().type(),
        QEasingCurve.Type.OutCubic,
    )
    QTest.qWait(ANIMATION_CONTROL + 30)
    self.assertAlmostEqual(switch.thumb_position, 1.0)
```

Add an interruption test that checks the thumb is between endpoints halfway through the first animation, toggles back, waits, and asserts `thumb_position == 0.0`.

- [ ] **Step 2: Run toggle tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_toggle_switch -v
```

Expected: failures report missing `ANIMATION_CONTROL`, property, and animation.

- [ ] **Step 3: Add the shared control duration**

In `spacing.py`:

```python
ANIMATION_FAST = 120
ANIMATION_CONTROL = 160
ANIMATION_NORMAL = 200
ANIMATION_SLOW = 320
```

Export `ANIMATION_CONTROL` through `soundflow.design.__init__`.

- [ ] **Step 4: Implement interruptible thumb interpolation**

Import `Property`, `QEasingCurve`, and `QPropertyAnimation`. Initialize:

```python
self._thumb_position = 1.0 if self.isChecked() else 0.0
self._thumb_animation = QPropertyAnimation(
    self, b"thumb_position", self
)
self._thumb_animation.setDuration(ANIMATION_CONTROL)
self._thumb_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
self.toggled.connect(self._animate_thumb)
```

Provide clamped getter/setter methods, call `update()` in the setter, and expose:

```python
thumb_position = Property(
    float,
    _get_thumb_position,
    _set_thumb_position,
)
```

When hidden, set the endpoint immediately. When visible, stop the current animation, start from the current property value, and animate to `1.0` or `0.0`. In `paintEvent`, calculate:

```python
x = 5 + round(18 * self._thumb_position)
```

- [ ] **Step 5: Run toggle and dependent preference tests**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_toggle_switch tests.test_general_tab_ui \
  tests.test_shortcuts_tab_ui tests.test_playback_tab_ui -v
git add src/soundflow/design/spacing.py src/soundflow/design/__init__.py \
  src/soundflow/ui/widgets/toggle_switch.py tests/test_toggle_switch.py
git commit -m "Animate preference toggles"
```

Expected: all invoked tests pass and rapid toggles end at the latest checked state.

---

### Task 3: Shared Button and Status Feedback

**Files:**
- Create: `src/soundflow/design/motion.py`
- Modify: `src/soundflow/design/__init__.py`
- Modify: `src/soundflow/app.py`
- Modify: `src/soundflow/ui/widgets/status_bar.py`
- Create: `tests/test_button_motion.py`
- Modify: `tests/test_motion_ui.py`

**Interfaces:**
- Produces: `install_motion_feedback(application: QApplication) -> ButtonPressAnimator`.
- Produces: one application-owned `ButtonPressAnimator` event filter.
- Produces: `StatusBar._label_animation`, a 200 ms non-looping fade.

- [ ] **Step 1: Write failing button feedback tests**

Create `tests/test_button_motion.py` with an offscreen application. Install motion feedback, create a visible enabled `QPushButton`, connect `clicked`, and use `QTest.mouseClick`. Assert:

```python
self.assertEqual(clicks, [True])
self.assertEqual(animator.animation_for(button).duration(), ANIMATION_FAST)
self.assertEqual(
    animator.animation_for(button).easingCurve().type(),
    QEasingCurve.Type.OutCubic,
)
```

Wait `ANIMATION_FAST + 30`, then assert `button.graphicsEffect() is None`. Add a disabled-button test asserting no animation is registered.

- [ ] **Step 2: Write failing status fade tests**

Extend `tests/test_motion_ui.py`:

```python
status = StatusBar()
status.show()
status.set_status("Downloading model", "connecting")
self.assertEqual(status._label_animation.duration(), ANIMATION_NORMAL)
self.assertEqual(status._label_animation.loopCount(), 1)
self.assertEqual(
    status._label_animation.state(),
    QAbstractAnimation.State.Running,
)
QTest.qWait(ANIMATION_NORMAL + 30)
self.assertEqual(status._label_effect.opacity(), 1.0)
```

Add an interrupted update that changes the message twice and verifies the second text and final opacity.

- [ ] **Step 3: Run motion tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_button_motion tests.test_motion_ui -v
```

Expected: import or attribute failures identify the missing shared controller and label fade.

- [ ] **Step 4: Implement the button event filter**

In `soundflow.design.motion`, create a `QObject` event filter that:

- recognizes mouse press plus Space/Return/Enter key press on enabled `QPushButton` objects;
- skips buttons that already own a non-controller graphics effect;
- stops and replaces any existing feedback animation for the same button;
- assigns a `QGraphicsOpacityEffect` at opacity `0.72`;
- animates opacity to `1.0` over `ANIMATION_FAST` with `OutCubic`;
- removes the graphics effect and dictionary entry only if the finishing animation is still current; and
- returns `False` so Qt continues delivering the original event.

Expose `animation_for(button)` for deterministic testing. Cache one controller on the `QApplication` object so repeated installation returns the same instance.

- [ ] **Step 5: Install button motion at startup**

Export `install_motion_feedback` from `soundflow.design`. In `app.py`, call it immediately after `register_application_fonts()`:

```python
from soundflow.design import (
    install_motion_feedback,
    register_application_fonts,
)

register_application_fonts()
install_motion_feedback(application)
```

- [ ] **Step 6: Animate changed status messages**

Give `_status_label` its own `QGraphicsOpacityEffect` and `QPropertyAnimation`. Configure duration `ANIMATION_NORMAL`, end value `1.0`, easing `OutCubic`, and one loop. In `set_status`, animate only when the label text changes:

```python
running = (
    self._label_animation.state()
    == QPropertyAnimation.State.Running
)
start = self._label_effect.opacity() if running else 0.35
self._label_animation.stop()
self._status_label.setText(label)
self._label_effect.setOpacity(start)
self._label_animation.setStartValue(start)
self._label_animation.setEndValue(1.0)
self._label_animation.start()
```

Keep the independent status-dot pulse behavior unchanged.

- [ ] **Step 7: Run motion tests and commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_button_motion tests.test_motion_ui \
  tests.test_ui_runtime_contracts -v
git add src/soundflow/design/motion.py src/soundflow/design/__init__.py \
  src/soundflow/app.py src/soundflow/ui/widgets/status_bar.py \
  tests/test_button_motion.py tests/test_motion_ui.py
git commit -m "Add restrained interface feedback"
```

Expected: all invoked tests pass, clicks remain immediate, effects clean up, and the existing recording pulse contract remains green.

---

### Task 4: Smooth Model Download Progress

**Files:**
- Modify: `src/soundflow/preferences/model_manager.py`
- Modify: `tests/test_model_manager_ui.py`

**Interfaces:**
- Consumes: `ANIMATION_CONTROL`.
- Produces: one `QPropertyAnimation` per `_ModelRow.progress`.
- Preserves: immediate `downloaded MB / total MB` text and exact byte accounting.

- [ ] **Step 1: Write failing determinate progress tests**

In `test_progress_and_errors_are_inline`, after emitting a valid byte update, assert:

```python
self.assertEqual(row.animation.duration(), ANIMATION_CONTROL)
self.assertEqual(
    row.animation.state(),
    QAbstractAnimation.State.Running,
)
self.assertEqual(progress.format(), "225.0 MB / 500.0 MB")
QTest.qWait(ANIMATION_CONTROL + 30)
self.assertEqual(progress.value(), 45)
```

Add a rapid-update assertion: issue fill 20, wait briefly, issue fill 70, then wait and assert the bar ends at 70 while its format immediately displays the newest byte values.

- [ ] **Step 2: Write failing stop-state tests**

Start a determinate progress animation, then call unknown progress, error, cancellation, and success helpers in separate assertions. Verify the row animation is stopped before the bar becomes indeterminate or hidden.

- [ ] **Step 3: Run model-manager tests and verify RED**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen \
  python3 -m unittest tests.test_model_manager_ui -v
```

Expected: failures report the missing row animation and immediate fill assignment.

- [ ] **Step 4: Add per-row value animations**

Extend `_ModelRow` with `animation: QPropertyAnimation`. Create it with the progress bar as target and parent:

```python
animation = QPropertyAnimation(progress, b"value", progress)
animation.setDuration(ANIMATION_CONTROL)
animation.setEasingCurve(QEasingCurve.Type.OutCubic)
```

For determinate Downloading events:

```python
row.animation.stop()
row.animation.setStartValue(row.progress.value())
row.animation.setEndValue(max(0, min(100, int(fill))))
row.animation.start()
```

Update the MB format before starting. For all non-download phases and unknown totals, stop the animation before setting the range/value. Stop it before hiding progress in success, cancellation, and error paths.

- [ ] **Step 5: Run model-manager and motion tests, then commit**

```bash
PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest \
  tests.test_model_manager_ui tests.test_motion_ui tests.test_design -v
git add src/soundflow/preferences/model_manager.py \
  tests/test_model_manager_ui.py
git commit -m "Animate model download progress"
```

Expected: all invoked tests pass; MB text updates immediately while fill transitions remain smooth and interruptible.

---

### Task 5: Full Verification, Package, Install, and Visual Review

**Files:**
- Verify: `src/soundflow/assets/fonts/`
- Verify: `src/soundflow/design/`
- Verify: `src/soundflow/ui/widgets/`
- Verify: `src/soundflow/preferences/model_manager.py`
- Verify: `tests/`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: a tested, packaged, freshly installed Soundflow application with reviewed typography and motion.

- [ ] **Step 1: Run focused typography and motion regression**

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

- [ ] **Step 3: Compile and inspect repository consistency**

```bash
PYTHONPATH=.vendor/python:src python3 -m compileall -q src tests
git diff --check
rg -n "Roboto|ROBOTO" src packaging tests && exit 1 || true
```

Expected: compilation and diff checks pass, and no Roboto references remain.

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

Expected: PyInstaller succeeds, the service is `enabled` and `active`, and executable hashes match.

- [ ] **Step 5: Verify packaged Geist assets**

```bash
find dist/Soundflow/_internal/soundflow/assets/fonts \
  -maxdepth 1 -type f -printf '%f\n' | sort
```

Expected: exactly the seven Geist TTF files and `GEIST-OFL.txt`; no Roboto asset is present.

- [ ] **Step 6: Capture and inspect light/dark UI**

Capture Preferences, History, Dictation, and a model-download row in both themes. Verify:

- Geist Sans renders page, section, body, and control text;
- Geist Mono renders shortcuts, paths, model sizes, and MB progress;
- weights remain legible without excessive boldness;
- text is not clipped at compact control heights;
- toggle movement, button feedback, status fade, and progress interpolation are restrained and smooth; and
- no persistent opacity effect or stale animation remains after completion.

- [ ] **Step 7: Confirm user-owned screenshots remain untouched**

```bash
git status --short
```

Expected: only the user's pre-existing `5db20f0e-b172-4f45-a323-c99fbc5d68df.png` and `screenshots/` paths remain untracked.
