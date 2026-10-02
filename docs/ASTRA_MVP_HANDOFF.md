# Astra handoff: usable Story Atlas MVP

Prepared October 2, 2026. Target: a usable local Windows preview when Jonathan returns from work. This is a prioritized execution plan, not a guarantee that the full scope fits one workday.

## Execution checkpoint — October 2

The local development preview has been implemented. Start with [MVP_DELIVERY.md](MVP_DELIVERY.md) for the launcher, supported scope, storage paths, walkthrough, and precise verification limits. The original assignment below remains the acceptance reference.

| Gate | Result |
| --- | --- |
| 1 — Native application | React/TypeScript assets built locally; actual pywebview/WebView2 launch, allowlisted bridge, serialized SQLite worker, sample display and relaunch verified. Separate preview launcher added. |
| 2 — Character loop | Stable IDs, dated scopes/provenance, revisions, receipts, durable drafts, matching cleanup, conflict/error paths, actual close/reopen and forced-interruption recovery verified. |
| 3 — Story workflow | New/open/sample; chapters/events; status/purpose/summary/notes; participants and return navigation; shared event context and durable outline implemented and tested. Moves/deletion remain unavailable. |
| 4 — Connections/graph | Preserved Greyhaven records, Python temporal resolution, direction/inverses, duplicate validation, atomic reviewed edits and drafts; native event-only reversion/restart; drag/pan/zoom/fit/reset verified. Deletion/custom type design remain unavailable. |
| 5 — World | Stable identities, single-choice assignments, creation/descriptions/rename, scoped references and backups implemented and tested. No destructive World operations. Existing themes and Gothic ornament reused. |
| 6 — Trustworthy enabled scope | Separate identified format, legacy editor guard, all-table SQLite-safe backup/restore, focused regression suite, native error/recovery tests and compact layouts pass. Source/development environment only; clean-machine packaging, physically offline installation, and per-monitor DPI checks remain unverified. |

The delivery is a usable local preview, not an installer. JSON interchange, legacy/prototype import, destructive/move operations, and deferred artwork/map/lore features are not exposed. Profile and connection review use one editor at a time rather than a combined batch. No existing user story was upgraded; intentional working-tree changes were preserved.

## Assignment

Build and verify the smallest complete version of the approved web interface backed by Python and SQLite. Work through the gates below in order. Make routine implementation decisions independently, record them, and keep going through implementation and verification. Prioritize a working launch/edit/save/reopen loop over broad unfinished scaffolding.

Do not redesign the approved screens. Do not spend this pass improving illustrations. Do not substitute browser localStorage for durable story storage. Keep the existing Tkinter application available.

## What Jonathan should be able to do tonight

1. Double-click a clearly named launcher for the new preview.
2. Create a new story or open a story previously created by this preview. Try a separate Greyhaven sample without changing any existing story.
3. Create chapters and events, select an event, and describe what happens there.
4. Create characters and edit their profiles. Review whether each change applies only to this event or carries forward.
5. Create and edit connections at an event, and explore them in the relationship graph.
6. Close the app, reopen the same story, and find saved content intact. Recover pending edits or explicitly discard them.

The first five steps are useful only if step six works. Never show “saved” before the database commits.

## Read first and preserve

- `docs/WEB_UI_ARCHITECTURE_DECISION.md`: accepted React + TypeScript / pywebview / Python / SQLite direction and integration constraints.
- `docs/PHASE2_UI_ROADMAP.md`: approved product behavior.
- `prototypes/phase2/`: visual and interaction reference; not the production data model.
- `story_atlas/profile_history.py` and `tests/test_profile_history.py`: initial opt-in persistence service and eight focused tests.
- Existing database, history, chapters, events, drafts, recovery, and distribution code before reusing their APIs.

Current starting state:

- Existing shipping UI is Tkinter. There is no completed React/pywebview bridge.
- The browser prototype uses localStorage; its data is not automatically migrated.
- Experimental profile history supports event-only and continuing field values, atomic saves, source metadata, stale-read rejection, and matching draft cleanup.
- Its schema is opt-in, separate from production migrations. World references are text, export/import and legacy Undo do not cover it, and legacy introduction constraints are not integrated.
- Forty-one relevant tests passed at the previous checkpoint. Rerun against your changes; this is not evidence for code you have not tested.
- The working tree contains intentional uncommitted prototype, documentation, and backend work. Inspect `git status` and preserve it. Do not reset or replace those changes.

## Scope and stopping rules

**Required core:** local launch, new/open/sample, chapter/event creation and selection, character creation and dated editing, safe saving, close/reopen, visible errors, and recovery of pending edits.

**Target complete MVP:** add relationship creation/editing and graph exploration, participant tags, and shared World choices. Finish a feature through its acceptance checks before beginning the next one.

**Defer if needed:** event/chapter moves and deletion, destructive World operations, full import from older databases, prototype import, installer distribution, map editing, expanded lore tools, illustration polish, cloud sync, and custom relationship-type design. Deferred controls must be hidden or clearly unavailable, never silently simulated.

If the full target cannot be verified, deliver the tested core with an explicit missing-feature list. Do not call it the complete MVP. A smaller working build is the fallback, not permission to stop after planning or scaffold generation.

## Gate 1 — Boot a real application early

- Inspect available runtimes and dependency files. Add pinned frontend/host dependencies using existing repository conventions.
- Create the React/TypeScript frontend and pywebview entry point without changing the existing launcher's behavior. Bundle local assets; no CDN fonts or scripts.
- Port the approved masthead, themes, navigation, and character editor shell first. Keep World → Story → Characters → Relationships order.
- Implement an explicit bridge with structured success/error results. Expose only intended application commands.
- Use one database worker/queue. Create, use, and close its connection on that worker. Bridge calls must not share SQLite connections across threads.
- Show loading, storage errors, and retry/reload paths. Prevent duplicate submissions while a command is pending.
- Provide a separate `Launch Story Atlas Preview.cmd` (or equally clear name) with a useful error if prerequisites are missing.

**Pass:** launch the actual native host, request sample data through the bridge, display it, close cleanly, and relaunch. A standalone browser screenshot or mocked bridge does not satisfy this gate.

## Gate 2 — Complete the character save loop

- Implement workspace loading, stable character IDs, revision-aware character creation, profile reads, and profile writes.
- Add request IDs/receipts for retryable writes, especially creation. A repeated request must not create a second character; reusing a request ID with different content must fail.
- Reuse the field resolver and extend its validation as needed. Do not call transaction-owning legacy methods inside an outer transaction and assume the result is atomic; extract transaction-free writes where needed.
- Keep the reviewed event-only/carry-forward review interaction. Explicit blank values clear fields. Later authored decisions remain authoritative.
- Return canonical saved values and their sources from Python. Do not independently resolve story history in React.
- Add durable, versioned drafts keyed by story/character/event context. Save clears only its own committed draft.
- Handle Save / Discard / Stay on navigation and shutdown. Persist drafts before accepting close; stale revisions preserve pending work and explain the conflict.

**Pass:** create a character, edit different fields with both scopes, save, change events, close the actual host, reopen the same file, and verify values and provenance. Test duplicate creation requests, stale writes, invalid fields, and an injected storage failure. Failed saves must preserve both previous committed data and pending edits.

## Gate 3 — Make a new story usable

- Provide New story, Open preview story, and Try sample. Store user files outside the code/build folder. Canceling a picker must create nothing.
- Initialize a new story with a valid first chapter/event; let the user rename both.
- Persist story title, chapters, event title/status/purpose/summary/notes, chapter membership, and event order using stable IDs.
- Port the full-height outline and event editor. Purpose precedes summary. Use searchable participant tags with remove controls and profile navigation.
- Share the selected event across Story, Characters, and Relationships. Preserve return-to-origin context.
- Never mark an event Happened merely because it was selected. Avoid inventing statuses for imported records.
- Keep move/delete controls unavailable until previews and all new references are supported. Existing legacy event deletion reassigns history; it is not the approved prototype behavior.

**Pass:** start empty, add two chapters and several events, add participants and event details, navigate to a profile and back, then restart and verify the complete outline and selected story.

At this point the required core can be delivered if later gates are blocked. It must include Gate 6's recovery and launch checks for every enabled feature.

## Gate 4 — Connections and the graph

- Adapt existing relationship semantics, preserving directional/mutual distinctions and supported multiple connections between the same pair.
- Add event-only scope alongside continuing states; preserve legacy continuing history. Python resolves active connections at the selected event.
- Implement create/edit with validation, atomic commits, revisions, drafts, and clear errors. Include deletion only if its references and temporal behavior are tested.
- Port the approved graph interactions: node dragging, background panning, wheel zoom, zoom-to-fit icon, home/reset-layout icon, and Full cast / Direct connections switch.
- Keep the cast sidebar hidden in Relationships. Show the actual event name and selected character summary with scrollable connections. Keep Open profile and Add connection together.
- Persist graph layout separately from story facts. Reset layout must never modify connections.

**Pass:** create a connection, change it for one event, verify the continuing state resumes afterward, restart, and verify it again. Test direction, invalid endpoints, and duplicate rules. Exercise drag/pan/zoom/reset and return navigation through the real UI.

## Gate 5 — Shared World choices

- Implement World entries with stable IDs and names/descriptions for the reviewed categories. Do not use display names as reference identity.
- Connect profile and event selectors to Python-backed choices. Keep single-choice language/belief/title fields as reviewed.
- Convert experimental text assignments deliberately; do not silently merge normalization collisions.
- Add entry creation and description editing first. Rename only when baseline and dated references resolve correctly. Delete only after every relevant history/draft reference is checked; otherwise leave it unavailable.
- Preserve current themes, including Gothic stained glass. No new decorative art work in this pass.

**Pass:** create and select a World entry, restart, rename it if enabled, and verify all referenced events retain the same assignment and scope.

## Gate 6 — Make the enabled scope trustworthy

Complete these checks before calling any build ready for use:

- Version and identify preview databases. Do not silently upgrade existing user stories. If legacy import is incomplete, provide new/sample/open-preview only and reject unsupported files with a clear message.
- Do not allow the legacy editor to unknowingly edit unsupported preview data. Enforce compatibility detection or use a separate preview format/storage boundary; a README warning alone is insufficient.
- Include every enabled durable table in backup and restore. Use SQLite-safe backups, not a raw file copy of an active connection with possible WAL state.
- Provide a reachable backup action and verify restoration to a different file. If JSON import/export is not extended, leave it unavailable in this preview; never offer an export that silently omits new history.
- Run focused backend tests plus relevant existing regression tests, frontend build/type checks, and real host smoke tests. Add tests for meaningful persistence and boundary failures, not tests that merely mirror markup.
- Verify offline runtime with built local assets. Record whether testing used the development environment or a packaged build; do not claim clean-machine support without testing it.
- Test closing with pending edits, restart after a forced interruption on a disposable file, missing story paths, and write failures.
- Verify the usual desktop layout and smaller windows. No clipped save buttons, inaccessible dialogs, or fake enabled navigation.

**Pass:** a fresh preview story completes the enabled workflow, survives restart, and can be backed up and restored without losing dated fields, relationships, participants, or World assignments that the build exposes.

## Delivery to Jonathan

Create `docs/MVP_DELIVERY.md` containing:

1. Exact launcher path and any one-time prerequisite instructions.
2. What works, what is disabled, and what is unfinished.
3. Where story files and backups live, and how to reopen/restore them.
4. A five-minute walkthrough: new/sample → event → character edit → save → connection if enabled → close/reopen.
5. Checks actually run, their results, and any unverified platform assumptions.
6. The next highest-priority task, with enough context to resume.

Update this roadmap with completed gates and remaining items. Keep implementation changes reviewable and run `git diff --check`. Do not merge, push, overwrite existing story files, or remove the legacy app as part of this handoff. Report the actual result candidly; a launchable, verified subset is more useful than an untested claim of completion.

## Copyable kickoff prompt

> Work in `C:\Users\Jonathan\Documents\dnd_relations_db`. Read `docs/ASTRA_MVP_HANDOFF.md` and the linked architecture decision, inspect the current working tree, and execute the roadmap toward a usable local MVP. Preserve all existing work and the approved visual design. Implement and verify complete workflows in priority order, using Python/SQLite as authoritative storage. Continue through the available gates without stopping at a plan or scaffolding. If a dependency or integration is blocked, make independent progress on the remaining core and report the precise blocker. Do not claim an untested feature works. Finish with the preview launcher, `docs/MVP_DELIVERY.md`, test evidence, and a clear list of remaining limitations. Do not push or merge.
