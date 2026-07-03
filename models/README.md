# Offline model location

Soundflow never downloads a speech model automatically.

Place a converted faster-whisper model in:

- Linux: `~/.local/share/soundflow/models/faster-whisper-small/`
- Windows: `%LOCALAPPDATA%\Soundflow\models\faster-whisper-small\`

Alternatively, choose any local model directory in **Settings → Recognition** or set
`SOUNDFLOW_MODEL_PATH`.

The selected directory should be a complete CTranslate2/faster-whisper model containing files
such as `model.bin`, `config.json`, `tokenizer.json`, and `vocabulary.*`.

For an entirely offline installation, copy that directory from another machine or include it in
the installer. Soundflow passes `local_files_only=True` and will not fetch missing files.

