# GUI overhaul release verification

Status: implemented, independently reviewed, locally validated, and integrated
through [PR #4](https://github.com/vanderjt/dnd_relations_db/pull/4) into
`gui_overhaul`. Merge `d73936ba6913ecd7e8f669435fa48b46d301d6fc` was pulled locally;
the post-pull source identity still matches the verified package.

Story Atlas **0.19.0** source identity:
`98bb3cce5bcbfee253c0ebcc7ea91b2a68e345a64057115cebdbb0376f138573`.

## Scope and recovery

This release implements the curated artwork, shared components, navigation,
core workspaces and supporting-screen portions of the asset visual roadmap.
Map editing, inventory records, user-authored covers, audio and alternate retro
themes remain separate product work. Database schema 13 and export format 9
are unchanged.

Integration is into `gui_overhaul`; local `main` remains at `7f84251`.
The original project archive and its restore instructions remain under
`project-snapshots/StoryAtlas-0.18.0-before-visual-redesign-20260928-201838`.

## Validation environment and method

- Windows 11 build 26200; Python 3.13.9 x64 in the existing `.build-env`.
- All 19 installed build-package versions match `requirements-build.lock.txt`.
- GUI tests, benchmarks and image capture run sequentially with disposable
  stories/settings. No existing user stories are used as test fixtures.
- Windows screenshots capture the owned Tk window directly. Screenshot
  inspection supplements geometry checks and callback-error monitoring.
- GUI performance uses five measurements after one warm-up, 100 characters,
  300 relationships, and cases with zero or 100 distinct managed portraits.
  The comparison source is extracted from unchanged local `main`.
- Memory figures are whole-process Windows working-set/private-byte snapshots
  after warmed operations, not memory attributable to the artwork. Allocator
  retention across repeated roots and ordered cases limits interpretation.

## Explicit limits

Actual Windows 100%, 125%, 150% and 200% scaling across physical displays,
mixed-monitor movement, a separate clean-machine installation, and independent
representative-user usability sessions have not been performed. Local package
smoke tests and simulated Tk scaling cannot establish those results. Contrast
checks concern the named design pairs, not complete accessibility conformance.

## Functional and contrast results

The independent full suite passed **254 tests in 159.856 seconds**, with no
skips or failures. Log: `build-verification/gui-stage4-full-tests.log`.
That run identifies source `de31b721afa7a8eab99c4b8e14de113c8ea482af4a1a47bf81f92be744542d8f`.
Subsequent screenshot review found one clipped empty-graph instruction. Its
two-line literal was shortened, independently reviewed, and checked by a new
300×180/16pt rendered-text boundary regression. All **seven supporting-screen
tests passed in 2.427 seconds** after that correction. This is not represented
as a 255-test full-suite run.

All **66 audited palette pairs** meet the defined targets. Minimum text contrast
is **4.752:1** (target 4.5); minimum audited boundary/outer-focus contrast is
**3.062:1** (target 3). Evidence: `build-verification/gui-overhaul/contrast-final.json`.

## Packaged Windows build

The existing locked environment built `StoryAtlas.spec` successfully with
PyInstaller in 23.8 seconds after `tools/freeze_build_metadata.py`. Commands:

```powershell
.build-env/Scripts/python.exe tools/freeze_build_metadata.py
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) 'build/pyinstaller-cache'
.build-env/Scripts/python.exe -m PyInstaller --noconfirm --clean StoryAtlas.spec
./tools/smoke_windows.ps1
```

The smoke script runs the executable with isolated test data and removes
Python/Conda/Tcl environment variables and development PATH entries. Result:
**ok=true, frozen=true, version 0.19.0, schema 13**, with the exact source identity
above. All 37 recorded checks passed, including bundled artwork hashes/licenses,
real icon/building Tk images, Illustrated/Minimal persistence, retained user
portraits, first launch, historical exports, drafts, backup/restore and undo/redo.
Reports: `build-verification/packaged-smoke.json` and
`build-verification/gui-overhaul/pyinstaller-final.log`.

The distribution includes the current launcher and Windows instructions. ZIP
inspection found 1,365 entries, all 30 UI PNGs, both UI license texts, matching
build metadata, and no CRC error.

| Artifact | SHA-256 |
|---|---|
| `dist/StoryAtlas-Windows-x64.zip` | `F95A48978942264986A29E2DB04CFB1D81546D129DA56DA8DECC123D886EAB27` |
| `dist/StoryAtlas/StoryAtlas.exe` | `D56DE77C06C6521165DA8D4B77FE3571A4C8A1BE78950DB54BA34BDF6721CCA7` |

Distribute the full ZIP/folder; the EXE depends on its `_internal` directory.
This is local isolated-environment verification, not a clean-machine result.

## Final visual review

Two agents independently reviewed the final **116 screenshots**, all with the
source identity above and no callback errors:

- `release-final-20260929-074212`: 40 core workspace cases and 36 supporting
  dialogs/true-empty cases, across both themes and supported window sizes.
- `release-text-9-20260929-074410`, `release-text-11-20260929-074415`,
  `release-text-12-20260929-074420`, `release-text-13-20260929-074425`,
  `release-text-14-20260929-074430`, `release-text-15-20260929-074436`:
  24 additional minimum-window font-size spot checks. Combined with the main
  10/16pt matrix, these cover every supported text size.
- `release-minimal-20260929-074441`: 16 Minimal-mode cases, including imported
  portrait overviews/editors in both modes and themes.

These directories are under `build-verification/gui-overhaul`. All show valid
owned-window captures. Selected planned cast, historical timeline/graph scope,
filtered-empty state, validation feedback and imported portraits remain coherent.
Minimum-size support actions remain visible; longer content uses scrolling.
The empty-graph text correction is visually confirmed. See the independent
support and final visual review reports for details.

## Performance investigation

Initial timing appeared to show first paint rising from about 0.33s to 1s.
Profiling established that the old revision had drawn only an empty canvas at
that point; the overhaul had already rendered the populated graph. The benchmark
now records both initial-window timing and comparable **first content paint**,
explicitly ensuring and asserting all 100 nodes and 300 edges before stopping
the latter timer. No application change was made to chase unequal measurements.
Profiles and original timing reports are retained in the evidence directory.

Comparable medians in milliseconds (five measurements after warm-up):

| Operation | No portraits: main → overhaul | 100 portraits: main → overhaul |
|---|---:|---:|
| First populated content | 650 → 994 (+53%) | 658 → 1,072 (+63%) |
| Mode round trip | 1,646 → 1,578 (−4%) | 1,668 → 1,752 (+5%) |
| Theme round trip | 688 → 850 (+24%) | 709 → 820 (+16%) |
| Graph refresh | 335 → 316 (−6%) | 312 → 326 (+5%) |

The startup and theme increases exceed the provisional 10% investigation
threshold and are **recorded tradeoffs, not parity claims**. Startup profiles
show the same graph-building count and similar graph-construction time, but
more Matplotlib path rasterization while the new layout settles. Populated
startup remains approximately one second on this machine. A theme round trip
adds 111–162ms, or roughly 55–81ms per change; live decoration and layout refresh
perform additional presentation work. Mode switches and graph refresh remain
within 6%. No late event-scheduling rewrite was made at the expense of the
verified first-map, minimum-size and historical-scope behavior.

Whole-process working-set snapshots rose from 209.4 to 219.9MB without portraits
and 303.6 to 315.3MB with portraits. Private-byte snapshots were 584.3 → 593.8MB
and 679.6 → 690.9MB respectively (decimal MB). These include repeated Tk roots
and allocator retention and are not estimates of asset memory. Observed UI
cache occupancy was 26/64 and 24/64; the portrait-row cache held 100/128 entries.
No callback failures or cache-bound assertion failures occurred.

The separate 30-chapter/300-event/1,200-history-state benchmark recorded medians
of 5.84ms for chapter display, 9.97ms for chapter switch, 13.73ms for search,
18.42ms for exact history and 6.30ms for move preview. Relative increases in
display/switch/history correspond to approximately 1.1/1.2/2.2ms; search and
preview were slightly faster. All remained below 20ms in these local samples.

Evidence: `performance-main.json`, `performance-overhaul.json`,
`performance-comparison.json`, `content-main.txt`, `content-overhaul.txt` and
`scale-overhaul.json`, under `build-verification/gui-overhaul`. This is a local
repeated comparison, not a general hardware performance guarantee.
