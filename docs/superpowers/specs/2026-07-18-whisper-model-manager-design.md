# Whisper Model Manager Design

## Goal

Let users download, activate, and remove a curated set of faster-whisper
models from Soundflow's Dictation settings without freezing the application or
manually entering model directories.

## Product Scope

The model manager supports exactly these multilingual models:

| Model ID | Display name | Guidance |
| --- | --- | --- |
| `tiny` | Tiny | Fastest, lowest resource use |
| `base` | Base | Fast and lightweight |
| `small` | Small | Recommended balance |
| `medium` | Medium | Higher accuracy, heavier |
| `large-v3-turbo` | Large-v3 Turbo | Best quality, highest resource use |

Custom local model directories remain supported through the existing Browse
control. English-only, Distil, and arbitrary Hugging Face model identifiers are
outside this feature.

## User Experience

Settings -> Dictation contains a compact `Whisper models` card. Each catalog
row contains:

- model display name and short speed/quality guidance;
- one status: `Active`, `Installed`, or `Not downloaded`;
- one contextual action: `Download`, `Use`, or `Delete`.

Small is visually marked `Recommended`. The active model cannot be deleted.
Inactive managed models can be deleted to reclaim disk space. A downloaded
model becomes active automatically after validation succeeds. An already
installed inactive model exposes `Use`, which activates it immediately unless
dictation is currently running; an active dictation finishes before the
runtime rebuilds with the new model.

Only one model download can run at a time. While downloading, the selected row
shows a slim progress bar, percentage, current phase, and `Cancel`; download
actions on other rows are disabled. The phases are `Preparing`, `Downloading`,
and `Verifying`.

Failures are shown inline on the affected row in plain language. The previous
active model and saved `model_path` remain unchanged after a failed or cancelled
download.

## Architecture

### Catalog

Create a focused catalog module containing immutable metadata for the five
models. Each entry exposes its model ID, display name, guidance, repository ID,
managed installation directory, and recommended state. UI code reads catalog
metadata but does not construct repository URLs or filesystem paths.

Managed models live under:

```text
<data_directory>/models/faster-whisper-<model-id>/
```

The bundled `small` model is detected and displayed as installed when present.
Custom paths outside the managed model root are never deleted by the manager.

### Model Service

Create a model-management service independent of Qt widgets. It owns:

- installed-state detection;
- required-file validation;
- download into a sibling `.partial` directory;
- progress and cancellation reporting;
- manifest generation and final validation;
- atomic promotion of a validated partial directory;
- safe deletion restricted to catalog-managed directories.

Downloads use Hugging Face Hub's snapshot API with the exact faster-whisper
repository mapping and file allow-list used by faster-whisper. The downloader
runs with one worker so progress and cancellation are deterministic. Required
files include `model.bin` and `config.json`; tokenizer, vocabulary, and
preprocessor files are downloaded when available.

After downloading, Soundflow writes `soundflow-manifest.json` with file sizes
and SHA-256 hashes. This preserves compatibility with the existing runtime
integrity check. The partial directory is atomically renamed only after
validation and manifest generation complete.

### Background Worker

A Qt worker object performs service calls off the UI thread and emits:

- phase changes;
- integer progress from 0 through 100;
- successful installation with the final path;
- cancellation;
- a normalized user-facing error.

The worker owns a thread-safe cancellation event. Cancellation is cooperative:
the active transfer stops at its next progress update, the partial directory is
removed, and the worker terminates cleanly. Closing Preferences does not destroy
an active worker; the application-level owner keeps it alive until completion or
cancellation.

### Settings and Runtime Integration

On successful installation, Soundflow updates `Settings.model_path`, persists
settings, refreshes model-row states, and requests the same runtime rebuild used
by other recognition-setting changes. Runtime replacement respects the existing
recording/draining guard so an active dictation is not interrupted.

Choosing `Use` follows the same settings and runtime path without a download.
Deletion re-checks the persisted active path immediately before removing files,
preventing stale UI state from deleting the active model.

## Failure Handling

The service normalizes these cases:

- no network or Hub timeout;
- insufficient permission or disk space;
- invalid catalog model ID;
- incomplete or corrupt downloaded files;
- user cancellation;
- attempt to delete the active model;
- attempt to delete a path outside the managed model root.

No failure can replace or remove the active model. Cleanup errors are logged but
do not hide the original download error. Retrying a model first removes its
stale managed `.partial` directory.

## Accessibility and Visual Rules

- All actions have accessible names that include the model display name.
- Status is represented by text, not color alone.
- Keyboard focus order follows model rows from top to bottom.
- Progress bars expose their numeric value to assistive technology.
- Row controls reuse Soundflow's compact control height, neutral surfaces,
  violet focus treatment, and true-black dark theme.
- Error text wraps within the row and does not expand the full card excessively.

## Testing

Service tests use temporary directories and injected download functions. They
cover catalog metadata, managed paths, installed detection, successful atomic
installation, manifest creation, cancellation, partial cleanup, validation
failure, safe deletion, and active-model deletion protection.

UI tests use a fake worker/service. They cover the five visible rows, status and
action mapping, one-download-at-a-time behavior, progress rendering,
cancellation, inline errors, automatic activation, manual `Use`, and protected
active-model deletion.

Runtime-contract tests verify that activation persists `model_path` and requests
a deferred rebuild during recording. Existing settings, history, theme, and
dictation tests remain green. The two known audio import-mocking failures are
tracked separately because they predate and do not exercise model management.

## Delivery Verification

Before delivery:

1. Run focused service, UI, settings, and runtime-contract tests.
2. Run every non-audio test module in isolation.
3. Run syntax compilation and `git diff --check`.
4. Build the PyInstaller application.
5. Freshly uninstall and install using the repository scripts.
6. Verify `soundflow.service` is enabled and active.
7. Capture and visually inspect the Dictation settings in light and dark themes.

## References

- faster-whisper model mapping and downloader:
  <https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/utils.py>
- Hugging Face Hub snapshot downloads:
  <https://huggingface.co/docs/huggingface_hub/guides/download>
