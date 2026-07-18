# Soundflow

Soundflow is a privacy-first desktop dictation MVP for Linux and Windows. It records a
microphone, detects phrase boundaries, transcribes with a model stored entirely on the local
machine, and leaves the result editable.

Repository: [Sayem-Ahmed-Shayeed/SoundFlow](https://github.com/Sayem-Ahmed-Shayeed/SoundFlow)

Implemented now:

- Redesigned modular UI with sidebar navigation across Dictation, History, and Playground pages
- Design token system — dark/light theming, Roboto fonts, spacing scale, Qt stylesheet engine
- Dictation page with waveform ring, voice orb, animated record button, and status indicators
- Editable history page with transcript cards, copy, clear, TXT, Markdown, and DOCX export
- Preferences dialog with five tabs: General, Dictation, Playback, Shortcuts, and System readiness
- Appearance selector (dark / light / follow system)
- Click-based start/stop, global toggle, and push-to-talk with press-and-release handling
- Native Wayland global shortcut support through the XDG desktop portal
- Automatic paste at the active cursor when push-to-talk is released
- Phrase-by-phrase transcription while recording continues
- Explicitly local `faster-whisper` model loading
- System tray operation
- A demo backend for testing UI and control flow without a model

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

## Download a Whisper model

Open **Preferences -> Dictation -> Whisper models** and choose Download for Tiny, Base, Small,
Medium, or Large-v3 Turbo. Downloads run in the background, are validated before use, and become
active automatically. Installed inactive models can be selected with Use or removed with Delete.

For an existing CTranslate2/faster-whisper directory, use **Model directory -> Browse**. Soundflow
never deletes custom model directories.

## Prepare an offline installer model

Prepare a faster-whisper/CTranslate2 model on a connected staging machine, then copy the complete
directory to the offline computer.

For an installer build, prepare the recommended `small` model with:

```bash
python scripts/prepare_model.py --model small
```

This writes a file-by-file SHA-256 manifest and places the model where the PyInstaller specification
will include it. The script remains the offline-installer workflow; in-app downloads are separate.

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
├── app.py                  command-line and Qt startup
├── audio.py                sounddevice microphone adapter
├── hotkeys.py              Windows/X11/Wayland shortcut listener
├── injector.py             focused-application paste adapter
├── portal.py               XDG desktop portal integration
├── transcription.py        capture/segment/inference workers
├── assets/
│   └── fonts/              bundled Roboto (Regular, Medium, Bold)
├── core/
│   ├── state.py            dictation state machine
│   ├── segmenter.py        phrase endpoint detector
│   ├── settings.py         atomic local JSON settings
│   └── export.py           TXT, Markdown, and DOCX export
├── design/
│   ├── theme.py            colour palette, dark/light stylesheets
│   ├── fonts.py            preferred font resolution
│   └── spacing.py          4-px spacing scale, radii, font sizes
├── history/
│   ├── page.py             transcript history page
│   ├── models.py           transcript data model
│   └── store.py            in-memory transcript store
├── playground/
│   ├── page.py             demo/testing playground page
│   └── actions.py          playground action definitions
├── preferences/
│   ├── dialog.py           preferences dialog shell
│   ├── system_check.py     system readiness checks
│   └── tabs/
│       ├── dictation.py    microphone, language, endpoint settings
│       ├── general.py      start minimised, appearance, profile
│       ├── playback.py     playback and audio output settings
│       ├── shortcuts.py    global hotkey configuration
│       └── system.py       system status and readiness checks
├── ui/
│   ├── main_window.py      top-level window with sidebar + page stack
│   ├── pages/
│   │   └── dictation_page.py
│   └── widgets/
│       ├── sidebar.py, top_tab_bar.py, status_bar.py
│       ├── waveform_ring.py, voice_orb.py
│       ├── toggle_switch.py, compat.py
│       └── window_chrome.py
├── _legacy/
│   └── ui_module.py        backward-compat re-exports
└── utils/
    └── files.py            file I/O helpers
```

## Known MVP constraints

- The microphone must accept 16 kHz mono input. Production should capture the device's preferred
  format and resample.
- Wayland global shortcuts and keyboard injection require the XDG GlobalShortcuts and
  RemoteDesktop portals, which need one-time desktop approval.
- Automatic insertion is clipboard plus simulated paste. On Wayland it may fall back to leaving
  the transcript on the clipboard.
- CUDA works only when the installed CTranslate2 build and NVIDIA runtime are compatible. CPU
  INT8 is the supported default.
- The MVP shows completed phrases rather than unstable word-by-word guesses.
