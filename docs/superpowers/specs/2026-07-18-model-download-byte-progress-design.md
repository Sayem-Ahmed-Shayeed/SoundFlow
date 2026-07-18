# Model Download Byte Progress Design

## Goal

Replace the misleading percentage label in the Whisper model manager with a truthful, live aggregate byte counter such as `186.4 MB / 486.0 MB`.

## User Experience

- While downloading, the progress bar displays downloaded model data over total model data in decimal megabytes.
- Cached files count as already downloaded, so a partially cached model may begin above zero.
- The counter combines every required file for the selected model instead of resetting for each file.
- The bar fill remains proportional to downloaded bytes, but no percentage is shown.
- Non-download phases continue to use the existing status label: Preparing, Verifying, Ready, Cancelled, or the relevant error.
- If exact size metadata is unavailable, the UI keeps the phase text and uses an indeterminate bar rather than presenting an invented total.

## Download Metadata and Accounting

Before downloading, the Hugging Face snapshot API runs in dry-run mode with the same repository, revision, destination, and allow-pattern arguments used for the real download. The returned `DryRunFileInfo` records provide:

- the exact required file size;
- whether each file is already cached; and
- whether it still needs to be downloaded.

The total is the sum of all required file sizes. The initial completed count is the sum of files already available locally. During the real snapshot download, the custom tqdm adapter accepts only byte-oriented file-transfer bars and adds each positive byte delta to the aggregate completed count. Counts are clamped between zero and the total to protect the UI from duplicate, resumed, or malformed progress events.

The existing single-worker download behavior remains unchanged. Cancellation is checked during metadata discovery and every transfer update.

## Progress Boundary

The service-to-UI progress callback is extended to carry:

- phase;
- internal fill value;
- completed bytes; and
- total bytes.

The thread adapter accepts two-argument progress events from test doubles and older injected downloaders, defaulting missing byte values to zero. Its Qt signal always emits the normalized four-field event. This preserves the existing dependency-injection boundary while allowing the production downloader to report exact byte totals.

The progress bar uses the internal fill value only to render its filled portion. During a byte download, its visible format is generated from completed and total bytes and never contains `%`.

## Formatting

Byte values use decimal megabytes (`1 MB = 1,000,000 bytes`) with one decimal place, for example `186.4 MB / 486.0 MB`. This is stable during small file transfers and matches common download-size presentation.

## Error Handling

- Failure to obtain dry-run metadata does not abort an otherwise valid download. The transfer proceeds with an indeterminate bar and phase text.
- Invalid or zero totals are treated as unknown.
- Download, verification, cancellation, and cleanup errors continue through the existing model-manager error path.
- A successful verification completes the visual bar before the row transitions to Ready.

## Testing

Service tests cover:

- exact totals from multiple files;
- cached files included in the initial completed count;
- live aggregate byte deltas across multiple file bars;
- resumed or duplicate updates clamped safely;
- unknown metadata fallback;
- cancellation during discovery and transfer; and
- successful completion.

UI tests cover:

- `downloaded MB / total MB` formatting;
- absence of percentage text;
- proportional fill;
- two-argument fake downloader compatibility;
- unknown-total behavior; and
- completed and error states.

The focused model service and model-manager UI suites must pass, followed by the broader non-audio test suite, packaged application build, fresh installation, and a visual screenshot check.

## Out of Scope

- Download speed and time-remaining estimates.
- Pause and resume controls.
- Changes to model catalog entries or model inference behavior.
