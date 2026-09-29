# Story Atlas independent UX review: corrective report

Date: 2026-09-24. Scope: three findings in ASTRA_UX_REVIEW.md. No schema change, unrelated features, or workflow redesign. No applicable AGENTS.md was found in the workspace or its ancestors.

## Reproduction before edits

Ran the supplied `build-verification/astra_review_probes.py` unchanged before touching application code. `build-verification/astra-corrections-before.log` reproduced all three findings:

- Historical graph event 1 opened History with `as_of_id=None` and no selected entry.
- Ended Enemy loaded as Friend; a notes-only graph correction saved Friend.
- One participant checkbox wheel event called the outer scroller once and the list zero times.

The same unchanged probe after the fixes (`astra-corrections-after.log`) reports History event 1 / selected state 1, Enemy loaded and retained, and outer=0 / list=1.

## Finding-to-fix mapping

| Finding | Correction | Regression evidence |
| --- | --- | --- |
| Ended correction overwrites content | `History.editing_state` resolves the exact effective entry, including inactive states. Graph Current editing loads the latest dated state; baseline is used only without dated entries. The relationship store uses the same resolver for omitted semantic defaults. Current correction identifies the entry and ended status. | Graph inspector correction, notes-only save, and return for Friend baseline / Ally / later ended Enemy (reversed endpoints, directional semantics, inverse Opponent), then active and undated variants. Complete before/after row equality permits only notes to change; IDs, event IDs, activity, type, semantics, endpoints, and inverse label are checked. |
| Nested participant wheel routing | Toplevel handlers identify the nearest ScrollFrame ancestor, including canvas/content background. Only its handler consumes input. Boundaries contain the gesture; no fallback to outer form. Native Text and Treeview handling remains intact. Focus reveal is unchanged. | Real Tk `event_generate`, 100-character cast: checkbox, list padding/background, lower boundary, preview Text, outer background, nested Treeview. Spies assert exactly one intended scroll call or no form scroll for native widgets; actual yview changes and keyboard focus visibility are asserted. |
| Graph History loses time | Graph passes `as_of_id`. History uses the domain resolver to select Current/latest (including ended), before-first baseline, direct event entry, or preceding effective entry. The context names inspected time and correction target; the correction editor retains this context and names its exact state. Existing StateEditor correction writes the selected state ID. | Graph inspector -> History -> embedded correction -> review -> commit -> return across Current, baseline, Alliance, intermediate Interlude, and ended Conflict in Changes only. Complete row comparisons verify only the selected entry notes change; captured graph state compares equal after return, including time, selection, filters, positions, pins, zoom, and inspector scroll. |

Tests are in `tests/test_astra_ux_corrections.py`. The original review probe remains unchanged as an independent before/after reproduction.

## Safeguards and validation

- Focused tests: 17 passed (`build-verification/astra-focused.log`), including existing batch reset/focus, failed save retention, exact-record editing, and historical inspection safeguards.
- The first full run had one status-text assertion failure; the wording was restored without weakening the existing test. Final full-suite results are recorded below.
- Existing suite covers mutual/directional meaning, inverse labels, history, story isolation, import/export, backups, recovery, and batch additions. Successful batch saves still clear every field, focus Source, and stay open; failed saves retain input.
- Packaged smoke additionally exercises ended notes correction through graph actions, full state preservation, and historical History selection, alongside the existing release checks.

## Interactive checks and limits

Used the computer-use skill with the disposable `build-verification/astra_visual_fixture.py` (100 characters; Friend -> Ally -> ended Enemy). On the live Windows display, opened History from the intermediate Interlude graph: Alliance was selected, context named Interlude and state 1 at Alliance. Opened the correction editor: Ally, Mutual, Alliance and state 1 were visible. Returned through History to the unchanged Interlude graph and selection. In New event, injected a physical wheel gesture over participant checkboxes: list moved while outer form controls stayed fixed.

The live check inspected navigation and scrolling; notes-only persistence and the full correction/review/save/return matrix were automated real-Tk checks. A subsequent small label addition keeps the inspected-time caption visible inside the embedded editor too; final tests/build include it. No claim is made that this final caption was visually checked across display scales.

Automated Tk geometry/focus/layout tests are not visual validation at actual Windows display scaling. The live checks used the available display only; no physical 125%, 150%, or 200% DPI matrix, alternate monitor, or fresh external Windows machine was tested. No user story data was used.

## Final release identity

- Final full suite: **160 tests passed in 64.830 seconds**, run by `build_windows.ps1` after final application source changes. Log: `build-verification/astra-build.log`. The separate earlier `astra-full-suite.log` intentionally retains the initial wording assertion failure for audit.
- Windows build completed successfully with the locked dependencies and CPython 3.13.9 x64. Packaged smoke passed: `ok=true`, `frozen=true`, Windows 11, Tcl/Tk 8.6.15. Evidence: `build-verification/astra-smoke.log` and `build-verification/packaged-smoke.json`.
- Application **0.9.0**, database schema **8** (unchanged).
- Source and packaged build fingerprint, verified equal after smoke: `4add16968df7387b57ba1940bd6710409c28e9c99ea15eb93b375fa3de24c967`.
- Executable: `dist/StoryAtlas/StoryAtlas.exe`; SHA-256 `B1EEB6D42F808D063117991DD43144D9CFAE94C106EB46A352C5B3C51F826097`.
- Distribution: `dist/StoryAtlas-Windows-x64.zip`; SHA-256 `0388E268CE787513B9EBFD16E5A5A3E2DBC299E5E95223B1D90456CE93805E3D` (also in the adjacent `.sha256` file).
- Distribute the ZIP or the entire StoryAtlas folder, not the executable alone. This package supersedes the implementation report's earlier build.
- The disposable interactive fixture was closed after verification. No application source changed after the successful final build.
