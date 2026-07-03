#!/bin/sh
set -eu

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_ID="io.github.SayemAhmedShayeed.Soundflow"
INSTALL_DIR="$DATA_HOME/soundflow"
BIN_PATH="$HOME/.local/bin/soundflow"
DESKTOP_FILE="$DATA_HOME/applications/$APP_ID.desktop"
LEGACY_DESKTOP_FILE="$DATA_HOME/applications/soundflow.desktop"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
AUTOSTART_FILE="$CONFIG_HOME/autostart/soundflow.desktop"
SERVICE_FILE="$CONFIG_HOME/systemd/user/soundflow.service"

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

echo "Soundflow was uninstalled. User settings and saved transcripts were preserved."
