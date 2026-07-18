# UI Density, Theme, and Recording Overlay Cleanup

## Goal

Make Soundflow smaller, clearer, and more professional: replace the Appearance
dropdown with a segmented control, use a true-black dark canvas, remove stale
local-only messaging and redundant footers, compact History and Preferences,
and replace the oversized recording overlay with a WhisperFlow-style pill.

## Interaction design

- Show two adjacent checkable buttons labeled `Light` and `Dark`.
- Exactly one option is selected at all times.
- The selected option uses the existing violet accent; the inactive option uses
  the neutral control surface.
- Clicking an option updates the same `settings.appearance` value currently
  written by the dropdown, so persistence and live theme application remain
  unchanged.
- Preserve keyboard focus and accessible names for both choices.

## Dark palette

- The main window and page canvas use `#000000` in dark mode.
- Cards, sidebar, inputs, and hover states use slightly lifted neutral-black
  surfaces rather than blue surfaces so structure remains visible.
- Text, borders, semantic colors, and the violet accent keep accessible contrast.
- Light mode remains unchanged.

## History

- Render the transcript count as a compact inline badge rather than a large tile.
- Remove the visible `Insert` action from every transcript card.
- Keep `Edit`, `Copy`, and the overflow menu for export and deletion.
- Preserve the centered empty state and unclipped transcript/editor geometry.

## Preference controls

- Give the model path, Browse button, and Dictation dropdowns the same compact
  control height.
- Apply the same clean dropdown treatment to shortcut modifier/key fields.
- Dropdowns retain their native behavior but use consistent padding, borders,
  popup colors, and a simple chevron instead of the current native-looking arrow.

## Removed chrome and copy

- Remove the `Changes are saved automatically` line; settings still auto-save.
- Remove the persistent bottom status bar. Recording state remains visible on the
  Dictation page and in the floating recording overlay.
- Remove the sidebar `100% Private` card and offline-only copy because future API
  processing means that promise will no longer be universally accurate.

## Recording overlay

- Replace the 360 by 72 white panel with a compact, dark floating pill.
- Show a small live waveform/activity mark, one state label (`Listening` or
  `Transcribing`), and a concise shortcut/release hint.
- Keep it non-focus-stealing, centered near the bottom of the active screen, and
  animated with the existing restrained fade.
- Ensure long three-key shortcuts fit without truncation.

## Scope

The change is limited to the modular shell, History and Preferences pages,
shared dark theme/control rules, the existing recording overlay, and focused UI
regression tests. Language, microphone, audio-device, and shortcut selectors
remain dropdowns.

## Verification

- A UI test confirms the dropdown is gone and the Light/Dark buttons are present,
  mutually exclusive, initialized from settings, and written back correctly.
- A theme test confirms the dark application canvas resolves to `#000000`.
- History tests confirm no Insert button is present and the result count stays
  compact.
- Preferences tests confirm uniform control heights, styled dropdowns, and the
  absence of the saved-status footer.
- Shell tests confirm the privacy card and persistent status footer are absent.
- Overlay tests confirm its compact geometry, retained state labels, and full
  shortcut text.
- Existing focused preferences and theme tests pass.
- Rebuild and reinstall Soundflow, capture screenshots, and ask a separate agent
  to review the screenshots. Apply any concrete visual corrections it identifies,
  then rebuild/reinstall and verify the user service and installed binary again.
