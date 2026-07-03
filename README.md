# Soundflow

Soundflow is a privacy-first desktop dictation MVP for Linux and Windows. It records a
microphone, detects phrase boundaries, transcribes with a model stored entirely on the local
machine, and leaves the result editable.

Repository: [Sayem-Ahmed-Shayeed/SoundFlow](https://github.com/Sayem-Ahmed-Shayeed/SoundFlow)

Implemented now:

- Click-based start and stop
- Global toggle dictation shortcut
- Global push-to-talk with press and release handling
- Native Wayland global shortcut support through the desktop portal
- A compact recording overlay that appears above the current application
- Automatic paste at the active cursor when push-to-talk is released
- Phrase-by-phrase transcription while recording continues
- Explicitly local `faster-whisper` model loading
- Editable transcript, copy, clear, TXT, Markdown, and DOCX export
- Insert into the focused application through clipboard paste
- Microphone, language, inference, endpoint, and shortcut settings
- System tray operation
- A demo backend for testing UI and control flow without a model
- Windows and Linux/X11 hotkeys

Wayland deliberately blocks arbitrary global keyboard capture and input injection. Soundflow uses
the XDG GlobalShortcuts and RemoteDesktop portals, which require one-time desktop approval.

## Requirements

- Python 3.11, 3.12, 3.13, or 3.14
- Linux or Windows
- A microphone
- A complete CTranslate2/faster-whisper model directory

Linux runtime packages typically include PortAudio and the Qt XCB dependencies. On Ubuntu:

```bash
sudo apt install python3-venv portaudio19-dev libxcb-cursor0
```

The prepared Linux PyInstaller bundle can carry `libportaudio.so.2` itself. System packages are
still the simpler choice for source development.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Run it before installing a model

Demo mode records real microphone audio but returns a labelled fake result. This verifies audio,
buttons, push-to-talk, the tray, exports, and insertion:

```bash
soundflow --demo
```

From this source checkout, the convenience launcher does the same and also detects the local
`.vendor/python` test bundle if present:

```bash
./run-soundflow.sh --demo
```

If the desktop does not allow global keyboard listeners:

```bash
soundflow --demo --no-hotkeys
```

Default shortcuts:

- Push-to-talk: `Ctrl+Alt+Space`

Hold the shortcut while speaking and release it to transcribe and paste at the active cursor.
The shortcut remains active while the main window is hidden. The installer also starts Soundflow
in the background when you sign in.

On first launch, approve the global-shortcut prompt and then the keyboard-control prompt. Soundflow
stays visible until shortcut setup succeeds. The Home indicator reports connecting, ready,
recording, transcribing, or setup-required states and provides a retry action when needed.

## Install an offline model

Soundflow does not fetch models. Prepare a faster-whisper/CTranslate2 model on a connected staging
machine, then copy the complete directory to the offline computer.

For an installer build, prepare the recommended `small` model with:

```bash
python scripts/prepare_model.py --model small
```

This writes a file-by-file SHA-256 manifest and places the model where the PyInstaller specification
will include it. Running Soundflow itself never invokes this build-time downloader.

Default locations:

- Linux: `~/.local/share/soundflow/models/faster-whisper-small/`
- Windows: `%LOCALAPPDATA%\Soundflow\models\faster-whisper-small\`

You can instead select a directory under **Settings → Recognition**, or set
`SOUNDFLOW_MODEL_PATH`.

The directory must contain `model.bin`, `config.json`, tokenizer data, and the model vocabulary.
`small` is the recommended balanced model; `base` is lighter. Soundflow supplies the directory
path to faster-whisper with `local_files_only=True`.

Then run:

```bash
soundflow
```

The repository's prepared Linux folder build can be launched directly with:

```bash
./dist/Soundflow/Soundflow
```

It already contains the `small` model and the PortAudio/XCB runtime libraries used by the bundle.
Windows builds must be produced on Windows with `packaging/soundflow.spec`, then wrapped with the
provided NSIS script.

### Install like a normal Linux application

From the repository directory:

```bash
chmod +x install-linux.sh
./install-linux.sh
```

This installs into your user account without `sudo`, adds Soundflow to the application menu, and
creates `~/.local/bin/soundflow`. To remove it later:

```bash
./uninstall-linux.sh
```

## Audio and privacy behavior

- Audio is captured as 16 kHz, mono, signed 16-bit PCM.
- A lightweight local energy detector ends a phrase after 700 ms of silence by default.
- Completed phrases are sent to faster-whisper on a worker thread.
- Audio exists only in memory and is discarded after processing.
- Transcripts are not saved unless the user exports them.
- There is no telemetry or update checker.
- The application does not include a network client.

The first model load can take several seconds. Later phrases reuse the loaded model.

## Development

Core tests use only the Python standard library:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Project layout:

```text
src/soundflow/
├── app.py              command-line and Qt startup
├── ui.py               main window, settings, and tray
├── audio.py            sounddevice microphone adapter
├── transcription.py    capture/segment/inference workers
├── hotkeys.py          Windows and X11 shortcut listener
├── injector.py         focused-application paste adapter
└── core/
    ├── state.py        dictation state machine
    ├── segmenter.py    phrase endpoint detector
    ├── settings.py     atomic local JSON settings
    └── export.py       TXT, Markdown, and DOCX export
```

## Known MVP constraints

- The microphone must accept 16 kHz mono input. Production should capture the device's preferred
  format and resample.
- Global hotkeys use `pynput`; Wayland portal support is not yet implemented.
- Automatic insertion is clipboard plus simulated paste. On Wayland it may fall back to leaving
  the transcript on the clipboard.
- CUDA works only when the installed CTranslate2 build and NVIDIA runtime are compatible. CPU
  INT8 is the supported default.
- The MVP shows completed phrases rather than unstable word-by-word guesses.
