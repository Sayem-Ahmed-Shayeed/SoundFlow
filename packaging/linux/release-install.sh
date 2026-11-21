#!/bin/sh
# Soundflow release installer: put this next to the downloaded
# soundflow-<version>-linux-x64.tar.gz and run ./install.sh
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ARCHIVE="$(ls "$HERE"/soundflow-*-linux-x64.tar.gz 2>/dev/null | sort -V | tail -n 1)"
if [ -z "$ARCHIVE" ]; then
    echo "Put soundflow-<version>-linux-x64.tar.gz in the same folder as this script."
    exit 1
fi
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
echo "Unpacking $(basename "$ARCHIVE") ..."
tar -xzf "$ARCHIVE" -C "$WORK"
sh "$WORK"/soundflow-*/install-linux.sh
echo "On first launch, choose a speech model in Preferences > Speech model."
