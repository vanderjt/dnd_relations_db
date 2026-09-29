# Story Atlas improvement plan for Sol

Prepared from [the 24 September 2026 review](REVIEW.md). The review identifies a strong local data foundation, with the main product gap being the effort required to carry story context between writing tasks. This plan addresses reliability and release clarity first, then improves event, chapter, and search workflows before validating larger feature ideas.

**Senior review: revised 24 September 2026.** Approved for sequential execution
with the contracts below. This revision changes planning only; it does not claim
any of these improvements have been implemented. The last verified source baseline
was 124 passing tests, schema version 8, and complete-story JSON format version 4.

### What changed in senior review

- Kept Luna's eight improvement areas; added a ninth, final-release task.
- Replaced ambiguous dependencies with a sequential handoff and shared safety contracts.
- Specified exact historical result identity, baseline/ended/Trash rules, and navigation.
- Added read-only chronology previews with stale-preview checks and atomic confirmation.
- Defined modal participant inspection so reviewing goals cannot discard event drafts.
- Added measurable regression and scale checks without arbitrary timing thresholds.
- Kept scope bounded: no calendar, structured-goal migration, chapter deletion, search-engine
  replacement, or renderer rewrite in this plan.

## How to use this plan

Give Sol one task prompt at a time, together with the shared execution contract
and that task's implementation requirements and acceptance checks. The quoted
prompt is not the whole specification. Keep the dependency order below. Do not
expand a task into unrelated redesign work. Sol should read the files directly;
the review and diagram describe the baseline, not necessarily the code after
earlier tasks have completed.

## Shared execution contract — applies to every task

> Implement only the assigned task in WORK_PLAN_FOR_SOL.md, including its detailed
> requirements and acceptance checks. Inspect the current implementation first.
> Preserve existing user edits and use disposable databases for validation.
> Keep Python/Tkinter, SQLite, NetworkX, Matplotlib, the shared theme system, and
> current dark/light settings. Do not change a user's active database, preferences,
> sample story, or packaged executable merely to demonstrate an improvement.
>
> Preserve new-relationship batch entry: every successful addition clears ALL
> editable fields, focuses Source, and leaves the dialog open. Failed saves retain
> all input; editing updates the same record. Show retained context outside cleared
> fields and never silently reapply it after saving. Preserve mutual/directional
> semantics, inverse labels, historical state, draft/committed-save distinction,
> and stable record IDs. Never infer mutual relationships from reciprocal links.
>
> Navigation and pending context must use story identity plus record IDs, not
> titles or display positions. Handle missing, trashed, or stale destinations
> without opening a same-numbered record from another story. Preserve selection,
> filters, graph state, unsaved edits, and the originating modal grab/focus where
> relevant. Do not save or discard drafts as a side effect of viewing information.
>
> Prefer no schema change for these UI tasks. If persistence requires one, use
> the ordered migration system, pre-migration backup, import/export validation,
> and recovery tests. Keep chapter/history mutation and validation in storage
> services; GUI callbacks must not write SQL or nest committing transactions.
>
> Run the established suite before the first change to establish the local
> baseline, focused tests during work, and the full suite after each completed
> task. Use the existing .build-env interpreter if available, otherwise the
> documented Conda environment. On this checkout the command is:
> `.\.build-env\Scripts\python.exe -m unittest discover -s tests -v`.
> Do not weaken assertions or reduce coverage merely to obtain a passing count.
> Exercise actual widgets/callbacks and modal navigation when testing UI behavior.
>
> Update README/help when behavior changes. Report changed files, exact checks,
> failures, remaining limits, and whether a migration or package rebuild occurred.
> Do not rebuild the distributed package until Task 9. Do not claim manual visual,
> physical DPI, or clean-machine checks based on widget tests or simulated scaling.

Small behavior-preserving extraction may precede a feature in the file being
changed. Keep imports used by existing callers/tests compatible where practical;
do not postpone all modularity until Task 8 or perform a broad up-front rewrite.

## Sequence

| Order | Task | Priority | Depends on |
|---|---|---|---|
| 1 | Protect unsaved quick-event input | Medium | — |
| 2 | Identify builds and prepare release verification (no release build yet) | High delivery | Baseline |
| 3 | Keep relationship creation and changes in event context | High | 1 |
| 4 | Turn chapters into a visible outline workspace | High | 3; preserve its event actions |
| 5 | Search all story content and open exact historical records | High | 4's exact chapter/event navigation |
| 6 | Add goal visibility for event planning | Medium | 3–5; reuse context/navigation |
| 7 | Complete the workflow visual and keyboard pass | Medium | Tasks 3–6 |
| 8 | Extract growing workflows and measure scale | Medium | Tasks 3–5 |
| 9 | Build and verify the final Windows release | High delivery | All accepted code changes from 1–8 |

Execute 1 through 9 sequentially in this shared checkout. Tasks 3–6 intentionally
reuse navigation contracts rather than implementing incompatible routes in parallel.
Task 7 is the cross-workflow pass; rerun affected interaction/appearance checks if
Task 8 changes those paths. Task 2 prepares release identity and scripts; Task 9
packages the final source, preventing an already-outdated mid-project release.

---

## Task 1 — Protect unsaved quick-event input

**Review finding:** The quick-event dialog closes on Back, Escape, or the window close control without checking dirty input. The full event and chapter editors already protect unfinished edits.

**Prompt for Sol**

> Fix the unsaved-input behavior in `story_atlas/quick_event.py`. First trace how quick-event creation is opened from the relationship workflow and how the full event and chapter editors handle dirty close. Give quick-event creation the same Save / Discard / Cancel contract on Back, Escape, and the window close control. Preserve the caller's pending relationship edit and modal focus: Cancel must leave the quick-event text and dialog in place; Discard must return to the original relationship editor without committing its pending change; Save must create the event and return the result to the caller. A failed save must keep all entered values. Add focused interaction regression coverage for these paths. Keep the change limited to this close/recovery workflow.

**Done when:** Cancel retains text and focus; failed save retains input; discard returns without committing the relationship edit; save follows the existing successful event-creation behavior.

**Implementation and test requirements:** Capture the original title, chapter ID,
and position, and compare all three for dirty state. An unchanged dialog closes
without prompting. Test Back, Escape, and WM_DELETE_WINDOW using the same close
path, plus Save/Discard/Cancel and a storage failure. Save-on-close must call the
creation callback exactly once and restore the caller's grab; failures must not
destroy either editor. If adding Ctrl+Enter, consume the event so it cannot also
save the parent relationship change. The pending relationship state must remain
byte-for-byte unchanged except its explicitly chosen new event.

## Task 2 — Identify the running build and verify releases

**Review finding:** The launcher prefers the packaged executable over current source, and the package was not rebuilt after source improvements. There is no in-app build/schema identification.

**Prompt for Sol**

> Make it clear which Story Atlas build is running and prepare a verifiable Windows release path. Inspect `Launch Story Atlas.cmd`, the About/help UI, schema-version source, and existing build scripts before editing. Add an About dialog or equivalent that displays the application version/build identity and supported database schema. Provide clearly named development and packaged launch paths so a developer can intentionally run `python main.py` and a user can intentionally run the packaged app. Prepare and document checks for clean first launch and upgrade against a disposable older database. Do not rebuild the release package in this task; the final build belongs to Task 9. Do not claim a pre-existing executable is current. Keep user data out of release checks. Report the source-mode checks and which packaged checks remain for Task 9.

**Done when:** The app identifies its build and schema; source and packaged launch paths are unambiguous; release steps check first launch and upgrade using disposable data; the release report distinguishes verified artifacts from unverified ones.

**Scope clarification:** This task prepares identity, launchers, and verification
scripts only. Task 9 performs the release build. Use one version source and build
metadata frozen at packaging time; distinguish application version, build identity,
supported schema, active database schema, and source/packaged runtime. Do not use
the current clock as an apparent build date or assume this checkout has Git.
Use a source fingerprint/manifest if no revision is available. Do not force an
unrelated schema bump just for build identification. Source mode must never
silently fall back to a stale executable; test paths with spaces and forwarded
arguments. Preserve upgrade-safe user-data locations. Test build metadata in
source mode now and packaged mode during Task 9.

## Task 3 — Keep relationship creation and changes in event context

**Review finding:** Starting a relationship from an event opens a blank form, loses participant choices, and requires event reselection. Changing an existing relationship at an event has a context-aware flow.

**Prompt for Sol**

> Improve the event-to-relationship workflow using `story_atlas/event_view.py`, `relationship_dialog.py`, and existing relationship/history APIs. Put explicit **Start a new relationship here** and **Change an existing relationship** actions beside the selected event. Carry the event context into the creation flow, show its chapter, title, order, and participants outside editable fields, and offer an explicit **Use this event** action for the relationship's beginning event. Suggest the selected event's participants without silently choosing either endpoint. Keep the originating event available as a clearly labeled return action, and allow the user to inspect the resulting relationship in that event context. Preserve the relationship dialog's successful-save contract (clear all fields, focus Source, remain open) and failure behavior (retain input). Reuse existing semantic validation and event-history behavior; do not introduce a parallel relationship model. Add focused interaction tests for participant suggestions, explicit event selection, return navigation, successful batch reset, and failed-save retention.

**Done when:** A writer can start or change a connection from an event and return to that event without finding it again; event selection is explicit; existing relationship save semantics still hold.

**Implementation and test requirements:** Open the contextual dialog without
switching the background tab to Relationships. Retain all character choices;
participant suggestions are a convenience, not a restriction. Missing/trashed
participants must not become selectable active endpoints. Return-to-event must
honor the existing unfinished-entry close contract. Keep the ID returned by the
successful save separately from editable fields; a success action must inspect
that exact connection at its event, including a connection that has ended in
Current. Do not resolve it through the current-only relationship list. Test two
successive additions, every field empty after each, duplicate-name participants,
an event with no participants, explicit event override, failed save, canceled
return, and historical inspection. No calendar/date model is introduced.

## Task 4 — Turn chapters into a visible outline workspace

**Review finding:** Chapters are represented by a filter over a flat event table. Empty chapters are hidden in that table, global and within-chapter numbering differ, and moving an event gives no direct destination route.

**Prompt for Sol**

> Make the Chapters & Events page communicate and support the chapter hierarchy. Inspect `story_atlas/event_view.py`, chapter storage/resequence code, and existing move dialogs before designing the smallest coherent change. Replace or augment the chapter dropdown with a left-side chapter outline that includes event counts, empty chapters, and a visible Unassigned group; show the selected chapter's summary and events on the right. Label global chronology order and within-chapter position distinctly wherever they are edited or displayed. After moving an event, confirm its destination and offer **Open destination chapter**. Before moving a whole chapter, show a before/after chronology preview and retain the existing atomic move/rollback guarantees. Do not add deletion; recovery semantics for chapter and event deletion are undefined. Add regression coverage for empty chapters, selection after moves, destination navigation, and failed/rolled-back moves.

**Done when:** Empty chapters can be found and opened; selection exposes summary and events; event moves clearly identify and open their destination; chapter resequencing can be reviewed before confirmation.

**Implementation and test requirements:** Retain All chapters and Unassigned
entries in the outline, chapter IDs, chronological ordering, and the existing
Unassigned ordering policy. Provide a single ID-based page navigation method for
Task 5 to reveal an event and its containing chapter, including when filters hide
it. Preserve per-story selection, reject stale IDs on story switches, and handle
duplicate chapter titles and empty stories. A destination link is shown only
after a successful event move and targets its committed chapter/event IDs.

The chapter-move preview is read-only: show old/new chapter and event ordering,
including Unassigned events if affected, and explain that relationship state may
change. Preview generation must neither write nor log. On confirmation, verify
the preview still represents the relevant chronology/history, then execute the
existing validated transaction; refresh/reconfirm a stale preview. Test Cancel,
changed data between preview and confirm, first/last chapter boundaries, and a
real timeline conflict rollback, not only a mocked helper exception. Preserve
event IDs and saved graph views. Do not replace chronology with a second ordering
system maintained independently by the GUI.

## Task 5 — Search all story content and open exact historical records

**Review finding:** Search omits chapter titles/summaries, event content, and historical/ended relationship states.

**Prompt for Sol**

> Extend global search so writers can find story context across the whole database. Inspect `story_atlas/retrieval.py`, the Ctrl+K search UI, record-navigation patterns, and relationship history storage. Add typed results for Chapters, Events, and Relationship history alongside existing results. Include a useful matching snippet; for history, label the result historical and show its effective event. Selecting a result must open the exact chapter, event, or historical relationship state rather than resolving an old match to the current relationship state. Keep story/database scoping intact and avoid broad scans on every keystroke if the current architecture supports a better query path. Add regression coverage for matches found only in an event summary, chapter summary, and ended relationship notes, including assertions that each opens the correct context.

**Done when:** Those three kinds of previously unsearchable content produce typed, understandable results and navigate to their exact records.

**Implementation and test requirements:** Specify search coverage as character
fields, current relationships, chapter titles/summaries, event titles/summaries,
and relationship baseline/dated-state labels and notes. An ended relationship is
not a deleted relationship. Include ended states of non-trashed records; exclude
Trash and uncommitted drafts by default. Do not expose a trashed character's
history through an otherwise active result.

Use stable result keys containing the type and record IDs: history results need
relationship ID plus dated-state ID, or an explicit baseline marker. Include the
event ID and Present/Ended label where applicable. “Before first event” is a
baseline, not a fabricated event. Open History with the matching state selected
and visible; selecting a result is read-only and must not open a correction editor
automatically. Label any later correction action as a correction to that state.
Deduplicate identical current/history hits deliberately without hiding distinct
matching states. Handle stale result removal and missing targets gracefully.

Debounce typing and cancel pending work on dialog close/story change before
considering new indexes or FTS. Preserve literal substring behavior, Unicode,
duplicate names, and existing Ctrl+K/Down/Enter/Escape navigation. Tests must open
results through the search UI and verify exact selection after event reordering,
baseline matches, ended matches, same-ID records in different stories, and an
unsaved profile with Save/Discard/Cancel. No new search schema is required unless
measurement demonstrates a need.

## Task 6 — Add goal visibility for event planning

**Review finding:** Goals are one free-form profile field, so the app cannot show cross-cast goals or relate an event's participants to their motives. The review recommends validating structured goal tracking later and preserving existing text verbatim.

**Prompt for Sol**

> Add a read-only cross-cast goals view and make participant profiles/goals easy to open while planning an event. Inspect profile overview, goal storage, participant selection, and event-draft lifecycle first. Keep each existing goals field as verbatim free text; do not parse it, split it, or migrate it into structured records. From an event's participant list, provide a direct route to each participant's profile/goals that preserves the unsaved event draft and returns to the same event. Add a cross-cast view that identifies the character for each goals entry and handles blank goals clearly. Do not add goal statuses or event-goal links in this task. Add focused regression coverage for draft preservation and unchanged goal text.

**Done when:** A writer can review participant motives without losing an event draft and can scan goals across the cast; existing free text remains unchanged.

**Implementation and test requirements:** Add one discoverable **Cast goals**
entry in the Characters workspace. Show active characters with name and ID,
verbatim saved goals, and a clear blank-goals state; label the view as committed
data. Reuse profile presentation rather than adding a second editable goals store.
Within a modal event editor, prefer a read-only participant profile/goals child
viewer. This avoids switching to a blocked main-window profile underneath a modal
grab. Closing the viewer must restore the event editor's grab, focus, participant
selection, title, summary, chapter, and position. Do not commit the event or save
unrelated profile edits to enable inspection. If existing profile routing is used
instead, it must meet the same invariant with an explicit tested return path.
Cover both new and existing unsaved events, multiline Unicode goals, duplicate
names, blank goals, and unavailable participants. Structured goals remain out of scope.

## Task 7 — Complete workflow-level visual and keyboard checks

**Review finding:** Several areas rely on broad More actions menus, nested modals, long ID-bearing labels, and colors without persistent text cues. The graph inspector split position resets on resize.

**Prompt for Sol**

> After the event, chapter, search, and goal changes are in place, do a focused visual and keyboard pass across those workflows. Use `VISUAL_REVIEW.md`, `VISUAL_DESIGN_PLAN.md`, and `UX_WORKFLOWS.md` as context. Ensure each task area has a clearly named primary action; current, historical, and unsaved states have persistent text as well as color; and Back labels identify their destination. Persist the graph inspector split width consistently with roster panes. Check chapter and event screens with long titles, duplicate names, empty data, both themes, and large text. Prefer the chapter outline over fitting long names into a short selector. Make only changes supported by a reproduced usability or layout issue, and add focused regression coverage for any changed interaction. Record which checks are automated and which require manual review; do not describe simulated DPI checks as physical Windows DPI validation.

**Done when:** State and focus are understandable without color alone; chapter names and empty states remain navigable at large text; graph split width persists; manual limitations are stated accurately.

**Implementation and test requirements:** Correct the finding's framing: existing
state indicators already use text as well as color in several places. Audit the
new workflows for gaps rather than presuming every existing cue is defective.
Add the graph pane setting to defaults, validation/loading, and saving; merely
writing an unknown JSON key will not make the current Settings loader restore it.
Restore once, clamp on resize, and never overwrite a user drag on every Configure
event. Verify restart, corrupt/out-of-range settings, compact windows, and that
zoom/selection remain unchanged. Preserve Tab/Shift+Tab and local shortcut scope
through child viewers and review dialogs. Use 900×600 and 1280×720, both themes,
large text, and existing simulated scaling cases as the automated baseline.

## Task 8 — Extract growing workflows and measure scale

**Review finding:** `event_view.py` combines page, event editor, and relationship-change chooser, while `graph_view.py` is also growing. Event participant and history data are scanned repeatedly. The review recommends targeted extraction and measured benchmarks, not a renderer rewrite.

**Prompt for Sol**

> Do a targeted maintainability and scale follow-up. First map the responsibilities in `story_atlas/event_view.py` and `graph_view.py`, and identify repeated participant/history scans on real view-composition paths. Extract the event editor and relationship-change chooser into focused modules only where this reduces coupling and preserves behavior; avoid a broad UI rewrite. Add reproducible benchmarks for stories with many chapters, events, and relationship-history states, recording dataset size, operations, and runtime. Use the measurements to identify a specific bottleneck before optimizing repeated scans. Do not rewrite the graph renderer without a measured limitation. Preserve the existing 100-character/300-relationship benchmark for comparison and add focused regressions for quick-event cancel, chapter selection after moves, and historical search if those are not already covered by earlier tasks.

**Done when:** Distinct event workflows have clearer ownership where extraction is justified; scale measurements cover chapters/events/history; any optimization is tied to measured evidence; graph rendering remains unchanged absent a demonstrated bottleneck.

**Implementation and test requirements:** Do not re-extract modules already
separated during Tasks 3–6. Use deterministic disposable data with at least 30
chapters, 300 events, 100 characters, 300 relationships, and 1,000 valid history
states. Retain the existing graph benchmark. Measure initial chapter display,
chapter switching, search, exact-history opening, and a chapter-move preview.
Record dataset seed, interpreter/hardware context, warm-up, repeated-run median
and slowest result, and whether rendering is included. Do not invent performance
guarantees; compare before/after on the same dataset when optimizing. Keep timing
benchmarks separate from correctness tests so machine speed cannot make the
normal regression suite flaky. End with the full regression suite and relevant
workflow/appearance checks after any extraction.

## Task 9 — Build and verify the final release

**Prompt for Sol**

> Package the accepted final Story Atlas source using the release identity,
> launcher, and verification work from Task 2. Run the full suite before building.
> Follow the existing locked build workflow and preserve user-data directories.
> Use an isolated data root for every packaged smoke test. Verify first launch,
> new/sample story isolation, reopen, migration of a disposable version-7 story,
> and opening a current version-8 story (or the final supported version if a
> justified migration was added). Check About/build identity, Goals, Chapters,
> contextual relationship entry, Tcl/Tk, Matplotlib resources, icons/assets,
> historical snapshot export, backups, and settings persistence. Record exact
> artifact paths, build identity, hashes, and test environment in a release report.
> Distinguish local packaged smoke checks from a clean Windows machine with no
> Python/Anaconda. If that machine is unavailable, report the clean-machine gate
> as outstanding. Do not publish or distribute the package as part of this task.

**Done when:** The final accepted source has identifiable package artifacts and
documented local verification, or a concrete build blocker is reported. A failed
build must not present a pre-existing executable/zip as the new release. A locally
verified package is not called clean-machine verified unless that check occurred.
If dependencies or tooling are unavailable, document the failure rather than
quietly changing the locked toolchain. Any source fix during package validation
requires rerunning affected tests and rebuilding before recording final hashes.

---

## Final review prompt for Sol

> Review the completed changes against `docs/reviews/2026-09-24/REVIEW.md` and this plan. Summarize each acceptance item as complete, incomplete, or intentionally deferred with evidence. Identify any migrations, user-data implications, or release artifacts. Run the project’s established regression suite and relevant interaction checks, and report exact commands and results. For the Windows package, clearly state whether it was rebuilt and which clean-install/upgrade checks were actually performed. Do not mark a task complete based only on a helper-method test when the finding concerns a user interaction path.

Maintain a completion checklist for Tasks 1–9. Distinguish source-ready, locally
package-verified, and clean-machine-verified status. Update the workflow-map
generator and render its PNG/SVG after UI paths change; inspect the render and
retain the 24 September baseline diagram as a dated comparison rather than
silently rewriting the historical review. Document unperformed user studies as
outstanding, not as automated-test successes.

## Product validation after implementation

Once the workflows are ready, run the review's short observed writing tasks with writers: create a scene with two participants; start a friendship there; change it to hostility later; move the later chapter; find the original friendship; recover an unsaved goal. Record completion, wrong turns, backtracking, and misunderstood saves. Treat task-time goals as unknown until a baseline has been recorded.
