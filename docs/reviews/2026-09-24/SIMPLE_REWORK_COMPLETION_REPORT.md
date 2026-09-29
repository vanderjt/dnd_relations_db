# Simple-mode task rework

24 September 2026 · Story Atlas 0.11.0 · schema 10 · portable format 6.

## Model decisions and preserved guarantees

- Classification is a dedicated current character attribute with exactly NPC Enemy, Player Enemy, Neutral, NPC Ally and Player Ally. It neither interprets player control nor changes narrative role, occupation or relationships.
- Migration 10 uses the existing backup-first, transactional migration runner. All existing characters, including Trash, receive Neutral. JSON formats 1–5 remain importable; new full exports and graph snapshots use format 6.
- Suggestions are presentation vocabulary, not records or defaults. Case and custom spelling remain distinct. Tags retain existing comma-separated storage.
- Simple and Advanced continue sharing SQLite, settings, Projects, exclusive publication, history, assets, backup, import and recovery services. NetworkX and Matplotlib remain. No user database or settings file was used for development.
- Recovery snapshots are uncommitted, stored per database. Relationship batches, events and exact-state commits delete their recovery snapshot in the same transaction as the committed change.
- Undo is deliberately limited to a recent character creation with no subsequent committed action; it uses Trash. It never overwrites later edits.

## Requirement mapping

| Request | Implementation | Evidence |
| --- | --- | --- |
| 1. Title → Create → graph | `story_setup` derives Windows-safe names, recognizes reserved names, suggests unused numbered filenames and retains exclusive publication. Normal creation has no picker. Destination and optional Change location are visible; opening customization starts collapsed. Projects defaults to the configured user-data Stories folder. | Filename/reserved/invalid/collision tests; actual StorySetup default save with picker mocked to assert no calls; custom filename prefill and canceled picker; existing setup isolation tests. |
| 2. Progressive profile | Shared `ProfileEditor(simple=True)` emphasizes Name and Classification. Optional details, Story, Goals, Abilities, Inventory and Notes are collapsed and show filled-content counts. Hidden widgets remain mounted. Save/Close remain outside the scroller. Introduction details expand explicitly. | Real-Tk collapsed-state, hidden-goals retention, unchanged-refresh, disabled-save and geometry tests. Native profile inspection described below. |
| 3. Suggestions and tags | Focused `suggestions` module combines starter lists with exact custom values. Occupation, species and status are editable. `TagPicker` adds/removes individual tags; a typed pending tag participates in dirty checks, drafts and saving. | Built-in/custom spelling tests, additive/removal tests, pending-tag draft/save test; existing organization/export tests. |
| 4. Empty selectors and nested creation | Relationship source/target show No characters yet / No matching characters with Create character. Creation is embedded and preserves the parent task. Effective-event entry offers No events yet and Create event using the shared quick-event dialog. Event participants explain empty/no-match states and offer embedded character creation. Inverse labels use plain entries; state types receive real suggestions. | Nested batch and event creation tests assert retained notes/title/summary and selected IDs. Existing keyboard selector tests cover Down/Enter; text-click regression now asserts the list stays closed. Record lists contain actual records; chronology sentinels are explicit choices. |
| 5. Classification | Focused `classification` module, SQL constraint and service/import validation. Warm enemy colors, cool ally colors, neutral gray and literal node badges. Legend/filter is visible normally and in More in compact layouts. Graph scope explicitly says classifications are current. Planned/provisional outlines and labels remain. | Version-9 migration with backup and field preservation; all five values; duplicate/Trash/JSON round trip; invalid-label rejection; filter, badge and unique-color checks. Existing backup/draft and planned-cast tests also run. |
| 6. Guided Connect | Saved summaries expose Connect. Ordinary graph clicks toggle targets while connecting; Shift-click remains available. Stable-ID chips expose Remove and Make source, with an explicit Exit selection. Add relationship opens with zero/one selection. Keyboard selectors remain available through selection controls and form fields. Compact layouts put selection chips inside the form scroller. | Source changes, exact ordered one-to-many target lists, duplicate-name baseline tests, graph mouse/keyboard dispatch and complete selection reset. A test caught and fixed a source trace dropping targets. |
| 7. Fewer relationship decisions | Explicit editable Friends, Parent/Child, Employer/Employee, Mentor/Student and Custom presets. Notes collapse without losing text. Review shows every pair's meaning, inverse label, notes and event. Shared preview/commit validation and explicit target exclusion remain. | Preset/nested creation/review/commit test; existing transactional preview, conflict rollback, failure retention and clear/refocus/stay-open tests. Success also clears preset and graph selection. |
| 8. Inspection versus editing | `CharacterSummary` reads saved values without editable fields or drafts. It exposes current classification/details/goals, every individual connection (including ended), Edit character and Connect. Full editing remains available. Exact history correction still uses shared StateEditor. | Summary creates no activity/dirty state; native summary/Connect inspection; existing historical ended-state correction and exact connection tests; new recovered-ended-correction test. |
| 9. Event progression and timing | Next event navigates or creates an editable Scene N suggestion in the current chapter. Chapter plus first event remains atomic. Compact introduction caption has Change introduction; detailed chronology guidance appears on expansion or validation failure. | Existing progression/carry-forward/layout tests; new current-chapter/suggested-title test; chronology, reassignment and rollback suites retained. |
| 10. Interruptions, recovery, Undo | Literal Save/Discard/Stay in Simple task navigation and embedded character cancellation. Unchanged saved profiles/events/corrections avoid writes. TaskDraft extends shared drafts to event creation/editing, relationship batches and changes/corrections. Missing IDs are retained explicitly or block recovery of an exact missing context. RecentCreation guards Undo against later activity/profile changes. | Restart/reopen, recovery launched from Advanced and story-isolation tests; missing target/participant tests; exact ended-state draft recovery; transactional draft deletion; Undo refusal after edits and Trash restoration; canceled playhead/mode navigation tests. |

## Before / after task steps

| Task | Before | After |
| --- | --- | --- |
| New story | Fill/review three names → Create → file picker → filename/location → Save | Title → Create story; opening names and location are optional |
| New character | Scroll a full profile with many visible fields | Name → optional classification → Save; details expand when needed |
| Inspect character | Clicking opens editable form | Click → saved summary; Edit is explicit |
| Connect one character to two others | Know Shift-click order before Add becomes enabled → enter meaning/inverse manually | Click Source → Connect → click two targets → choose editable preset → Review → Save |
| Add a missing endpoint | Leave the task or find a separate creation route | Create character inside the task → resume with all other input retained |
| Advance story | Finish event / Continue → blank event title | Next event → next existing event, or suggested title with current chapter |
| Resume after interruption | Character drafts only | Recovery restores character, event, batch or exact-state task without committing |

## Validation

Focused suite: 26 tests passed in 21.590 seconds in `build-verification/rework-focused.log` before the final unchanged-task/stale-draft refinements. The release build reruns these and the complete suite against final source.

An intermediate complete suite passed 183 tests in 92.209 seconds (`rework-full.log`). The final suite additionally includes exact-state recovery, nested event creation and expanded geometry coverage. Final build and package results are recorded below.

Coverage includes both themes, 1280×720 and 900×600, larger text and simulated Tk scaling, and disposable 100-character/300-relationship graphs. The focused Simple graph draw measured 0.320 seconds on this machine. Timings are observations, not guarantees.

Native Windows inspection used the computer-use skill and disposable `rework_visual_fixture.py`. Inspected the dark 1280×720 graph and new-character pane; inspected the light 900×600, 16-point profile, unchanged Close, saved-node summary and Connect. This exposed excessive toolbar/selection chrome and a partially hidden classification selector. The final compact toolbar, reduced profile guidance and connection-footer refinements were then checked by automated geometry tests. The last connection-footer/scroll-placement refinement was not independently re-inspected natively.

Automated widget-boundary tests are distinct from native inspection. Neither is actual Windows 125%/150%/200% per-monitor DPI testing. No display-scale settings were changed.

## Remaining limits

- Actual Windows DPI changes, alternate monitors, a separate clean Windows machine without Python, and observed writer usability/task-time studies were not performed.
- Very narrow graphs with large labels can overlap; focus/filter/zoom remain useful. Dense graphs retain the existing selective-label policy.
- Drafts use short debounce intervals (character one second; Simple tasks half a second); an abrupt crash can lose input from the most recent interval. Missing exact correction events require restoring their context rather than guessing a substitute.
- Creating an event from a relationship uses the existing compact modal quick-event dialog. Its parent form is retained. Embedded character creation commits that character separately and says so.
- Undo covers only recent character creation before later committed activity. Event/batch creation has no general Undo; existing Trash/restoration and backups remain available.
- Tags keep the existing comma-separated format, so a comma remains a separator rather than part of an individual tag.
- Classification filters are presentation-only, and labels always describe Current. No historical classification tracking or interpretation of Player Enemy/Ally is introduced.

## Final release evidence

- Final full suite: **188 tests passed in 88.263 seconds**, executed by `build_windows.ps1` against final application source. Log: `build-verification/rework-release-build.log`.
- Final focused additions: **13 tests passed in 7.448 seconds** (`rework-new-tests.log`), including Simple draft recovery launched from Advanced and complete deselection of the last graph source. Combined earlier focused baseline/rework run: 26 passed.
- Windows build completed successfully with CPython 3.13.9 x64 and locked dependencies. Package smoke passed with `ok=true`, `frozen=true`, Windows 11 and Tcl/Tk 8.6.15. Logs: `build-verification/rework-packaged-smoke.log`, `build-verification/packaged-smoke.json`.
- Smoke includes startup/reopen, sample isolation, Advanced history corrections, exports, portraits, backups, schema migration/reopen, external writable data, Simple classification/collapsed form, summary inspection, event draft recovery and atomic commit, and relationship full-batch reset.
- Application **0.11.0**, schema **10**, export **6**. Source, frozen metadata and packaged smoke fingerprints match: `baf1d2ef3be3e65e3738fb3753b877ebf398bd6de0e63d6b4cf118250872dca9`.
- Executable: `dist/StoryAtlas/StoryAtlas.exe`; SHA-256 `B392A6FD8FDE7B37CCB6C69045B059415A7B032105D24CBB732FC3074A5A5FDC`.
- Distribution: `dist/StoryAtlas-Windows-x64.zip` (42,937,676 bytes); SHA-256 `D390CA92C77160C00597D720A67427B9A3368919DF83BF59291B9226D8491443`. The adjacent `.sha256` file matches.
- Distribute the ZIP or entire StoryAtlas folder, never the executable alone. The build was tested locally with Python/Conda/Tcl environment overrides removed and PATH restricted by `tools/smoke_windows.ps1`; no external clean-machine certification is claimed.
- No application source changed after the successful final build. Earlier interrupted build logs remain as development evidence; `rework-release-build.log` is the release gate.
