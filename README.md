# macked

Browse the software update list from macked.app in a sortable table.

## Run

- Double-click `Macked.command`, or
- `python3 macked.py` (requires Python 3 with `requests`, `beautifulsoup4`, `pillow` — see `requirements.txt`)

## Features

- Fetch the latest updates across multiple pages (configurable page count and delay)
- Sortable columns: name, version, description, updated time, comments, views, likes, activation method, link
- Click a link in the Link column to open the app's page; Ctrl+click a row to favorite it
- Green highlight for updates in the last 24 hours, blue for favorites; optional 24-hour-only filter
- Remembers window size, column widths, and favorites between runs

## Build a .app bundle

Run `python3 build_app.py` (requires `pyinstaller`).
