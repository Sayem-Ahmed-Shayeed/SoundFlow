# Soundflow

Soundflow is private dictation for Linux. Hold a shortcut, speak in English or Bangla, and
the text is typed wherever your cursor is. Speech is transcribed on your own computer with
a local Whisper model; nothing you say is sent anywhere.

Repository: [Sayem-Ahmed-Shayeed/SoundFlow](https://github.com/Sayem-Ahmed-Shayeed/SoundFlow)

What it does:

- Push-to-talk from any app (default `Ctrl+Alt+Space`): hold, speak, release, and the text
  is pasted at the cursor. A small floating pill shows that it is listening.
- Live preview while you speak, then a final transcript when you release.
- On-device speech models from Tiny to Large-v3 Turbo, plus a Bangla model, downloaded
  inside the app. Uses the GPU (CUDA) when there is one.
- Home dashboard: words this week, speaking speed, time saved, day streak, words per day
  and recent dictations.
- History with search, editing, copy, and export to TXT, Markdown or Word.
- Soundflow accounts: sign in with email and password, and your transcripts sync to every
  computer you sign in on. They stay cached locally for offline use.
- Optional AI Polish with Gemini or OpenRouter (off by default) to fix grammar,
  punctuation and filler words.
- Light and dark themes, a tray icon, and it runs in the background after you sign in.

Wayland deliberately blocks apps from capturing keys and typing into other apps. Soundflow
uses the desktop's GlobalShortcuts and RemoteDesktop portals instead, which you approve
once.

## Install on Linux (from a release)

You need 64-bit Linux and a microphone. No `sudo` and no Python are needed.

1. Open the [latest release](https://github.com/Sayem-Ahmed-Shayeed/SoundFlow/releases/latest)
   and download both files into the same folder:
   - `soundflow-<version>-linux-x64.tar.gz`
   - `install.sh`
2. Optional: check the download against the SHA-256 given in the release notes:

   ```bash
   sha256sum soundflow-*-linux-x64.tar.gz
   ```

3. Run the installer from that folder:

   ```bash
   chmod +x install.sh
   ./install.sh
   ```

   It installs Soundflow for your user only, adds it to the application menu, creates the
   `soundflow` command in `~/.local/bin`, and starts it in the background.
4. Sign in, or create an account, in the window that opens.
5. Approve the shortcut prompt from your desktop, then the keyboard-control prompt. These
   let Soundflow hear the shortcut and type into other apps.
6. Download a speech model in **Preferences → Speech model**:

   | Model | Download | Good for |
   | --- | --- | --- |
   | Tiny | 78 MB | Fastest, lowest resource use |
   | Base | 148 MB | Fast and lightweight |
   | Small | 486 MB | Recommended balance |
   | Medium | 1.53 GB | Higher accuracy, heavier |
   | Large-v3 Turbo | 1.62 GB | Best quality, needs the most memory |
   | Bangla (Bengali.AI) | 1.53 GB | Best for Bangla speech; Bangla only |

7. Hold `Ctrl+Alt+Space`, speak, and release. You can change the shortcut in
   **Preferences → Dictation**.

To use AI Polish, add a Gemini or OpenRouter API key in **Preferences → AI Polish**.

### Where Soundflow keeps its files

| What | Where |
| --- | --- |
| The program | `~/.local/share/soundflow-app/` |
| Speech models and the transcript history | `~/.local/share/soundflow/` |
| Settings, API keys and sign-in | `~/.config/soundflow/` |
| Background service | `~/.config/systemd/user/soundflow.service` |

### Update

Download the new release and run its `install.sh` the same way. Your settings, models and
transcripts are kept.

Coming from 0.1.0: it installed the program inside `~/.local/share/soundflow/app`. After
the new version is running you can delete that `app` folder; leave the rest of
`~/.local/share/soundflow`, which holds your models and history.

### Uninstall

Remove the program but keep your models, settings and transcripts:

```bash
systemctl --user disable --now soundflow.service
rm -rf ~/.local/share/soundflow-app
rm -f ~/.local/bin/soundflow \
      ~/.local/share/applications/io.github.SayemAhmedShayeed.Soundflow.desktop \
      ~/.config/autostart/soundflow.desktop \
      ~/.config/systemd/user/soundflow.service
systemctl --user daemon-reload
```

From a source checkout, `./uninstall-linux.sh` does the same.

To remove everything as well, including downloaded models, local transcripts, settings and
API keys, also run the command below. Transcripts that have synced to your account come
back when you sign in again; anything not yet synced is lost.

```bash
rm -rf ~/.local/share/soundflow ~/.config/soundflow
```

## Build from source

Requirements:

- Python 3.11 to 3.14
- Linux (Windows builds must be made on Windows with `packaging/soundflow.spec` and the
  provided NSIS script)
- PortAudio and the Qt XCB libraries. On Ubuntu:

  ```bash
  sudo apt install python3-venv portaudio19-dev libxcb-cursor0
  ```

Set up and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
soundflow
```

On Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Demo mode records real microphone audio but returns a labelled fake result, so you can
check audio, shortcuts, the tray, exports and pasting without a model:

```bash
soundflow --demo
soundflow --demo --no-hotkeys   # if the desktop doesn't allow global shortcuts
```

`./run-soundflow.sh --demo` does the same from this checkout and also finds a local
`.vendor/python` test bundle if there is one.

### Build and install the app from your checkout

```bash
.venv/bin/pyinstaller --clean --noconfirm packaging/soundflow.spec
./install-linux.sh
```

The build goes to `dist/Soundflow/`; `install-linux.sh` installs it exactly as a release
does.

### Make a release

1. Set the version in `pyproject.toml` and `src/soundflow/__init__.py`.
2. Build with PyInstaller as above.
3. Put `dist/Soundflow/`, `install-linux.sh`, `uninstall-linux.sh` and `README.md` in a
   folder named `soundflow-<version>/`, and pack it as
   `soundflow-<version>-linux-x64.tar.gz`.
4. Upload that archive with `packaging/linux/release-install.sh` renamed to `install.sh`.

### Use your own or an offline model

For an existing CTranslate2/faster-whisper model folder, open **Preferences → Speech model**,
expand the advanced options and use **Use a model from a folder → Choose folder**, or set
`SOUNDFLOW_MODEL_PATH`. The folder must
contain `model.bin`, `config.json`, the tokenizer and the vocabulary. Soundflow never
deletes a model folder you chose yourself.

To ship a model inside an offline build, prepare it on a connected machine first:

```bash
python scripts/prepare_model.py --model small
```

This writes a SHA-256 manifest and places the model where the PyInstaller spec includes it.

## Audio and privacy behavior

- Audio is captured as 16 kHz, mono, signed 16-bit PCM.
- A lightweight local energy detector ends a phrase after 700 ms of silence by default.
- Completed phrases are sent to faster-whisper on a worker thread.
- Audio exists only in memory and is discarded after processing.
- Transcription stays local; audio is never sent to a network service.
- Saved transcripts (text only) are stored in the local history database and synced to the
  signed-in user's Supabase account. Row-level security limits each account to its own rows.
- Other network access occurs only for account sign-in, a model download, or AI Polish
  (Preferences → AI Polish) with the user's own Gemini or OpenRouter API key.
- There is no telemetry or automatic update behavior.

The first model load can take several seconds. Later phrases reuse the loaded model.

## Accounts and cloud sync (Supabase)

Soundflow requires signing in. The app ships with the project URL and publishable key in
`src/soundflow/cloud/config.py` (override with `SOUNDFLOW_SUPABASE_URL` /
`SOUNDFLOW_SUPABASE_KEY`). One-time project setup:

1. **Database.** In the Supabase dashboard open *SQL Editor*, paste
   `supabase/migrations/0001_soundflow_cloud.sql`, and run it. It creates `profiles` and
   `transcripts` with row-level security and a trigger that fills the profile on sign-up.
2. **Email sign-up.** *Authentication → Sign In / Providers → Email* is on by default. With
   "Confirm email" on, new users must click the emailed link before signing in. Set
   *Authentication → URL Configuration → Site URL* to a page you control so that link does
   not land on a dead `localhost:3000`.

Local data: the session (refresh token) is stored in `~/.config/soundflow/session.json`
with mode 600. History stays in `~/.local/share/soundflow/history.db`; transcripts saved
before accounts existed are attached to the first account that signs in on that machine.

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
│   ├── llm.py              optional OpenRouter transcript polish
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
