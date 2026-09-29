# Story Atlas UX implementation

24 September 2026. Implements the competitive UX review against the current
source, preserving the event-layout corrections. No database migration or
framework change was needed. Python, Tkinter, SQLite, NetworkX, Matplotlib,
dark/light themes, backups, imports, exports, and separate story files remain.

## Review-to-implementation map

| Recommendation | Implementation | Validation / limits |
|---|---|---|
| Finish event creation in place | `EventDialog` reveals the saved ID in its destination chapter; the selected event exposes Record change, Start relationship, and Graph at event. | Regression saves into a different chapter, injects a failed save, and verifies the selected ID and next actions. Existing move-destination navigation is preserved. |
| Searchable participant selection | New `ParticipantPicker` uses native checkboxes, Tab/Space, search independent of selected IDs, and a persistent selected summary. Names include stable IDs and role/faction. | 100-character search/keyboard regression selects five nonadjacent people, changes searches, and commits exact IDs. Duplicate names stay separate. |
| Deleted participation | New choices exclude Trash; existing linked Trash participants stay visibly marked and checked. | Deleted and historical reference assertions plus existing recovery/import tests. These references cannot be unchecked while in Trash; restore the character to change participation. |
| Inline goals preview | Focusing a checkbox shows current committed goals in a wrapping, selectable area. | Draft preservation and saved-text assertions; native light-theme inspection of checkboxes and preview. Goals remain free text, not historical versions or structured tasks. |
| Contained relationship changes | One event dialog contains connection search, participant-only scope, state editing, review, and completion. `StateEditor` is reused inside History and in the standalone host. | Record/correct, mutual/ended states, keyboard review/save, Back, cancellation, failed writes, and later-state independence regressions. No chooser/editor/review stack in the event task. |
| Record versus correct | Record adds a dated state; Correct entry updates the state ID at this event. Before/after includes notes and direction. Existing `History` transactions enforce whole-timeline duplicate prevention. | Tests assert unchanged IDs on correction, rollback on a real duplicate conflict, retained input on injected errors, and independent later states. Review rechecks saved state before committing. |
| Committed result and next steps | The saved change is selected in the event outline; the task offers another change, Graph at event, and Close / Return. | Tests verify exact saved state selection and correct graph event after completion. |
| Historical context | Graph uses Current — after the last event or After: Chapter / Event. Profiles, goal previews, and graph character details explicitly identify current profile information. | Historical export tests check independent time/display/profile scopes. The undated baseline is labeled Before first event. |
| Contextual Back | `EventDestination` captures chapter, all four outlines, expansion, focus, selection, scroll, pane widths, and collapsed navigation. Graph destinations preserve filters, positions, pins, selection, zoom, and inspector scroll. | Full Event → Graph → Profile → Back → Back regression and contextual goal-save/return regression. Story switching clears Back and graph presentation choices; unfinished task dialogs block switches. |
| Reading hierarchy | Prominent selected-event/profile titles, quiet context, compact outline previews, complete wrapping detail text, and one outer prose scrollbar in event details. Event layout remains three panes. | Existing collapse/selection/indentation regressions remain. Long-text and both-theme tests; native dark event overview and light larger-text inspection. Trees retain their own scrolling for large outlines. |
| Narrow windows | Expand details hides chapter/event navigation; Show chapters and events restores it. Compact action menu remains available. | Automated 900×600 and large-text checks, existing simulated scaling checks, plus native light 900×600 inspection. At narrow widths the deliberate expand control provides more reading space. |
| Primary and secondary actions | Event creation is primary when no event is selected; Record change is primary for the selected event. Profile read mode has Edit profile; edit mode has Save changes. Duplicate/Delete are in Profile actions. | Existing profile/Done/Trash tests and geometry checks. Menus remain keyboard accessible. |
| Language and validation | Event title/position and state fields have inline validation. Empty errors consume no form space. Relationship direction includes one-way/shared explanations and perspective previews. Save and close, Add relationship, and Save correction describe their behavior. | Failed saves retain values. Existing ten-addition batch, semantic, keyboard, and draft tests remain passing. Recovery wording says Save changes to commit. |
| Progressive optional fields | Event summary and relationship timing/notes expand deliberately. Collapsing preserves text. Inverse labels remain visible when populated, including conflicts with Mutual. | Optional-content retention regression; existing inverse validation and batch clearing checks. |
| Graph time exploration | Previous/Next event preserves layout and limits. Filters can highlight event changes or show a separate changes-only scope including endings. Clear filters leaves historical time and focus intact. | Event stepping, positions/zoom/selection, ending visibility, and independent filter/time regression. Full historical graphs continue to omit inactive connections. |
| Honest graph exports | PNG titles distinguish graph scope; JSON adds `time_scope`, `display_scope`, and `profile_scope`. Changes-only ending records export inactive. | PNG/JSON assertions and existing snapshot/import tests. View metadata records focus/type/direction filters independently. |
| Dense graph and individual connections | Dense views suppress unrelated labels, reveal selected/nearby labels, and keep every connection in the inspector. No consolidation or edge merging. | Disposable 100-character/300-relationship tests cover parallel/reverse record selection, drag/pin, event stepping, highlight, preserved positions/zoom, and full inspector notes. This is automated interaction, not a timed writer study. |
| Explicit visual categories | Types default to Other. Filters → Visual categories assigns optional presentation categories explicitly; named graph views retain them. No type name implies support/conflict. | Tests verify neutral Mentor, explicit assignment, saved-view round trip, invalid metadata rejection, and unchanged stored meaning. No new schema; legacy views load with defaults. |
| Goals in context | Event goals outline offers Edit current goals. Save, then named Back returns to the event. Cast goals searches names/IDs/prose and opens the chosen current profile. | Search/direct navigation and edit/save/exact-event return tests. All profile fields and free text remain intact. |
| Participation matrix | Deliberately deferred as requested. | No speculative schema or task conversion. |

## Preserved event-layout corrections

Stable outline IDs preserve expansion, selection, focus, and scroll on unrelated
refreshes. Placeholder nodes now also have stable IDs. Full saved notes and goal
indentation remain available, even when long outline previews are shortened.
Responsive event actions and nested-tree wheel handling remain covered. Quick
character/event focus callbacks are still canceled on destruction. History's
event-context state selection is retained; the event correction path now stays
inside the same task instead of opening that nested History window.

## Verification

- Source checkpoint: **157 tests passed in 67.337 seconds**; log
  `build-verification/ux-full-suite.log`. The release build reran all **157 tests
  in 66.346 seconds**, passing after the final wording, keyboard, and
  optional-summary adjustments: `build-verification/ux-build.log`.
- Ten new tests in `tests/test_competitive_ux.py`; existing tests were updated
  where they explicitly required the removed modal stack or modifier selection.
  Behavioral assertions for history, input preservation, and batch entry remain.
- Release benchmark: 100 nodes / 300 edges, 0.759 s initial display,
  0.023 s unrelated notes refresh, 0.037 s direct focus on this machine.
  These timings are machine-specific and do not establish usability targets.
- Native Windows inspection through the computer-use plugin: dark 1280×720 event
  overview; connection dropdown; Ctrl+Enter to internal edit/review; Escape Back;
  light 900×600 with 14-point text; expand/restore navigation; participant search,
  native checkbox labels, current-goal preview, and visible save/cancel controls.
  The inspection prompted smaller validation spacing, stronger selected titles,
  and a collapsible optional event summary. Automated checks cover final geometry.
- All stories and settings used for validation were disposable. No existing user
  database was opened or edited.

## Remaining validation limits

Actual Windows display scaling at 100/125/150%, per-monitor transitions, a clean
machine without Python/Conda, and the five-storyteller formative study were not
performed. Automated geometry tests and native inspection on this development
machine do not substitute for those checks. Dense labels can still overlap around
a heavily connected selected character; focus/filter views and the inspector
provide access to complete details. Native screen-reader output was not tested.

Visual categories are saved with named graph views rather than globally assigned
to a story's type vocabulary. This keeps them explicitly presentation-only and
avoids a schema migration. Event and relationship-state editors preserve failed
input and confirm leaving, but do not create crash-recovery drafts; profile drafts
continue to use the existing recovery system.

## Packaged build

**Build and local packaged smoke tests passed.** Build log:
`build-verification/ux-build.log`; smoke log: `build-verification/ux-smoke.log`;
machine-readable results: `build-verification/packaged-smoke.json`.

The frozen executable ran with Python/Conda/Tcl overrides removed and a minimal
Windows PATH on Windows 11 build 26200, Tcl/Tk 8.6.15. Smoke tests verified first
launch/reopen, isolated samples, bundled assets/fonts/TkAgg, event reveal and
participant filtering, contained record/review/correction, Event–Graph–Profile
Back, historical exports, batch reset, portraits, backups/restore, settings,
version-7 migration/backup, version-8 reopen, and writable external data.

- Application version: **0.9.0**; schema: **8**.
- Source and packaged fingerprint (matched):
  `03827b169d82dc8042cd827b0813b138d6774bc90afa7a5575cf8b82b5a9662d`.
- `dist/StoryAtlas/StoryAtlas.exe` SHA-256:
  `0FCED02C2368E81B887260EBD88917FE9E5E832228B21F62C781C8A3D18F6ED6`.
- `dist/StoryAtlas-Windows-x64.zip` SHA-256:
  `60BF80E6E227AF3A1533DFA99B60F2D7B984F88A6C5DBE647D72B929513C6B9D`.

The package uses the existing locked CPython 3.13.9 / PyInstaller environment.
Distribute the complete ZIP or entire `dist/StoryAtlas` directory, never the
executable by itself. Local packaged verification is not a clean-machine test.

## Corrective follow-up

The independent review identified three issues after this implementation report. See [ASTRA_UX_CORRECTIVE_REPORT.md](ASTRA_UX_CORRECTIVE_REPORT.md) for the focused fixes and replacement package identity; the original validation and package hashes above describe the earlier build.
