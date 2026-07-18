# Theme Toggle and True-Black Dark Mode

## Goal

Replace the Appearance theme dropdown with a compact, professional segmented
control and change the dark-mode canvas from blue-black to true black.

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

## Scope

The change is limited to the modular General preferences tab, shared dark theme
tokens/rules, and focused UI regression tests. Other dropdowns such as language,
microphone, and audio-device selectors remain dropdowns.

## Verification

- A UI test confirms the dropdown is gone and the Light/Dark buttons are present,
  mutually exclusive, initialized from settings, and written back correctly.
- A theme test confirms the dark application canvas resolves to `#000000`.
- Existing focused preferences and theme tests pass.
- Rebuild and reinstall Soundflow, then verify the user service and installed
  binary.
