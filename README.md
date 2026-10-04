# Story Atlas

An offline workspace for story events, characters, world references, and changing
relationships. The current app uses React, Python, SQLite, and pywebview.

## Install on Windows

Install Git LFS once, then clone the housekeeping branch:

```powershell
git lfs install
git clone --branch codex/repo-housekeeping https://github.com/vanderjt/dnd_relations_db.git
cd dnd_relations_db
git lfs pull
```

Run **installer/StoryAtlasPreview-0.1.1-Windows-x64-Offline-Setup.exe** on Windows
10/11 x64. It includes the app and offline WebView2 runtime; Python and Node.js
are not needed. Open the installed desktop or Start Menu shortcut afterward.
The Setup EXE can also be shared directly without Git or Git LFS.

To update, close the app, pull the repository and LFS files, then double-click
**installer/Manage Story Atlas.cmd** and choose **Install/update**. The same menu
can uninstall or reinstall while preserving stories and backups. Installed
copies only gain new features when a new installer is built and published.
See [Windows installation instructions](installer/README.txt).

## Run from source

Install Python 3.13 (development used 3.13.9) and Node.js LTS. Mac users can
skip the Windows installer download when cloning:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --branch codex/repo-housekeeping https://github.com/vanderjt/dnd_relations_db.git
cd dnd_relations_db
bash "Launch Story Atlas.command"
```

The Mac launcher creates its local environment, installs dependencies, builds
changed frontend assets, and runs `preview_main.py`. See [Mac instructions](installer/README-MAC.md)
for direct Python launch and troubleshooting. Native Mac testing is pending.

On Windows, install WebView2 if needed, then run in PowerShell:

```powershell
py -3.13 -m venv .build-env
.\.build-env\Scripts\python.exe -m pip install -r requirements-preview.txt
cd preview
npm ci
npm run build
cd ..
.\.build-env\Scripts\python.exe preview_main.py
```

**Launch Story Atlas.cmd** uses source when its environment and built frontend
exist, otherwise a local packaged app or the installed copy. It reports which
mode it launches. After source UI changes, run `npm run build` in `preview`.

## Use the app

See the [user guide](docs/USER_GUIDE.md). Ready-made
[Frankenstein, Dracula, and Edgerunners stories](examples/saved-stories/README.md)
are included. Greyhaven is available from the welcome screen.

Stories and backups normally live outside the repository:
`%LOCALAPPDATA%\StoryAtlasPreview` on Windows and
`~/Library/Application Support/StoryAtlasPreview` on Mac. Use the app's backup
command to transfer stories. Uninstalling the Windows app preserves these files.

## Repository layout

| Location | Purpose |
| --- | --- |
| `preview_main.py` | Native source entry point |
| `preview/src/` | React UI |
| `preview/assets/` | Current styles, themes, and artwork |
| `story_atlas/` | Current SQLite storage, worker, profile resolution, and relationship validation |
| `story_atlas/resources/` | Greyhaven sample and Windows icon |
| `examples/saved-stories/` | Supported example stories and portrait credits |
| `installer/` | Windows release, checksum, setup definition, manager, and platform instructions |
| `docs/` | User guide and installer build instructions |
| `tests/`, `tools/` | Current app checks and release verification |

Generated frontend files, Python environments, build dependencies, packaging
output, verification data, and local story data are ignored by Git. Old Tkinter
and browser prototype implementations have been removed from this branch.

## Verify and build a release

```powershell
.\.build-env\Scripts\python.exe -m unittest discover -s tests -q
.\.build-env\Scripts\python.exe tools/verify_examples.py
```

For Windows packaging, also install `requirements-build.lock.txt`, prepare Inno
Setup and the signed offline WebView2 installer, then run
`build_preview_installer.ps1`. See the [installer build guide](docs/OFFLINE_INSTALLER.md).
The ready-to-run 0.1.1 release remains usable independently of the source cleanup.
