# Story Atlas Preview — October 2, 2026

The local React / TypeScript / pywebview preview is implemented and tested on this Windows development machine. Python and SQLite own story facts, dated resolution, revisions, receipts, drafts, and backups. The existing Tkinter application and launchers remain available.

## Launch

Double-click:

`C:\Users\Jonathan\Documents\dnd_relations_db\Launch Story Atlas.cmd`

No additional setup is needed on this development machine: the pinned host dependencies are installed in `.build-env`, and `preview/dist` contains the built local frontend. The launcher reports missing assets or prerequisites and pauses on an error.

This is a source/development preview, **not an installer or a clean-machine release**. A different development checkout needs Python, Microsoft Edge WebView2, and the following build steps from the repository root:

```powershell
python -m venv .build-env
.build-env\Scripts\python.exe -m pip install -r requirements-preview.txt
cd preview
npm.cmd ci
npm.cmd run build
cd ..
```

Node is needed to build, not to run the built preview. Tested runtime: Python 3.13.9, Node 24.14.0, npm 11.9.0, pywebview 6.1 and the installed Windows WebView2 renderer. Frontend versions are pinned in `preview/package.json` and `preview/package-lock.json`; host dependencies are pinned in `requirements-preview.txt`.

## What works

- New story with an initial chapter and event; Open story; a separate Greyhaven sample; reopening the last story. Story filenames contain the initial title plus a unique suffix. Renaming a story changes its displayed title, not its filename.
- Chapter creation and title/summary editing; event creation within a chapter; event title, Planned/Happened/Unclassified status, purpose, summary, location, notes, and searchable removable participant tags. Selection alone never changes event status. Participant profile navigation has a return action.
- Character creation and the approved profile sections. Each changed field is reviewed as event-only or carry-forward. Python returns canonical values and named source events. Explicit blanks clear fields; later authored decisions remain authoritative.
- Directional and mutual connections, inverse perspectives, notes, event-only/carry-forward review, and later-state preservation. New duplicate pairs are rejected. All 50 Greyhaven connection records and their snapshot transitions are preserved, including existing multiple connections between a pair and directional legacy labels.
- Relationship graph with character selection, Full cast / Direct connections, drag, pan, wheel zoom, fit, reset, and profile navigation. Node positions are stored separately from story facts. Reset does not change connections or the story revision. Pan, zoom, and the direct/full toggle are session view state.
- World entries for species, roles, factions, locations, languages, beliefs, and titles. Add, describe, and rename entries. Profile/event assignments reference stable IDs; rename preserves dated scope and draft references. Case/space normalization never silently merges distinct names. Each profile reference field has one selected entry.
- Storybook, Gothic, Cyberpunk, Noir, and Medieval theme assets are bundled locally, including the existing Gothic stained-glass ornament. Theme choice persists per story.
- Durable drafts for editable workflows; Save / Discard / Stay navigation; Keep draft & close; recovery after restart. Writes use revision checks and request receipts. A successful save clears only its matching draft; transaction failures retain saved facts and pending work. Reload saved values lets a stale profile compare current saved values with its pending changes before retrying.
- **Story file → Back up story** and **Restore backup as a copy…**. Backups use SQLite's backup API, including every durable preview table. Restoration creates a different file and opens it.

Profile and connection edits use the shared scope-review dialog, one editor at a time. Finish or explicitly discard pending profile edits before opening a connection editor; simultaneous mixed profile/connection batch editing is not implemented.

## Disabled or unfinished

Legacy database import, browser-prototype import, JSON interchange, destructive operations, event/chapter moves, custom relationship-type design, post-save Undo, portrait importing, map editing, expanded World prose/lore, installer packaging, and cloud features are not exposed. World entries are added on the World page; inline creation from a profile selector is not included.

The sample's event statuses remain Unclassified. Its character profiles are baseline template content, not reconstructed historic profiles. Participant tags are authored in this preview; the prototype sample fixture does not include a historical participant list.

The preview deliberately uses its own format, application ID `0x53415056`, version `10002`, and `.atlas-preview` extension. Unsupported files are rejected before changes. The current Tkinter editor explicitly rejects preview files; older legacy migration code also rejects the higher format version. Existing user databases have not been migrated. Earlier disposable `10001` files from this implementation session are unsupported; no user story was created in that intermediate format.

## Files, reopening, and recovery

Normal launch stores files outside the repository:

- Stories: `%LOCALAPPDATA%\StoryAtlasPreview\stories`
- Backups: `%LOCALAPPDATA%\StoryAtlasPreview\backups`
- Last-story preference: `%LOCALAPPDATA%\StoryAtlasPreview\settings.json`

The **Story file** menu shows the current story's full path. **New / open… → Open story…** opens the stories folder. A missing last-story path shows an error and leaves new/open/restore choices available. Canceling a picker creates nothing.

To restore, choose **Story file → Restore backup as a copy…** and select a backup. This is available from the welcome screen too. A new `restored-…atlas-preview` file is created in the stories folder; the source and existing story are preserved. To inspect a backup without editing the backup itself, use Restore rather than Open.

Pending work lives in the story file, separate from saved facts. **Recover pending edits** lists other editor contexts. The last character/event context recovers its draft when reopened. Draft recovery does not commit changes automatically. With pending work, closing offers Save, Discard, Stay, and Keep draft & close. A forced interruption can lose keystrokes that have not yet reached the bridge; the UI distinguishes “Keeping draft…” from “Draft kept on disk.”

The title-bar X now cancels the native close event immediately and requests the frontend decision asynchronously, avoiding a WebView2 UI-thread deadlock. Clean editors close directly; pending edits offer Save, Discard edits, Stay, and Keep draft & close. Closing waits for draft writes and a saved resume context. Reopening restores the selected page/event/character, retained modal draft when applicable, pane scroll positions, collapsed chapters, and the expanded World-details section. Save errors keep the window open. Repeated X presses do not schedule duplicate destruction.

Close regression evidence: `tests/test_preview_close.py` verifies nonblocking dispatch and idempotent destruction; the combined close/store suite passes 20 tests. Native `x-close`/`x-reopen` stages exercise actual FormClosing, Stay, repeated X, retained drafts and scroll restoration. `build-verification/close-save-final` verifies Save via scope review, exit, committed values on restart, and cleared drafts. The `x-clean` stage verifies normal native exit without pending edits. Use fresh disposable sample homes for each paired scenario; these scenarios write fixed sentinel values and are not designed to rerun against their already-saved result.

Developer smoke tests use isolated homes under `build-verification/preview-*`, never the normal story directory. `preview_main.py --home <directory>` selects an isolated data root; `--story <path>` opens an explicit supported preview file.

## Five-minute walkthrough

1. Launch the preview. Enter a title and **Create story**, or choose **Try Greyhaven sample**.
2. On **Story**, rename Opening scene, write its purpose and summary, and Save event. Add a chapter and two more events. Choose an event to work at.
3. On **World**, choose Locations, add an entry, and save it. On **Characters**, create two characters. Choose the location and change age or summary. **Review changes**; check age to carry it forward and leave location unchecked. Save, then choose the next event to see the continuing and event-only behavior.
4. On **Story**, add a participant, save, open their tag, and return to the event. On **Relationships**, use **Add connection**, select a type and scope, review, and save. Explore the graph. Edit the connection at one event with carry-forward unchecked, then check that its earlier continuing state resumes afterward.
5. **Back up story**, close, and launch again. Verify the selected story and saved work. Make a pending edit and choose **Keep draft & close** to try recovery. Use **Restore backup as a copy…** to reopen the backup independently.

## Verification evidence

All checks used disposable files and the local development environment.

- Focused Python suite: **53 tests passed, no failures or skips** across `test_preview_store.py`, `test_profile_history.py`, `test_database.py`, `test_recovery.py`, and `test_chapters_goals.py`. Evidence: `build-verification/preview-backend-tests.log`.
- TypeScript checks and esbuild production bundle: `cd preview; npm.cmd run build` passed. The build copies approved prototype CSS/themes/ornaments without modifying those source assets.
- Actual WebView2 host acceptance in `tools/preview_native_smoke.py`: new story; chapter/event/character creation; both profile scopes; participant return navigation; World creation/rename; directed connection; event-only connection reversion; graph full/direct selection; backup; pending-close prompt; clean close; separate-process restart; recovered draft save. Final workflow results: `build-verification/preview-final/create-result.json` and `reopen-result.json`.
- Native injected storage failure: the UI displayed an error, previous committed content and its draft survived, and retry saved successfully. Native forced process exit after draft persistence: relaunch recovered and saved the pending content. Evidence: `build-verification/preview-final/failure-result.json`, `crash-result.json`, `recover-crash-result.json`. The crash stage intentionally exits without cleanup and is not expected to return a normal success exit code.
- Native compact layout: **900×600**, Storybook and Gothic, all four pages, full graph bounds and visible graph actions, and reachable review Save/Back controls. Final evidence: `build-verification/preview-final/layout-result.json`. The full workflow also runs at 1280×800; manual native visual inspection used 1360×900.
- Manual native input verified node dragging, wheel zoom, background panning, fit, and reset. SQLite inspection confirmed the dragged layout was durable and reset changed the layout to `{}` while keeping the fact revision at 17. The Windows automation helper subsequently timed out during final window cleanup; a disposable test window may remain open.
- New/sample isolation, every Greyhaven connection snapshot, duplicate/invalid connections, request reuse, stale writes, invalid fields/references, failed transactions, draft isolation, legacy format rejection, missing paths, safe filenames, worker serialization, and restoration to a different file are covered by backend tests. Backup comparison includes every table with active WAL state. Picker cancellation is tested at the bridge boundary with a canceled picker result.
- Runtime resource inspection in the real host found only loopback asset requests. No external fonts, scripts, services, or browser localStorage are required. Networking was not physically disabled; offline installation and a clean machine without Python/Node/WebView2 were **not tested**.
- `git diff --check` passed. No push, merge, reset, or overwrite of an existing story was performed. Pre-existing prototype/backend edits were preserved.

Run native checks in order with a fresh disposable home:

```powershell
.build-env\Scripts\python.exe tools\preview_native_smoke.py --home build-verification\my-preview-check --stage create
.build-env\Scripts\python.exe tools\preview_native_smoke.py --home build-verification\my-preview-check --stage reopen
.build-env\Scripts\python.exe tools\preview_native_smoke.py --home build-verification\my-preview-check --stage failure
.build-env\Scripts\python.exe tools\preview_native_smoke.py --home build-verification\my-preview-check --stage crash
.build-env\Scripts\python.exe tools\preview_native_smoke.py --home build-verification\my-preview-check --stage recover-crash
.build-env\Scripts\python.exe tools\preview_native_smoke.py --home build-verification\my-preview-check --stage layout
```

## Next highest-priority work

### UI fidelity correction — October 2

The first React pass omitted several approved presentation details. The preview now restores the full-height Story outline with chapter numbering, collapse controls and chapter-specific Add event actions; the Story heading and integrated participant relationship shortcut; compact search-to-add participant tags; the chapter-grouped timeline on Characters/Relationships only; the graph's binary scope switch, portrait/age/race/role inspector, fit/home icons, and alphabetical cast arrangement; full-width character sheets and consistent masthead sizing; and both themed World margins. Internal database IDs and implementation-oriented copy were removed from routine profile/cast UI.

Verification: frontend type check/build passed. The native create/save/reopen flow passed in `build-verification/ui-parity-flow2`, including both profile scopes, scoped relationships, participants, World rename, backups, and recovered drafts. The final compact native checks passed in `build-verification/ui-parity-native/layout-result.json` for Storybook/Gothic, all pages, constant masthead height, full-height outline, grouped timeline, graph switch and inspector, and accessible review actions. Story and Relationships were also visually inspected in the native host.

This corrects presentation and supported navigation; it does not implement the previously deferred move/delete operations, inline World creation, portrait import, or simultaneous profile/connection batch review. Those remain functional differences from the approved prototype and should be addressed before claiming full prototype parity. Restart the preview to load rebuilt assets; normal user stories are unchanged by these checks.

Package this tested preview and validate it on a clean Windows machine with networking disabled, including a deliberate WebView2 prerequisite strategy. Bundle `preview/dist`, `prototypes/phase2/greyhaven.json`, the Python host, and pinned dependencies. Keep the preview format separate until a tested importer preserves introductions, temporal references, and recovery data from legacy stories. Before introducing any preview schema upgrade, add a SQLite-safe pre-upgrade backup and migration/rollback tests.

Implementation map: `preview_main.py` exposes the allowlisted bridge and native lifecycle; `story_atlas/preview_worker.py` owns the single database worker; `story_atlas/preview_store.py` owns the isolated format, transactions, resolution, and backup; `preview/src` owns rendering and transient interaction. The pure profile resolver and existing relationship semantic helpers are reused. Do not replace preview persistence with prototype localStorage or route writes through legacy transaction-owning methods.
