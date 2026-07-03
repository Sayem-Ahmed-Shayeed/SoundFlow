#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -d "$ROOT/.vendor/python" ]; then
    export PYTHONPATH="$ROOT/.vendor/python:$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
else
    export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
fi
PORTAUDIO="$ROOT/.vendor/portaudio/usr/lib/x86_64-linux-gnu"
if [ -d "$PORTAUDIO" ]; then
    export LD_LIBRARY_PATH="$PORTAUDIO${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
exec python3 -m soundflow "$@"
