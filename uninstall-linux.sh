#!/bin/sh
set -eu

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_ID="io.github.SayemAhmedShayeed.Soundflow"
# Keep the program apart from $DATA_HOME/soundflow, which holds history.db and models.
INSTALL_DIR="$DATA_HOME/soundflow-app"
BIN_PATH="$HOME/.local/bin/soundflow"
DESKTOP_FILE="$DATA_HOME/applications/$APP_ID.desktop"
LEGACY_DESKTOP_FILE="$DATA_HOME/applications/soundflow.desktop"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
AUTOSTART_FILE="$CONFIG_HOME/autostart/soundflow.desktop"
SERVICE_FILE="$CONFIG_HOME/systemd/user/soundflow.service"

# --everything also deletes downloaded models, local transcripts, settings,
# API keys and the saved sign-in.
EVERYTHING=0
case "${1:-}" in
    --everything) EVERYTHING=1 ;;
    "") ;;
    *) echo "Usage: $0 [--everything]"; exit 2 ;;
esac

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user disable --now soundflow.service >/dev/null 2>&1 || true
fi

rm -rf "$INSTALL_DIR"
rm -f \
    "$BIN_PATH" \
    "$DESKTOP_FILE" \
    "$LEGACY_DESKTOP_FILE" \
    "$AUTOSTART_FILE" \
    "$SERVICE_FILE"

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user daemon-reload
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi

if [ "$EVERYTHING" = 1 ]; then
    rm -rf "$DATA_HOME/soundflow" "$CONFIG_HOME/soundflow"
    echo "Soundflow was uninstalled, with its models, transcripts and settings."
    echo "Transcripts synced to your account come back when you sign in again."
else
    echo "Soundflow was uninstalled. Models, settings and transcripts were kept in"
    echo "  $DATA_HOME/soundflow and $CONFIG_HOME/soundflow"
    echo "Run it again with --everything to remove those too."
fi
