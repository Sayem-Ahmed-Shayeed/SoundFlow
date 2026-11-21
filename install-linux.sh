#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_ID="io.github.SayemAhmedShayeed.Soundflow"
# From a source checkout the build is in dist/; in a release archive it sits
# next to this script.
SOURCE="$ROOT/dist/Soundflow"
[ -x "$SOURCE/Soundflow" ] || SOURCE="$ROOT/Soundflow"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
# Keep the program apart from $DATA_HOME/soundflow, which holds history.db and models.
INSTALL_DIR="$DATA_HOME/soundflow-app"
STAGING_DIR="$DATA_HOME/.soundflow-install-$$"
OLD_DIR="$DATA_HOME/.soundflow-previous-$$"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$DATA_HOME/applications"
DESKTOP_FILE="$APP_DIR/$APP_ID.desktop"
LEGACY_DESKTOP_FILE="$APP_DIR/soundflow.desktop"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
AUTOSTART_DIR="$CONFIG_HOME/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/soundflow.desktop"
SYSTEMD_DIR="$CONFIG_HOME/systemd/user"
SERVICE_FILE="$SYSTEMD_DIR/soundflow.service"

cleanup() {
    rm -rf "$STAGING_DIR"
}
trap cleanup EXIT HUP INT TERM

if [ ! -x "$SOURCE/Soundflow" ]; then
    echo "Soundflow's packaged build was not found at:"
    echo "  $SOURCE/Soundflow"
    echo "Build it first using the instructions in README.md."
    exit 1
fi

echo "Installing Soundflow to $INSTALL_DIR ..."
mkdir -p "$DATA_HOME" "$BIN_DIR" "$APP_DIR" "$AUTOSTART_DIR" "$SYSTEMD_DIR"
rm -rf "$STAGING_DIR" "$OLD_DIR"
mkdir -p "$STAGING_DIR"
cp -a "$SOURCE/." "$STAGING_DIR/"

if [ -d "$INSTALL_DIR" ]; then
    mv "$INSTALL_DIR" "$OLD_DIR"
fi
if ! mv "$STAGING_DIR" "$INSTALL_DIR"; then
    if [ -d "$OLD_DIR" ]; then
        mv "$OLD_DIR" "$INSTALL_DIR"
    fi
    echo "Installation failed; the previous version was restored."
    exit 1
fi
rm -rf "$OLD_DIR"
ln -sf "$INSTALL_DIR/Soundflow" "$BIN_DIR/soundflow"
rm -f "$LEGACY_DESKTOP_FILE"

ICON_FILE="$INSTALL_DIR/_internal/soundflow/assets/icons/soundflow.svg"
[ -f "$ICON_FILE" ] || ICON_FILE="audio-input-microphone"

{
    echo "[Desktop Entry]"
    echo "Type=Application"
    echo "Name=Soundflow"
    echo "Comment=Private offline dictation"
    echo "Exec=$INSTALL_DIR/Soundflow"
    echo "Icon=$ICON_FILE"
    echo "Categories=AudioVideo;Audio;Utility;Accessibility;"
    echo "Terminal=false"
    echo "StartupNotify=true"
    echo "StartupWMClass=soundflow"
} > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

{
    echo "[Desktop Entry]"
    echo "Type=Application"
    echo "Name=Soundflow Background"
    echo "Comment=Keep private push-to-talk dictation ready"
    echo "Exec=$INSTALL_DIR/Soundflow --background"
    echo "Icon=$ICON_FILE"
    echo "Terminal=false"
    echo "X-GNOME-Autostart-enabled=true"
} > "$AUTOSTART_FILE"
chmod +x "$AUTOSTART_FILE"

{
    echo "[Unit]"
    echo "Description=Soundflow background dictation"
    echo "After=graphical-session.target"
    echo
    echo "[Service]"
    echo "Type=simple"
    echo "ExecStart=$INSTALL_DIR/Soundflow --background"
    echo "Restart=on-failure"
    echo "RestartSec=2"
    echo
    echo "[Install]"
    echo "WantedBy=default.target"
} > "$SERVICE_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable --now soundflow.service
    rm -f "$AUTOSTART_FILE"
fi

echo
echo "Soundflow is installed."
echo "Open it from your application menu, or run:"
echo "  $BIN_DIR/soundflow"
echo
case ":${PATH:-}:" in
    *":$BIN_DIR:"*) ;;
    *) echo "Note: add $BIN_DIR to PATH to use the short 'soundflow' command." ;;
esac
