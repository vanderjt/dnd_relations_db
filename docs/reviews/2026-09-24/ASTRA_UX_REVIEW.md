# Independent review of Astra's UX implementation

24 September 2026. Reviewed the current source against COMPETITIVE_UX_REVIEW.md
and UX_IMPLEMENTATION_REPORT.md. No Git repository is available, so this is a
current-state review of the implemented workflows rather than a commit diff.

## Assessment

The implementation substantially follows the requested direction. The event
workflow now has a contained edit/review flow, participant selection is searchable
and persistent across filters, newly created events are revealed, and contextual
Back navigation covers event/graph/profile work. These are meaningful reductions
in interaction friction rather than merely cosmetic changes.

I would retain this implementation and make a focused corrective pass before
calling it ready for distribution. One reproduced issue can unintentionally
overwrite relationship content; two others undermine the intended seamless flow.

## Findings

### P1 — Correcting an ended connection loads baseline fields into the latest state

Location: `story_atlas/graph_view.py:336–351`, with persistence through
`story_atlas/relationship_store.py:26–37`.

`relationship_row()` looks for an active Current relationship and falls back to
the stored baseline. For a relationship whose latest state is Ended, the first
lookup has no result. The correction form therefore receives the baseline fields,
even though saving an existing dated relationship updates the latest dated state.
The new Changes-only graph makes ended connections directly available for this
action.

Reproduction on a disposable story:

1. Create a Friend baseline, then an Ally event state.
2. Add a later Enemy state marked Ended, with its own notes.
3. Show Changes only at the ending event and choose Correct entry.
4. Accept the explicit warning that correction targets Current.
5. Change only the notes and save.

Observed: the editor loads **Friend**, and the latest **Enemy** state becomes
**Friend** after the notes-only save. The warning describes the destination but
does not prevent loading the wrong source values. Other fields such as direction
and inverse label can also differ between baseline and latest state.

Required correction: resolve the latest effective state including inactive states
for a Current correction. Use baseline only when there are no dated states.
Alternatively route to the exact state editor with an explicit state ID. Keep
historical correction versus Current correction unambiguous. Add regressions for
notes-only edits of ended connections, including changed semantics/inverse labels,
and assert all untouched fields remain identical.

### P2 — Mouse wheel over participant checkboxes scrolls the outer form

Location: `story_atlas/scroll_frame.py:39–43` and the nested `ScrollFrame` in
`story_atlas/participant_picker.py`.

Both nested and outer ScrollFrames bind MouseWheel to the same dialog. The outer
frame's handler sees the checkbox as its descendant, scrolls the whole event form,
and returns `break` before the inner participant-list handler runs.

Reproduction: create a 100-character cast, open New event, and send a mouse-wheel
event over a visible participant checkbox. Observed callback counts: outer form
**1**, participant list **0**. Search and the scrollbar remain usable, but normal
list browsing moves the wrong region.

Required correction: route wheel events to the nearest eligible scroll container,
with a deliberate policy for behavior at its boundaries. Add a real event-dispatch
regression covering checkboxes, empty list background, preview text, and outer
form background. Calling the inner handler directly would miss this issue.

### P2 — Graph History loses the event context the user was inspecting

Location: `story_atlas/graph_view.py:359–362`.

View history constructs `HistoryDialog` without `as_of_id`. On an early-event
graph, the dialog opens with no effective state selected and no originating event
context. This is particularly awkward because Correct entry on a historical
graph explicitly directs users to History when they want to correct the earlier
state.

Reproduction: show the Ally event of a relationship that becomes Enemy later;
select its edge and choose View history. Observed: graph event ID **1**,
History `as_of_id=None`, and History selection **empty**.

Required correction: carry the selected graph time into History and select the
state effective there. Handle Current, Before first event, an event without a
direct change, and an ended state deliberately. Add graph-to-History tests, not
only event-to-History or graph-to-profile tests.

## What was done well

- `StateEditor` is reused across event changes and History, reducing duplicated
  persistence logic and replacing the previous modal stack with internal steps.
- Recording and correction remain distinct. Before/after review includes notes,
  and commits check whether the underlying state changed since review.
- Participant selection uses stable IDs independent of the current search.
  Duplicate names and existing deleted participation references are explicit.
- Back navigation captures substantial context, including graph layout/zoom and
  event outline selection/expansion. Goals editing uses that same return path.
- Graph exports distinguish time, display scope, and current profile scope.
  Endings are represented explicitly in the changes-only view.
- Shared theme vocabulary is reused; presentation categories do not silently
  alter relationship semantics or classify arbitrary type names.
- No unnecessary migration or renderer rewrite was introduced. New concerns are
  split into focused modules such as participant_picker, state_editor, event_context,
  graph_time and reading_text.

## Remaining polish and product tradeoffs

These are follow-up opportunities, not additional reproduced correctness defects:

- The event page still shows character lists, goal outlines, change outlines and
  prose details together. Test whether this is easier to scan at laptop size;
  more wrapping text alone does not establish a simpler reading hierarchy.
- Graph visual categories are saved per named view. That is a reasonable scoped
  implementation, but users may expect a type to keep its color across views.
  Keep the current limitation visible before considering story-wide settings.
- Large participant summaries can become long. Observe selection of a large cast
  before deciding whether to show a compact count with an expandable selected list.
- Event and state input still lack crash-recovery drafts. This is documented and
  not a regression, but it matters more as users write longer notes in these tasks.
- A small storyteller usability study remains the best next step after the three
  findings above. Verify that users can complete event → relationship change →
  graph → return without coaching and correctly explain historical versus Current.

## Independent validation

- Ran `.build-env/Scripts/python.exe -m unittest discover -s tests -v`.
- **157 tests passed in 56.406 seconds**.
- Disposable 100-character/300-relationship benchmark: 0.684 s initial display,
  0.028 s unrelated notes refresh, 0.035 s direct focus on this machine.
- Full log: `build-verification/astra-independent-review.log`.
- Additional executable probes:
  `build-verification/astra_review_probes.py` and
  `build-verification/astra-review-probes.log` reproduce all three findings.
- All probe databases/settings were temporary. Production code and user stories
  were not changed. The probes document observed defects; they are not passing
  regression assertions for the desired behavior.

The existing suite is valuable but misses these boundary paths. Passing the suite
does not negate the reproduced findings. This review did not independently repeat
Astra's native visual inspection, packaged smoke test, clean-machine testing,
physical display-scaling checks or user study. Packaging results in the
implementation report remain Astra's reported results.
