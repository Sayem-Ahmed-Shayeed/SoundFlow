# Model Download Percentage Design

## Goal

Show the current model-download percentage inside the existing progress bar so
users can see exact progress without increasing row height.

## UI Contract

- Use the existing `QProgressBar` in each model row.
- Enable its native centered text and use Qt's `%p%` format.
- Display a clamped integer from `0%` through `100%`.
- Keep the existing phase label, such as `Downloading` or `Verifying`, beside
  the bar.
- Preserve current completion, cancellation, and error behavior: the progress
  bar is hidden when the operation ends.
- Apply existing light/dark progress-bar styling; add only the text styling
  needed for readable contrast.

## Verification

- Add a UI regression proving the progress bar displays `42%` for a 42 percent
  update.
- Verify clamping remains `0–100`.
- Run the model-manager and design tests.
- Rebuild, freshly uninstall/install, verify the service, and confirm the built
  and installed executable hashes match.
