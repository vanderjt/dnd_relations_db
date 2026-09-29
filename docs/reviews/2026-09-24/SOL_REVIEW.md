# Senior review of Sol's implementation

24 September 2026. Reviewed against WORK_PLAN_FOR_SOL.md and Sol's
IMPLEMENTATION_REPORT.md. Application source and release artifacts were not changed.

**Recommendation: changes required before sign-off.** Most planned capabilities
are implemented, and the release report correctly distinguishes local package
checks from the outstanding clean-machine gate. Four reproducible or directly
verified interaction gaps remain. Task completion claims need qualification until
these are addressed.

**Follow-up:** The four findings below have since been addressed in source.
See `SENIOR_FIXES.md` for the new regression and release verification results.
The original findings and reproduction observations are retained as review history.

## Findings, in priority order

### P1 — Discarded profile changes survive search navigation and can be committed later

Location: `story_atlas/global_search.py:183–190` (also the history branch at 192);
underlying contract in `story_atlas/characters.py`, `can_leave()`.

Reproduction: edit a saved character's name from `Original` to `Discard this name`;
open Ctrl+K and select a chapter; answer No to the save-before-continuing prompt.
The chapter opens, but the character editor still contains `Discard this name`
and remains dirty. A subsequent Save character commits that supposedly discarded
name. The probe confirmed both the retained field and the later database write.

`can_leave()` deletes the recovery draft on Discard but does not reload the saved
profile. Callers that open another character subsequently replace the editor;
the new chapter/event/history search paths do not. This is an existing helper
contract exposed by the new routes, not proof the entire defect originated in Sol's work.

Required fix: ensure successful Discard navigation restores committed editor state
(or an empty new-character form) without changing Cancel/Save behavior. Cover
chapter, event, and historical result navigation through actual SearchDialog
callbacks. Verify discarded values cannot be committed on a later Save or restored
by the draft timer. Test existing and new unsaved profiles.

### P2 — Chapter move previews are unbounded native message boxes

Location: `story_atlas/event_view.py:254–262`, `move_chapter()`.

The implementation places every chapter and every event twice into askyesno.
A disposable story with 102 events produced **217 message lines**. The approved
scale dataset has 300 events. This control provides no application-managed scroll
area or bounded preview layout; reviewing a large chronology and reaching its
confirmation controls is not a supported, tested interaction at laptop sizes.
The exact native overflow appearance was not manually inspected.

Required fix: use a resizable modal preview with scrollable before/after lists,
persistent Confirm/Cancel controls, chapter grouping, and explicit Unassigned
entries. Keep the storage-layer preview/stale-check/atomic commit behavior.
Validate the rendered widget boundaries and keyboard access using the scale
dataset; the current benchmark measures preview data generation, not this dialog.

### P2 — “Inspect saved relationship here” does not resolve the effective state

Location: `story_atlas/relationship_dialog.py:191–198`, `inspect_saved()`.

Reproduction: start a relationship from an event but deliberately leave Begins at
event blank. Save and choose Inspect saved relationship here. History opens with
the correct connection, but **no state selected**, even though its baseline is
effective at that event. The probe returned `states=['baseline'], selected=[]`.
The same exact-event lookup cannot select an earlier dated state that remains
effective at the originating event.

Required fix: select the latest state effective at or before the originating
event, falling back to baseline. Explain Present/Ended/Not yet begun where
appropriate. Do not select a later state or silently imply the connection is
present if its explicit beginning lies after the origin. Test blank beginning,
earlier beginning, exact beginning, later beginning, and an ended state. Preserve
the successful entry reset and modal return behavior.

### P2 — Chapter/event selection is not retained per story

Location: `story_atlas/projects.py:98–119` and `story_atlas/event_view.py:101–104`.

Reproduction: select chapter #1 in story A, open story B, then reopen A. The
chapter selection becomes `all`. Projects retains character and relationship
workspace state but omits chapter/event state; EventView resets it on every story
switch. This misses Task 4's explicit per-story selection requirement.

Required fix: store chapter/event IDs in the existing story-keyed session state
and restore after the database/view refresh, validating IDs against the reopened
story. Preserve All and Unassigned choices; fall back safely when a destination
is unavailable. Test A → B → A with identical numeric IDs belonging to different
chapters/events in the two databases. No new database schema is necessary.

## What passed and should be retained

- Quick-event dirty close now handles Save/Discard/Cancel and failed saves.
- Contextual relationship entry retains an explicit originating event and clears
  editable fields after additions; the tab remains in event context.
- The chapter outline includes empty chapters and Unassigned; destination links
  and validated, stale-aware chapter moves exist.
- Search includes chapter/event text and stable baseline/dated-history identities.
- Goals inspection uses read-only child dialogs, preserving event drafts.
- Graph inspector sizing, build identity, explicit launchers, modular event
  editors, deterministic benchmarks, and release verification were added.
- No schema migration was introduced; schema remains 8.

These positive findings do not override the four defects or imply that every
acceptance item was exhaustively re-tested manually.

## Independent validation

Commands run from the project root:

```powershell
.\.build-env\Scripts\python.exe -m unittest discover -s tests -v
.\.build-env\Scripts\python.exe build-verification\sol_review_probe.py
```

**137 tests passed in 40.726 seconds.** Full output:
`build-verification/sol-review-tests.log`. The additional disposable probe reproduced
the discard, historical selection, and per-story selection problems and captured
the oversized preview message. It is a review probe, not a replacement for permanent
regression tests. Existing user stories/preferences were not used.

The existing benchmark measured 1.416 seconds initial graph display, 0.019 seconds
notes refresh, and 0.036 seconds direct focus. Local artifact hashes match the
executable and ZIP hashes recorded by Sol. This review did not rebuild the package
or independently repeat packaged smoke/clean-machine testing.

Physical DPI, manual visual accessibility, clean Windows execution without
Python/Anaconda, and observed writer tasks remain outstanding, as Sol reported.
After fixing the findings, rerun focused and full tests, rebuild the release,
repeat packaged smoke tests, and replace the recorded artifact hashes. Do not
describe the existing package as containing fixes made only in source.
