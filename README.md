# Story Atlas

An offline desktop workspace for story events, characters, world references,
and relationships that change over a story's timeline. The current app uses
React, Python, SQLite, and pywebview.

## Choose how to run it

- **Windows, ready to use:** install the offline Setup EXE. Python, Node.js,
  and VS Code are not required. See [Windows installation](installer/README.txt).
- **Develop from source:** open this repository in VS Code or another editor,
  prepare the Python environment and frontend below, then run `preview_main.py`.
- **Mac:** use the [macOS source instructions](installer/README-MAC.md).
  There is no standalone Mac installer; native Mac validation is still pending.

**The bundled Windows release is 0.1.1, built from `d6376bc388169bfe636115be5ea2ef444ff875b8`.
It predates the current source.** `VERSION` identifies the 0.1.2 source
candidate; no matching new Windows installer has been published. Pulling source
changes does not update an installed app. The existing EXE, checksum, and `installer/release.json` remain
that older release until a replacement is built and verified. See
[release history and verification limits](docs/RELEASE_HISTORY.md).

## Install the Windows release

Run `installer/StoryAtlasPreview-0.1.1-Windows-x64-Offline-Setup.exe` on a Windows
10/11 x64 PC, then use the installed desktop or Start Menu shortcut. Setup
includes the app and Microsoft's offline WebView2 runtime. The EXE can be
shared directly on a flash drive.

To obtain the real installer through Git, use Git LFS:

```powershell
git lfs install
git clone --branch codex/repo-housekeeping https://github.com/vanderjt/dnd_relations_db.git
cd dnd_relations_db
git lfs pull
```

A small text file beginning `version https://git-lfs.github.com` is an LFS
pointer, not the installer. Downloading requires internet access; installation
is designed to work offline. Clean-machine/offline WebView2 verification remains
outstanding. See [Windows installation](installer/README.txt) for updates,
custom installation paths, uninstall, and reinstall.

## Run from source on Windows

Use Python 3.13, Node.js with npm, and WebView2. Run these commands in a
PowerShell terminal at the repository root, including VS Code's terminal:

```powershell
py -3.13 -m venv .build-env
.\.build-env\Scripts\python.exe -m pip install -r requirements-preview.txt
cd preview
npm ci
npm run build
cd ..
.\.build-env\Scripts\python.exe preview_main.py
```

In VS Code, select `.build-env\Scripts\python.exe` as the Python interpreter.
The direct command above always runs source. After frontend changes, run
`npm run build` in `preview` again. Repeat `npm ci` when the lockfile changes.

`Launch Story Atlas.cmd` prefers ready source, then a local frozen package,
then the registered installed app. It prints which mode it chose. Use an
installed shortcut when you specifically want the shipped release.

The [contributor guide](CONTRIBUTING.md) covers isolated development data,
checks, source updates, and repository conventions. Source setup downloads
dependencies; normal app use keeps stories and assets local.

## Stories and data

Start with **Create story**, **Try Greyhaven sample**, or **Open story**.
The editable [Frankenstein, Dracula, and Edgerunners examples](examples/saved-stories/README.md)
include their provenance and portrait credits. Opening a file edits that file;
copy an example first if you want to preserve the original.

Default stories and backups live outside the repository:

- Windows: `%LOCALAPPDATA%\StoryAtlasPreview`
- macOS: `~/Library/Application Support/StoryAtlasPreview`

Source and installed copies use the same default data root. For experiments,
pass `--home` with a disposable directory. Use **Back up story** before moving
or sharing work; **Restore backup as a copy** creates a separate working file.
Uninstalling the Windows app preserves its separate story data. Legacy `.db`
files are not imported. Read the [user guide](docs/USER_GUIDE.md) for details.

## Project guide

| Location | Purpose |
| --- | --- |
| `preview_main.py` | Native source entry point and restricted UI bridge |
| `preview/src/` | React UI and component styles |
| `preview/assets/` | Themes, styles, and artwork copied into frontend builds |
| `story_atlas/` | Serialized worker, SQLite storage, profile and relationship rules |
| `story_atlas/resources/` | Greyhaven sample and Windows icon |
| `examples/saved-stories/` | Three saved stories and portrait credits |
| `installer/` | Bundled Windows release, release metadata, Setup definition, manager |
| `tests/`, `tools/` | Unit checks, example checks, native and installer verification |

- [Contributing and development checks](CONTRIBUTING.md)
- [Architecture and data-safety rules](docs/ARCHITECTURE.md)
- [Windows build and release verification](docs/OFFLINE_INSTALLER.md)
- [Historical release evidence](docs/RELEASE_HISTORY.md)

Generated frontend output, environments, packaging output, and local test data
are ignored by Git. The old Tkinter app and browser prototypes are no longer
part of the supported source tree.
