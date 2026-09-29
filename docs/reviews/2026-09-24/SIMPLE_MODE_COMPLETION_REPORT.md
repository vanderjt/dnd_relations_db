# Graph-centered Simple mode

24 September 2026 · Story Atlas 0.10.0 · schema 9 · portable story format 5.

## Scope and review baseline

Implemented Simple as another presentation of the existing database, with the
Advanced tabs retained. Read the README, market/competitive assessment, UX
implementation, independent Astra review and corrective reports. Verified the
three Astra corrections through their existing real-Tk regressions: Current
correction includes ended states; graph History retains the exact historical
context; nested scrolling reaches the nearest container. Those fixes remain.
The checkout has no Git repository or applicable AGENTS.md.

No existing user story or settings file was used for development or verification.
No renderer rewrite, profile-history system, structured goals, cloud service or
generated sample insertion into existing stories was introduced.

## Workflow-to-implementation map

| Agreed workflow | Implementation and evidence |
|---|---|
| Start a story; retain Advanced | `story_setup` publishes a new database exclusively, with title, chapter and initial event. Welcome defaults new settings to Simple; old settings without a mode remain Advanced. The mode selector persists preference and checks unfinished tasks. `Projects` still owns switching and recovery. Setup/isolation and mode-cancellation tests cover this. |
| Provisional character | `simple_profile` hosts the complete `ProfileEditor` and `DraftController`. The graph adds ID -1 only in memory, with dashed styling and an unsaved label. Save atomically commits the character, introduction reference and participation; Cancel/Discard removes the provisional node. Position/pin transfer uses the new stable ID. Name-only save, goals draft, cancellation and position tests pass. |
| Introduction chronology | Migration 9 adds a deferred foreign key to the event ID and a separate constrained narrative role. Legacy characters default to an undated introduction and neutral role. Shared `History.validate` checks active connections at all event boundaries. Advanced event/chapter moves, history writes, profile changes, batch saves and Trash restoration use it. Imports validate the same invariant. Tests cover visibility, planned cast, early links, reordering rollback, migration, imports, Trash and backups. |
| Explicit reassignment | Profile introduction changes are deliberate and validated. Event removal requires a replacement and an internal review naming affected introductions, states, participants and draft references, including Trash. The service rechecks the review, backs up, reassigns references and validates the whole operation. Conflicting states cannot merge. Tests cover Trash/draft reassignment and complete rollback. |
| Ordered one-to-many selection | `selection` stores ordered IDs; duplicate names remain distinct. Shift-click toggles IDs without initiating a drag. Keyboard controls provide Inspect, Select/remove, Make source and Clear. The first ID supplies every proposed pair's source. Tests cover source changes, deselection, duplicate names, directional and canonical mutual saves. |
| Batch review and commit | `simple_batch` uses the shared normalizer, searchable type/character selectors and `RelationshipStore.batch`. Preview uses the actual transaction path and rolls back. Commit writes the full reviewed batch in one transaction. Failure retains fields and selection; explicit target exclusion is available. Success clears every field, notes, targets and ordered selection, focuses Source and keeps the task open. Tests exercise both success and conflicts. |
| Exact connection inspection and changes | The existing renderer keeps separate arrows and IDs. The inspector lists individual visible connections; selection controls also expose saved connections including ended ones. `StateEditor` provides before/after review in the same pane. Correction resolves the exact effective state at the inspected time; Current includes ended states. Change at an occupied event explicitly offers correction. Ending and moving the whole connection to Trash are separate. Existing and new tests compare untouched fields and historical IDs. |
| Events and chapters | `simple_event` creates events using the existing chapter/event services and creates chapter plus first event atomically. Existing cast, positions and relationships carry forward. Finish/Continue opens the next event or a new event task. Events remain editable. Committed-event messages distinguish saved records from later unfinished input. Tests verify carry-forward and event/chapter commits. |
| Timeline and graph | `simple_timeline` draws chapter bands, markers and a snapping playhead. Exact chapter/event selectors and Previous/Next remain. Drag previews are labeled; graph rendering is debounced at 120 ms. Navigation never reorders or writes story records. Save/Discard/Stay guards restore the selected time on cancellation. Hidden future positions and pins are retained. Mouse background pan, pointer zoom, node dragging, shift-selection, keyboard node movement, Fit, filters and named views retain NetworkX/Matplotlib. Tests check no SQLite writes during scrubbing, stable layout/zoom, real Matplotlib input dispatch and 100/300 graphs. |
| Shared persistence and exports | Existing databases are backed up before the ordered transactional migration. Full export/import includes narrative role, introduction IDs and title metadata; older formats remain accepted. Graph exports retain time/filter/profile/planned visibility metadata. Graph snapshot import deliberately creates a static undated story, as documented; full exports preserve chronology. Assets, settings, backups, Trash and user data remain outside the packaged application. |

## Validation and release evidence

Final release validation passed. Earlier diagnostic runs are intentionally
retained in `build-verification`; the authoritative final logs are
`simple-release-build.log` and `simple-release-smoke.log`.

- `tests/test_simple_mode.py`: 15 focused tests, with domain transactions and real
  Tk/Matplotlib interactions. The dense fixture has 100 characters and 300 stored
  links, including reverse connections. A focused run measured 0.319 s to refresh
  and draw on this machine; timings are descriptive, not a usability benchmark.
- Existing suites retain Advanced mode, relationship semantics/history, portraits,
  recovery, migrations, import/export, navigation, nested wheel dispatch, long
  text and appearance coverage. New format/onboarding expectations were updated;
  legacy preservation assertions were retained.
- Tests normalize Tk scaling for the new 900×650 / 14-point geometry check.
  This is a simulated layout check, not a physical Windows DPI test.
- Live Windows inspection used the computer-use skill and a disposable fixture:
  planned cast had dashed outlines and no connections; the graph showed separate
  role labels; New character displayed a provisional node; typing a name and
  saving replaced it with a stable saved character in the same position.
  Inspection exposed an overfull pane. Secondary graph/selection controls were
  collapsed and the inspector was mounted in its proper container. A second live
  pass verified the improved graph/pane layout and name-only save.
- Subsequent compact-header, scrollable-introduction, keyboard and secondary-action
  adjustments are covered by automated tests; that exact final UI revision was
  not re-inspected across native display sizes.

## Final package

- **175 tests passed in 83.543 seconds** in the final build. Simple 100/300 refresh
  and draw measured **0.493 s**; the existing Advanced benchmark measured its
  independent initial/focus timings in the same log.
- **Packaged smoke passed**, `ok=true`, `frozen=true`, on Windows 11 build 26200,
  CPython 3.13.9 x64, Tcl/Tk 8.6.15. Python/Conda/Tcl overrides were cleared and
  PATH was restricted by the existing smoke script. This is local packaged
  verification, not a clean-machine test.
- Smoke includes first-story setup/reopen, sample isolation, Advanced workflows,
  historical correction/export, resources/portraits, backups, migration, and
  Simple provisional save, introduction visibility, planned cast without links,
  and reviewed full-batch commit/reset/stay-open.
- The withdrawn smoke window needed an explicit lazy graph refresh before its
  post-save assertion. That harness correction passed in source and frozen runs;
  no application save behavior was changed for it.
- Additional executable checks passed for exact story-title export/import and
  static graph-snapshot import with introduction metadata.
- Source and packaged fingerprint match:
  `403c0fa389999d0f404b115645e8bf5ba76a70bd1fe23c37d69f2657711b17cc`.
- ZIP: `dist/StoryAtlas-Windows-x64.zip`, **42,898,382 bytes**.
  SHA-256: `7B9C88BDDF057514E8CB02D04258E929A1A38500DB4C485D18022C14FAF16749`.
- Executable: `dist/StoryAtlas/StoryAtlas.exe`.
  SHA-256: `EB9BA94CB3E9C64D6EF742C83477EA3711AF3532944A05A70FDA676D8700EF4D`.
  Distribute the entire ZIP/folder,
  not the executable alone. Machine-readable evidence is in
  `build-verification/packaged-smoke.json`; the ZIP checksum is stored alongside
  the ZIP in `dist`.
- All live inspection windows were closed after the disposable checks. No
  application source changed after the successful final build.

## Remaining limitations and checks not performed

- Dense labels can overlap around highly connected characters. Focus/filter views,
  the connection list and exact IDs provide access to all records. This is a
  concrete Matplotlib presentation limitation; it does not justify replacing the
  renderer in this change.
- Very narrow panes and large fonts require scrolling/resizing or collapsing
  secondary controls. Long timeline chapter names are shortened in the bands;
  exact selectors retain their full labels and IDs.
- Event removal requires a different replacement event. Conflicting states at the
  replacement must be resolved explicitly; no merge or chronology rewrite is
  inferred. Event-removal recovery uses its pre-removal database backup.
- Profile drafts are crash-recoverable. Event, relationship-entry and state tasks
  retain failed input and guard navigation but do not gain crash-recovery drafts.
- Narrative role, profile and goals remain current attributes. Graph snapshots
  are static subsets and are not substitutes for full story exports or backups.
- Native light-theme and full end-to-end batch/timeline testing in this pass used
  automated Tk interactions. Physical 125/150/200% Windows scaling, per-monitor
  transitions, screen-reader output, a fresh Windows machine without Python, and
  a storyteller usability study were not performed.
