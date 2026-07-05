# System Tab Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw System preferences form with a clear local-readiness dashboard and local-data card.

**Architecture:** Keep `SystemCheckResult` and `open_data_folder()` as the behavior boundaries. Rebuild only `SystemTab`, add narrowly scoped theme selectors, and verify the widget through Qt tests.

**Tech Stack:** Python 3, PySide6 widgets, Qt stylesheets, unittest.

## Global Constraints

- Preserve all runtime, model, microphone, shortcut, permission, and data-folder behavior.
- Reuse the existing design tokens and `preferencesCard` surface.
- Do not restore the removed About panel.
- Keep the layout responsive without fixed card widths.

---

### Task 1: System tab structure

**Files:**
- Modify: `src/soundflow/preferences/tabs/system.py`
- Test: `tests/test_system_tab_ui.py`

**Interfaces:**
- Consumes: `run_system_check(settings) -> SystemCheckResult`
- Produces: `SystemTab.run_check() -> None`

- [ ] **Step 1: Write the failing structure test**

Create a Qt test that constructs `SystemTab`, finds five widgets named
`systemCheckRow`, and confirms the compact `systemCheckButton`, model path, and
data path are visible.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_system_tab_ui -v`
Expected: FAIL because the new object names and rows do not exist.

- [ ] **Step 3: Implement the readiness and local-data cards**

Replace the form with reusable row builders, selectable wrapped paths, natural
width action buttons, and neutral initial states.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_system_tab_ui -v`
Expected: PASS.

### Task 2: Diagnostic state rendering

**Files:**
- Modify: `src/soundflow/preferences/tabs/system.py`
- Modify: `src/soundflow/design/theme.py`
- Test: `tests/test_system_tab_ui.py`

**Interfaces:**
- Consumes: `SystemCheckResult`
- Produces: status labels and dynamic `state` properties.

- [ ] **Step 1: Write the failing state test**

Patch `run_system_check()` with a deterministic result and verify the overall
pill, all component labels, and CPU fallback copy after `run_check()`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_system_tab_ui -v`
Expected: FAIL because the status widgets do not update independently.

- [ ] **Step 3: Implement status updates and theme selectors**

Map readiness fields to ready, warning, and error copy; refresh dynamic Qt
properties; style rows, pills, path surfaces, and compact secondary actions in
both themes.

- [ ] **Step 4: Run focused and regression tests**

Run: `python3 -m unittest tests.test_system_tab_ui tests.test_system_check -v`
Expected: PASS.

### Task 3: Package verification and reinstall

**Files:**
- No source changes.

**Interfaces:**
- Consumes: repository test and install scripts.
- Produces: freshly installed Soundflow application.

- [ ] **Step 1: Run UI and packaged smoke tests**

Run the repository's Qt/UI tests and packaged `--smoke-test`.
Expected: PASS.

- [ ] **Step 2: Reinstall**

Run: `./install-linux.sh`
Expected: package installs and the user service is enabled and active.

- [ ] **Step 3: Verify service state**

Run: `systemctl --user is-enabled soundflow.service`
Run: `systemctl --user is-active soundflow.service`
Expected: `enabled` and `active`.
