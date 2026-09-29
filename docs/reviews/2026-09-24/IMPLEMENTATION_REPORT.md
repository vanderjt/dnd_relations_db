# Story Atlas plan implementation and release verification

24 September 2026 · [Work plan](WORK_PLAN_FOR_SOL.md) · [Original review](REVIEW.md)

**Superseded release:** Follow-up senior-review fixes and rebuilt artifact hashes
are recorded in [SENIOR_FIXES.md](SENIOR_FIXES.md). The results and hashes below
describe the original Sol build and are retained for traceability.

## Completion checklist

| Task | Status | Evidence |
|---|---|---|
| 1. Quick-event close | Complete in source | Back, Escape, and window close use the same dirty Save/Discard/Cancel path. Interaction tests cover focus, failed save, and the pending relationship change. |
| 2. Build identity and launchers | Complete in source and package | About shows version, build fingerprint, runtime mode, supported schema, and active schema. Source and packaged launchers are explicit. Build metadata is frozen during packaging. |
| 3. Relationships from events | Complete in source | Separate start/change actions keep the event tab and origin; beginning-event selection is explicit; saved ID survives batch-entry reset. Widget tests cover return, failure, and exact history inspection. |
| 4. Chapter outline | Complete in source | ID-based outline includes All, empty chapters, and Unassigned; event moves offer a destination route; chapter moves show a read-only preview with stale checks and atomic rollback. |
| 5. Global search | Complete in source | Typed chapter, event, and baseline/dated relationship-history hits have stable keys and exact navigation. Search excludes Trash and drafts; UI tests cover ended states and story scoping. |
| 6. Goals | Complete in source | Cast goals and modal participant profile/goals views show committed, verbatim text without changing an event draft. |
| 7. Workflow and appearance | Automated pass complete; physical review outstanding | Named actions and state labels were checked; graph inspector width persists. Automated geometry/interaction checks cover 900×600, 1280×720, both themes, large text, and simulated scaling. |
| 8. Extraction and scale | Complete in source | Event editor and relationship-change chooser moved into focused modules. The deterministic scale benchmark is recorded below; no measured bottleneck justified a renderer or query rewrite. |
| 9. Final Windows package | Locally package-verified; clean-machine gate outstanding | Full source suite, locked build, and isolated packaged smoke pass. ZIP and executable hashes are below. No package was published. |

The original workflow map remains `user-workflow-map.png`/`.svg`. The updated generator produced [current PNG](user-workflow-map-current.png) and [current SVG](user-workflow-map-current.svg); the PNG was visually inspected.

## Commands and results

Run from `C:\Users\Jonathan\Documents\dnd_relations_db`:

```powershell
.\.build-env\Scripts\python.exe -m unittest discover -s tests -q
.\build_windows.ps1 -Python 'C:\ProgramData\anaconda3\python.exe'
.\tools\smoke_windows.ps1
```

The final suite ran **137 tests in 41.100 seconds: OK**. The build script ran the full suite again before freezing metadata and packaging with the locked dependencies. The packaged smoke reported `ok=true`, `frozen=true`, version `0.9.0`, schema `8`, Tcl/Tk `8.6.15`, and fingerprint `c93289ee5d8182b3e751ab0d04d4d3d15af375284d76a64aecc73e5a292bc805`. A further packaged `--self-test` with spaces in both the report and data paths exited 0 with the same fingerprint. Source launcher and source self-test with spaces/forwarded arguments were also checked. The source suite's existing 100-character/300-relationship graph benchmark ran successfully (initial 1.403 s, note refresh 0.018 s, direct focus 0.036 s on the final test run).

The isolated packaged smoke exercised first-launch creation and reopening, separate sample stories, full app startup, About identity, Goals, Chapters, contextual relationship entry and batch reset, TkAgg/fonts and Tcl/Tk resources, historical PNG/JSON snapshot export, icon and portrait assets, SQLite backup/restore, settings persistence, disposable version-7 migration with backup, version-8 reopen, and external writable data. Its machine was Windows 11 x64 build 26200 with Python 3.13.9 used to *build* the package. The smoke runner removed Python/Conda/Tcl overrides and restricted `PATH` to Windows system directories; that remains a local packaged check.

The first package attempt exposed a bundled Tcl path initialization problem. The relative Tcl/Tk paths are now set before importing Tkinter, and relative command-line file paths are resolved before changing to the executable directory. The affected checks and package build were rerun; only the successful final package hashes below are release candidates.

## Release artifacts

| Artifact | SHA-256 |
|---|---|
| `dist/StoryAtlas/StoryAtlas.exe` | `BCE549C7FEBA32E5B4A6276ED8F0F316987F58634744DDFEFE8DC99E19B14367` |
| `dist/StoryAtlas-Windows-x64.zip` | `66E8BAFCB97795E8D920691FE3DE8AF35C53372F4438007FD535D80FE5A24DEA` |

The ZIP is 42,792,246 bytes and contains the full `StoryAtlas` directory. The accompanying `dist/StoryAtlas-Windows-x64.zip.sha256` records its digest. Package build identity is version `0.9.0`, schema `8`, fingerprint `c93289ee5d8182b3e751ab0d04d4d3d15af375284d76a64aecc73e5a292bc805`. The final smoke report is `build-verification/packaged-smoke.json`. The separate spaces-path report is `build-verification/packaged smoke with spaces.json`.

## Scale measurement

`tools/benchmark_story_scale.py` used seed `24092026` and disposable data: 30 chapters, 300 events, 100 characters, 300 relationships, and 1,200 history states. One warm-up and five timed runs were recorded on Windows 11 x64, Python 3.13.9, AMD64 Family 26 Model 68 (12 logical CPUs). Chapter display, switching, and history opening include Tk widget/layout work; search and preview are storage-only.

| Operation | Median | Slowest |
|---|---:|---:|
| Initial chapter display | 0.0080 s | 0.0081 s |
| Chapter switch | 0.0113 s | 0.0123 s |
| Search | 0.0124 s | 0.0126 s |
| Exact history open | 0.0113 s | 0.0123 s |
| Chapter move preview | 0.0059 s | 0.0060 s |

Raw measurements and environment details are in `build-verification/scale-benchmark-2026-09-24.json`. These are observations on this machine, not performance guarantees. There was no optimization requiring a before/after comparison.

## Data and remaining validation

Database schema remains **8**; this work added no migration. Existing user stories, preferences, and sample data were not changed for verification. Tests and packaged smoke used disposable databases and isolated data roots. Source changes were packaged only in Task 9. The built ZIP has not been distributed.

The clean-machine gate is **outstanding**: no second Windows machine without Python/Anaconda was available. Before distribution, verify under a standard non-admin account with a read-only installation folder, Windows display scaling and Unicode paths, and the intended security-software/SmartScreen environment. Physical Windows DPI and manual native-window appearance were not verified by simulated scaling or widget tests. The review's observed writer tasks—scene and relationship creation/change, chapter move, historical retrieval, and unsaved-goal recovery—also remain outstanding; no task-time baseline or user-study result is claimed.
