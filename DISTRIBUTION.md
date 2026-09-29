> 0.19.0 adds curated HAS artwork, Illustrated/Minimal appearance, compact navigation and responsive workspaces. Imported portraits remain visible in Minimal. Help → Artwork credits includes the original licenses. Schema 13 and portable format 9 are unchanged.

> 0.18.0 advances immediately from searchable starting-character cards to connections. A persistent source card and Change character action preserve context, entered details, and compatible targets. Keyboard activation, graph selection, and recovered drafts share this flow.

> 0.17.0 replaces Simple connection entry with Starting character → Other characters → Relationship → Review. Direct choices, consistent graph clicks, early validation, and preserved Back navigation reduce selection mistakes.

> 0.16.0 makes the wheel scroll forms without changing dropdown values and adds a saved Support / Conflict / Personal / Other category to connection creation and editing.

> 0.15.0 adds Ctrl+Z undo and Ctrl+Y redo. Text fields undo local typing; the workspace undoes saved story changes and node positioning. History is local to the current open-story session.

> 0.14.2 adds Delete beside Connect in the character info panel. It moves the character and attached connections to Trash; restore them from Settings → Recovery.

> 0.14.1 simplifies graph labels: no numeric IDs beside names or relationships, and no redundant Dot/Link prefixes in the plotted legend.

> Try **Story → Sample stories → The modern prometheus…** for a complete Frankenstein example,
> or **Story → Sample stories → Expanded Greyhaven…** for the updated original.
> Each creates a fresh local story. Use **View → Legend · dots & links** and
> **More → Saved graph views…** to explore colors and guided scenes.

> Latest source release: **0.19.0**, schema **13**, portable format **9**. The GUI overhaul release report records package verification separately; historical hashes below do not identify this release.
> [GUI overhaul review records](docs/reviews/gui-overhaul/) contain current staged verification. [Combined legend and worked examples release](docs/reviews/2026-09-24/EXAMPLES_REPORT.md) and package identities below are historical.

> Historical source release: Story Atlas 0.11.0, schema 10, export format 6.
> See [Simple rework completion report](docs/reviews/2026-09-24/SIMPLE_REWORK_COMPLETION_REPORT.md)
> for the replacement package, verification results and limitations. Earlier hashes below are historical.

# Story Atlas for Windows

This build targets Windows x64 using CPython 3.13.9 and PyInstaller. It is a
standalone folder, not an installer. End users do not need Python or Anaconda.
Distribute the entire `dist/StoryAtlas` folder, including `_internal`; moving only
the EXE will not work. Double-click `StoryAtlas.exe`. The source checkout also
includes `Launch Story Atlas.cmd` for the packaged build only. Developers use
`Launch Story Atlas Source.cmd`, which runs `.build-env` or the existing
`story-atlas` Conda environment and never starts a packaged executable. Both
launchers forward command-line arguments. Source mode may also be run directly
with `python main.py`.
The build also creates `dist/StoryAtlas-Windows-x64.zip` and its SHA-256 checksum.
Extract the complete archive before launching; do not run the EXE inside the ZIP.

## Rebuild

Use Windows x64 and CPython **3.13.9** with Tcl/Tk (the python.org installer or
the tested Anaconda interpreter). Keep `environment.yml` for normal development.
Run from PowerShell:

```powershell
.\build_windows.ps1 -Python 'C:\path\to\python.exe'
.\tools\smoke_windows.ps1
```

The script creates `.build-env`, installs all versions in
`requirements-build.lock.txt`, generates the original icon, runs tests, and builds
`StoryAtlas.spec`. No user databases or local settings are bundled. The spec
selects the TkAgg backend and uses PyInstaller's Tcl/Tk and Matplotlib hooks;
resource directories and dependency metadata/licenses are included explicitly.
See [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html)
and [bundling behavior](https://pyinstaller.org/en/stable/operating-mode.html).

`requirements-build.txt` records the direct inputs. To intentionally refresh the
lock, install those inputs in a fresh build environment, run all checks, then save
`python -m pip freeze --all` to `requirements-build.lock.txt`. The lock reproduces
dependency versions; it does not promise byte-identical signed executables across
machines, toolchain updates, or timestamps. Build on Windows; this is not a
cross-platform build configuration. PowerShell script policies may require your
organization's normal script approval; no policy changes are made by the scripts.

## User data and upgrades

Default storage is `%LOCALAPPDATA%\StoryAtlas`: `settings.json`, `stories`, and
`cache\matplotlib`. Backups and managed portrait folders live beside each story.
Explicitly selected stories may live elsewhere, but the packaged app rejects
paths inside its own installation folder (including `--data-dir` overrides).
Use `--data-dir "D:\Story Atlas data"` or `STORY_ATLAS_HOME` for a portable data
location outside the program folder. Do not put data in `dist`, `_internal`, or
the folder you replace during upgrades.

To upgrade, close the app, back up stories, and replace the application folder.
User data remains outside it. SQLite migrations make a pre-migration backup before
schema changes. There is no automatic updater or installer/uninstaller. Old source
checkout databases are not moved or deleted: choose Open story to continue them.

## Verification

Use **About** in the running app to read its application version, source
fingerprint, runtime mode, supported schema, and active story schema. The
packaging script freezes the source fingerprint after tests and before
PyInstaller runs; it does not use the clock or require Git. The 24 September
2026 source was rebuilt and locally smoke-tested. See the implementation report
in `docs/reviews/2026-09-24/` for artifact hashes and exact evidence.

Release verification uses a new disposable `--data-dir` outside the installation
folder for each run. Before shipping, run the full suite, build with the locked
toolchain, and run `tools/smoke_windows.ps1`. Check a clean first launch, creation
of a new story and a sample story in separate paths, reopening both, a version-7
database upgrade with its pre-migration backup, and opening a version-8 database.
Confirm About reports the packaged fingerprint and the expected active schema;
exercise Goals, Chapters, contextual relationship entry, Tk and Matplotlib assets,
snapshot export, backup restore, and settings persistence. Record the executable
and ZIP SHA-256 hashes. A separate Windows machine without Python or Anaconda is
a distinct gate; local smoke tests do not satisfy it.

`tools/smoke_windows.ps1` launches the frozen executable with Python/Conda/Tcl
environment overrides removed and PATH limited to Windows system directories.
It checks first-launch creation and reopening, separate sample stories, About,
Goals, Chapters, contextual relationship entry and batch reset, historical graph
snapshot export, TkAgg rendering/fonts, Tcl/Tk resources, window icon, managed
portraits, backups/restoration, settings persistence, version-7 migration and
pre-migration backup, version-8 opening, and external writable paths. The
disposable test stories are removed; the JSON report and cache remain in
`build-verification`. The local run passed on Windows 11 x64 (build 26200) with
Tcl/Tk 8.6.15. See `docs/reviews/2026-09-24/UX_IMPLEMENTATION_REPORT.md` for current source and package verification. Geometry checks cover
900×600 and 1280×720, both themes, large text, and simulated scaling.

A stripped environment on the development PC is not a clean Windows installation.
Native visual inspection covered dark/light event workflows on this development
machine. No second/clean machine was tested; Tk geometry checks do not verify
actual Windows per-monitor DPI behavior.
Release validation must still cover a machine with no
Python/Anaconda, a standard non-admin account, read-only installation folder,
Windows display scaling, Unicode paths, and security software/SmartScreen.
The EXE is unsigned; no code-signing certificate, installer, automatic updates,
or macOS/Linux packages are supplied.

## Simple mode release (0.10.0)

Schema 9 preserves legacy visibility, adds introduction-event references and
narrative roles, and backs up before migration. Complete JSON exports are version 5.
The packaged self-test also exercises Simple provisional save, one-to-many batch
review/commit/reset, and planned cast without active future connections.
See docs/reviews/2026-09-24/SIMPLE_MODE_COMPLETION_REPORT.md for this release's
validation and limitations; earlier package hashes above are historical.
