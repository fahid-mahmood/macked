#!/bin/bash
# Double-clickable launcher for the Macked app.
# Creates the virtualenv on first run, installs dependencies, then starts the app.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -d .venv ]; then
    python3 -m venv .venv || { osascript -e 'display notification "Failed to create virtualenv. Is Python installed?" with title "Macked"'; exit 1; }
    .venv/bin/pip install --quiet -r requirements.txt
fi

exec .venv/bin/python macked.py
