# Story Atlas

An offline storytelling workspace for worlds, chapters, events, characters, and their changing relationships. The current app uses React, Python, SQLite, and pywebview.

## Open the app

Double-click **Launch Story Atlas.cmd** in this folder.

It uses this checkout when the Python environment and built frontend are available, then the local preview package, then the installed preview. It never opens the older Tkinter app. Errors stay visible instead of silently switching versions. Arguments such as `--home` are forwarded.

For friends, copy the Setup EXE from **dist/installer** to a flash drive. Setup installs the app and creates a desktop icon. See the [offline installer guide](docs/OFFLINE_INSTALLER.md).

Stories and backups normally live in `%LOCALAPPDATA%\StoryAtlasPreview`, outside this repository. Legacy stories use a different format; keep them intact.

## Where things live

Ready-made [Frankenstein, Dracula, and Edgerunners examples](examples/saved-stories/README.md)
live in `examples/saved-stories`. Open them with the normal story file picker.

| Location | Purpose |
| --- | --- |
| `preview/` | Current React UI and frontend build |
| `preview_main.py` | Current native app entry point |
| `story_atlas/` | Python storage, logic, and legacy implementation |
| `installer/` | Setup definition and installation instructions |
| `dist/installer/` | Generated installer and checksum to distribute |
| `docs/` | Current plans, delivery notes, and architecture |
| `docs/legacy/` | Older Tkinter guides and design/research history |
| `tools/launchers/` | Explicit source, legacy, and browser-prototype launchers |
| `tests/`, `tools/` | Tests and developer utilities |
| `prototypes/` | Design reference and sample data; still used by the app/build |
| `project-snapshots/` | Preserved recovery archives |
| `build/`, `build-verification/` | Ignored build dependencies and test evidence |
| `data/` | Existing local data; preserved |

## Develop or rebuild

Create `.build-env` with Python 3.13 x64, install `requirements-preview.txt`, then run `npm ci` and `npm run build` inside `preview`. Use the root launcher afterward. Source-only launch is available in `tools/launchers/Launch Preview Source.cmd`.

Run `build_preview_installer.ps1` to build the offline installer; prerequisites are in the [build guide](docs/OFFLINE_INSTALLER.md). `build_windows.ps1` and `StoryAtlas.spec` remain for legacy Tkinter builds.

See [MVP delivery](docs/MVP_DELIVERY.md) for supported features and remaining gaps. The [legacy guide](docs/legacy/README.md) documents the older application only.
