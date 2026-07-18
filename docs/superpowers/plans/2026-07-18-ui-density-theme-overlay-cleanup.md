# UI Density, Theme, and Recording Overlay Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a compact Soundflow shell with a true-black dark mode, polished preference controls, simplified History actions, no stale local-only chrome, and a minimal recording pill.

**Architecture:** Keep existing data and runtime behavior intact while changing only modular Qt widgets and shared QSS. Reuse `AppearanceSelector` for the two-option theme control, retain native `QComboBox` behavior with a focused shared style, and preserve the existing overlay state/fade API while shrinking its layout.

**Tech Stack:** Python 3, PySide6/Qt Widgets, Qt Style Sheets, unittest, PyInstaller, systemd user service.

## Global Constraints

- Main dark-mode canvas is exactly `#000000`; light mode is unchanged.
- Existing settings keys and persistence behavior remain unchanged.
- Language, device, microphone, and shortcut selectors remain dropdowns.
- Cursor injection, dictation state, and hotkey behavior must not change.
- Production changes follow red-green-refactor and use `apply_patch`.
- The installed app is rebuilt and reinstalled after code changes.

---

### Task 1: Segmented theme selector and true-black palette

**Files:**
- Modify: `tests/test_general_tab_ui.py`
- Modify: `tests/test_ui.py`
- Modify: `src/soundflow/ui/widgets/compat.py`
- Modify: `src/soundflow/preferences/tabs/general.py`
- Modify: `src/soundflow/design/theme.py`

**Interfaces:**
- Consumes: `AppearanceSelector(value: str)` with `value()`, `set_value()`, and `changed`.
- Produces: a two-option `AppearanceSelector` and unchanged `GeneralTab.write_back(settings)` behavior.

- [ ] **Step 1: Write failing tests** asserting General has Light/Dark buttons and no theme combo, button selection writes `settings.appearance`, and `stylesheet(True)` contains a `#000000` application canvas.
- [ ] **Step 2: Run** `PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_general_tab_ui tests.test_ui -v` and confirm failures describe the old combo/three-option selector and old background.
- [ ] **Step 3: Implement** a two-option segmented selector, connect it to preference auto-save through its checkable buttons, update `write_back`, and change dark neutrals to black/near-black values.
- [ ] **Step 4: Re-run the focused tests** and confirm they pass.

### Task 2: Compact History actions and count

**Files:**
- Modify: `tests/test_history_geometry.py`
- Modify: `src/soundflow/history/page.py`
- Modify: `src/soundflow/ui/main_window.py`
- Modify: `src/soundflow/design/theme.py`

**Interfaces:**
- Consumes: `TranscriptCard(entry)` and `HistoryPage(store)`.
- Produces: transcript cards exposing Edit, Copy, and overflow actions without an Insert action.

- [ ] **Step 1: Write failing tests** asserting cards contain no `Insert transcript at cursor` button and `resultCount` has compact height/width after layout.
- [ ] **Step 2: Run** `PYTHONPATH=.vendor/python:src QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_history_geometry -v` and confirm failure against the existing card/count UI.
- [ ] **Step 3: Remove** the Insert button/signal connection and set compact result-count sizing and QSS while preserving the empty-state stretch logic.
- [ ] **Step 4: Re-run History tests** and confirm empty and populated layouts pass.

### Task 3: Uniform fields and polished dropdowns

**Files:**
- Modify: `tests/test_dictation_tab_ui.py`
- Modify: `tests/test_shortcuts_tab_ui.py`
- Modify: `src/soundflow/preferences/tabs/dictation.py`
- Modify: `src/soundflow/design/theme.py`

**Interfaces:**
- Consumes: `CONTROL_HEIGHT_SM`, `compactPathField`, `compactPreferenceField`, and `compactShortcutField`.
- Produces: uniform compact geometry and shared dropdown/popup styling.

- [ ] **Step 1: Write failing tests** asserting Browse/path/dropdowns all equal `CONTROL_HEIGHT_SM`, Browse has `compactBrowseButton`, and compact combos reserve a consistent arrow area.
- [ ] **Step 2: Run** the Dictation and Shortcuts UI tests and confirm Browse geometry/style currently fails.
- [ ] **Step 3: Implement** fixed-height Browse geometry plus compact QSS with consistent radius, padding, drop-down subcontrol, chevron, hover/focus state, and popup item spacing.
- [ ] **Step 4: Re-run both focused test modules** and confirm they pass in dark and light stylesheets.

### Task 4: Remove redundant footer and local-only messaging

**Files:**
- Modify: `tests/test_ui.py`
- Modify: `src/soundflow/preferences/page.py`
- Modify: `src/soundflow/ui/widgets/sidebar.py`
- Modify: `src/soundflow/ui/main_window.py`

**Interfaces:**
- Consumes: the existing hidden compatibility widgets for legacy runtime callbacks.
- Produces: a shell without `privacyCard`, `savedStatus`, or visible `StatusBar`, while runtime status callbacks remain safe.

- [ ] **Step 1: Write failing shell tests** asserting the three removed widgets are absent from a constructed `MainWindow`.
- [ ] **Step 2: Run** `tests.test_ui` and confirm it fails because those widgets exist.
- [ ] **Step 3: Remove** the saved label and sidebar card; stop adding `StatusBar` to the layout while retaining a hidden compatibility status object for unchanged runtime calls.
- [ ] **Step 4: Re-run shell and motion tests** and confirm navigation and state transitions remain valid.

### Task 5: Minimal WhisperFlow-style recording pill

**Files:**
- Modify: `tests/test_ui.py`
- Modify: `src/soundflow/_legacy/ui_module.py`

**Interfaces:**
- Consumes: `show_recording(shortcut)`, `show_processing()`, `set_level(level)`, and `hide_animated()`.
- Produces: the same overlay API in a compact pill no larger than 300 by 52 pixels.

- [ ] **Step 1: Write failing tests** asserting compact dimensions, full three-key shortcut text, and correct Listening/Transcribing state copy.
- [ ] **Step 2: Run** `tests.test_ui.UiTests.test_overlay_displays_three_key_chord` and confirm failure on the old 360 by 72 geometry.
- [ ] **Step 3: Implement** a small translucent dark pill, compact waveform, single-line state/hint arrangement, and updated overlay-specific styling while preserving placement and fade behavior.
- [ ] **Step 4: Re-run overlay and shell tests** and confirm they pass.

### Task 6: Visual review, correction, package, and install

**Files:**
- Modify only files implicated by concrete screenshot-review findings.

**Interfaces:**
- Consumes: the completed source UI and repo-native installer.
- Produces: verified installed binaries and review screenshots.

- [ ] **Step 1: Run focused regression suite** for General, Dictation, Shortcuts, History, UI shell, toggle switch, and motion.
- [ ] **Step 2: Run** `git diff --check` on changed source/test files.
- [ ] **Step 3: Build** with `PYTHONPATH=.vendor/python python3 -m PyInstaller --noconfirm packaging/soundflow.spec` and confirm exit code 0.
- [ ] **Step 4: Reinstall** with `./uninstall-linux.sh` followed by `./install-linux.sh`.
- [ ] **Step 5: Capture** dark/light Preferences, History, Dictation, and recording-overlay screenshots from the rebuilt UI.
- [ ] **Step 6: Dispatch a separate visual-review agent** with the screenshots and requirement checklist; require actionable findings ranked by severity.
- [ ] **Step 7: If findings exist, add/adjust regression tests first, implement corrections, rebuild, reinstall, and recapture affected screenshots.**
- [ ] **Step 8: Verify** service enabled/active, installed/build binary hashes match, and desktop portal sessions are present.
