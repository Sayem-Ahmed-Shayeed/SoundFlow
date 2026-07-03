#!/bin/sh
set -eu

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
INSTALL_DIR="$DATA_HOME/soundflow"
BIN_PATH="$HOME/.local/bin/soundflow"
DESKTOP_FILE="$DATA_HOME/applications/soundflow.desktop"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
AUTOSTART_FILE="$CONFIG_HOME/autostart/soundflow.desktop"

rm -rf "$INSTALL_DIR"
rm -f "$BIN_PATH" "$DESKTOP_FILE" "$AUTOSTART_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi

echo "Soundflow was uninstalled. User settings and saved transcripts were preserved."
