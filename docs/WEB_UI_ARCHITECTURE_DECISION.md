# Web UI and Python desktop architecture decision

Decision date: October 1, 2026. Status: direction accepted; production implementation and distribution validation remain pending.

October 2 implementation update: the selected architecture now has a working native development preview with a single SQLite worker, explicit bridge commands, atomic revision/receipt/draft handling, stable World references, temporal profiles/connections, and complete SQLite backups. See [MVP_DELIVERY.md](MVP_DELIVERY.md). The historical audit and proposal below describe the starting point; packaged clean-machine distribution and legacy-format integration are still pending.

Story Atlas will pursue a React and TypeScript interface hosted in pywebview, with Python owning application logic and authoritative state and SQLite retaining local story data. The user accepted this direction after comparing Tauri, pywebview, NiceGUI, Electron, and a browser-based local application.

This record captures the discussion and its rationale. It does not claim that the existing Tkinter application has been migrated or that an offline web desktop build has been verified.

## User goals

- Use web-development tools to create an attractive interface for data entry and visualization.
- Keep all story rules, validation, and authoritative application state in Python.
- Give friends a simple executable to launch, without requiring a development environment.
- Run without an internet connection, with stories stored locally.

Windows is the initial distribution assumption. Supporting other operating systems was not decided.

## Selected architecture

The intended flow is React interface → pywebview JavaScript–Python bridge → Python application layer → SQLite.

React handles layout, forms, visual feedback, and graph rendering. Python handles character and relationship operations, chronology, validation, persistence, recovery, and authoritative application state. The frontend submits commands and displays results from Python rather than maintaining a second implementation of story rules.

Temporary presentation state can remain in JavaScript: hover effects, open menus, text being entered, and drag feedback. For example, the frontend can animate a node while dragging, then ask Python to accept and persist the final position. Durable drafts and saved data remain Python responsibilities. Any client-side validation is convenience feedback; Python must enforce the rules.

pywebview supports exposing Python methods through a JavaScript bridge and serving bundled static frontend assets with its internal HTTP server. A separate FastAPI or Flask application is therefore not required for this design. Local asset serving does not imply internet access. See the official [architecture guide](https://pywebview.flowrl.com/guide/architecture.html) and [bridge documentation](https://pywebview.flowrl.com/guide/interdomain.html).

The exact API contracts, state update mechanism, graph library, and handling of concurrent requests remain implementation decisions. Database access must respect Python thread ownership and transaction boundaries when bridge calls arrive.

## Alternatives considered

The assessments below reflect this project's priorities, not universal rankings of the frameworks.

| Option | Strength for Story Atlas | Tradeoff and decision |
| --- | --- | --- |
| React with pywebview | Direct use of web components and styling, with a Python desktop host and bridge. | Requires frontend tooling and a deliberate Python API. Selected for design freedom and fit with the existing Python code. |
| NiceGUI in native mode | Quickly builds forms, tables, and dashboards through Python controls and callbacks. | Customized graph interactions may require Vue or JavaScript component work. Strong alternative if writing the UI mostly in Python becomes the priority. |
| React with Tauri and a Python sidecar | Web desktop shell that supports bundling a separate Python executable. | Adds Rust tooling and sidecar process management. Viable, but those additional layers are not needed for the selected approach. |
| React with Electron and a Python process | Bundles a browser engine for a consistent rendering environment. | Larger distribution footprint and another runtime to maintain. A fallback if bundled browser consistency outweighs size. |
| Web UI with a local Python server in the default browser | Uses the friend's existing browser and avoids a desktop webview wrapper. | Browser-tab and backend lifecycles need coordination; less cohesive desktop experience. |

Tauri explicitly supports [external binaries including packaged Python applications](https://v2.tauri.app/develop/sidecar/). Electron documents its [desktop process model and web renderer](https://www.electronjs.org/docs/latest/tutorial/process-model).

## Why pywebview was chosen over NiceGUI

These options overlap: NiceGUI's native mode uses pywebview. The central choice is between a frontend we build directly with React and a UI driven through NiceGUI's Python framework. See [NiceGUI's native implementation](https://github.com/zauberzeug/nicegui/blob/main/nicegui/native/native.py).

NiceGUI is attractive for this application's routine data-entry screens. It provides Python-driven UI updates using Vue and Quasar, supports custom CSS, and allows custom Vue components. It can produce polished interfaces; appearance alone is not a reason to reject it. See its [foundations](https://nicegui.io/documentation/section_foundations), [styling support](https://nicegui.io/documentation/section_styling_appearance), and [custom component and packaging documentation](https://nicegui.io/documentation/section_configuration_deployment).

React with pywebview was preferred because the user specifically wants the flexibility of web-development tools. Story Atlas also needs coordinated graph selection, dragging, contextual tools, timeline navigation, and editing panels. Our assessment is that direct frontend development gives us more flexibility for these interactions, while an explicit Python boundary keeps domain rules reusable and testable.

The cost is maintaining two development environments and the interface between them. NiceGUI would reduce initial UI setup for standard forms, but specialized frontend components could bring web tooling back into that approach as well. No comparative performance or development-time benchmark was performed.

## Offline distribution requirements

Both approaches can be packaged for offline operation. All JavaScript, CSS, fonts, icons, images, and visualization dependencies must be included locally; production screens must not require CDNs, hosted APIs, or online asset downloads.

pywebview documents [PyInstaller packaging for built React assets](https://pywebview.flowrl.com/guide/freezing.html). Friends should not need Python, Node.js, or package managers installed. Node.js is a development/build dependency for the proposed frontend.

The final delivery format remains open:

- A portable executable is convenient to share. PyInstaller's one-file mode extracts bundled components at launch and may start more slowly.
- A setup executable can install application files and prerequisites, then provide a normal shortcut.

See [PyInstaller's packaging model](https://pyinstaller.org/en/stable/operating-mode.html). A single installer executable is not the same as a single portable application executable.

For the proposed Windows renderer, WebView2 availability must be handled explicitly. Offline operation on an already configured computer and offline installation on a clean computer are separate acceptance checks. NiceGUI's native mode does not remove this renderer dependency. See [pywebview's renderer requirements](https://pywebview.flowrl.com/guide/web_engine.html).

The initial pasted Tauri research was useful as an architectural starting point, but its small-download claims were not accepted as estimates for Story Atlas. Python, dependencies, assets, and any bundled renderer prerequisites all contribute to size. Its shell API/configuration example also needs updating for Tauri 2. Tauri's [Windows installer guide](https://v2.tauri.app/distribute/windows-installer/) explains the additional cost of offline WebView2 distribution. Actual size and startup time must be measured for our build.

## Relationship to the existing project

The current application uses Python, Tkinter, SQLite, NetworkX, and Matplotlib. Existing storage and domain logic are candidates for reuse, but their coupling to UI code must be assessed before migration estimates are made. SQLite story compatibility, backups, and recovery behavior should be preserved and verified during implementation.

The existing [Phase 2 prototype](../prototypes/phase2/README.md) is a separate browser design experiment using JavaScript modules and browser localStorage. Its visual and interaction ideas can inform the new frontend. Its browser-owned data model is not the accepted production state architecture; production operations must go through Python. This decision does not itself rewrite that prototype or change its documented scope.

## Proposed first implementation milestone

Build one end-to-end prototype before a broad migration:

1. Open a disposable copy of a story through Python.
2. Display an interactive relationship graph and a polished character-entry screen in pywebview.
3. Submit edits to Python, enforce existing rules, save through SQLite, and reload to verify persistence.
4. Package the application with all frontend assets and its required runtime components.
5. Test launch, editing, graph interaction, persistence, shutdown, and relaunch on Windows without Python or Node installed and with networking disabled.
6. Verify the selected prerequisite strategy on a machine without WebView2, and measure package size and startup time.

This milestone is a proposed validation plan, not completed work. Final packaging format, graph library, migration sequence, and estimates remain open until implementation evidence is available.

## Integration plan after the UI checkpoint

Repository audit: October 2, 2026. This section is an implementation plan, not a completed migration. The approved browser UI remains in `prototypes/phase2`; real stories have not been modified by this audit.

### What can be reused, and what is missing

| Prototype behavior | Existing Python/SQLite support | Integration work |
| --- | --- | --- |
| Character profiles and creation | `database.py: Database.save_character`, `models.py: PROFILE_FIELDS`, portraits, character types, validation | Reuse baseline character identity and metadata. Add age, health, armor, mana, language, belief, and title fields; add dated profile changes. Existing character fields currently hold one value, not a profile timeline. |
| Event-only / carry-forward profile edits | No profile-history table in migrations 1–13 | Add field-level history referencing stable character and event IDs. Python resolves values and reports their source. |
| Connections at events | `relationship_history`, `history_model.resolve`, `History`, semantic duplicate validation | Preserve full directional/mutual states and original record identities. Add explicit event-only scope; current history entries continue until superseded. Keep legacy multiple connections per pair. |
| Chapters, events, participation | `Chapters`, `Events`, `story_events`, `event_participants` | Reuse IDs and transactional sequence changes. Add event status, purpose, World location reference, and notes. Extend chronology previews to profile history and arbitrary destinations. |
| Shared World lists | Suggestions derived from character values and starter lists | Add real World entries with stable IDs, category, name, and description. Starter suggestions are not authored World entries. |
| Deletion | Trash for characters/connections; event removal explicitly reassigns references | New deletion commands must match the reviewed UI; do not call legacy event reassignment expecting it to discard history. Preserve old APIs until consumers are migrated. |
| Drafts and recovery | `Drafts`, snapshots, migration backups, activity log | Reuse storage with event-aware draft keys and new payload versions. Atomic save must clear only the draft that was committed. |
| Graph arrangement | Saved graph views and existing graph state modules | Adapt view preferences later; keep layout separate from story content and character history. |

Evidence: `migrations.py` currently defines 13 ordered migrations; `Database.export_json` exports format version 9. Migration and export format versions are separate. Both import/export and backup/recovery must include any new durable tables before the new app becomes the default editor.

### Data rules for the new interface

- Use database event IDs everywhere. A position is only display order. Unlike the browser prototype, moving an event must not rewrite history references from one numeric position to another.
- Keep `characters` as the baseline. A proposed `character_field_history` table stores character ID, event ID, approved field key, value, and scope (`event_only` or `carry_forward`), unique per character/event/field. Unknown fields and invalid references are rejected by Python.
- Resolve an exact event override first; otherwise use the latest earlier carry-forward decision; otherwise use baseline. Empty text is an explicit cleared value. Absence of a row means no decision. An event-only edit must not become the continuing value at the next event.
- Extend relationship history with scope defaulting to carry-forward for existing entries. Do not manufacture a next-event restoration row: that would behave incorrectly after event reordering. Preserve relationship semantic validation at all affected boundaries.
- Proposed World tables: `world_entries` for stable reference identities, plus baseline and dated character assignments. Reference fields use entry IDs instead of storing their display names as identity. Renaming changes one World entry; deleting an entry checks all baseline assignments, event history, event locations, and durable drafts. Keep the reviewed single-choice behavior for the first migration; multiple languages or titles is a separate design decision.
- Existing free-text species, roles, factions, and locations remain intact during migration. Create entries from authored values, preserving original spelling. Review normalization collisions before merging them; do not silently collapse different records. New blank fields remain blank.
- Existing profile text has no dated provenance. Retain it as a migrated baseline; do not invent historical edits or claim that it was authored before the first event. Existing relationship history remains authoritative.
- New characters have no required introduction event and are available across the story. Preserve explicit introduction constraints in older stories; show them and require deliberate resolution when an operation conflicts with them.
- Keep event status separate from the selected editing moment. Selecting an event never changes Planned/Happened. Existing real events with no status should remain unclassified until the author chooses; the sample prototype's Happened display is not migration evidence.
- New UI deletion has no post-save Undo action. Recovery snapshots remain a separate maintenance feature. Preview all references, including legacy introductions and recoverable drafts, before deleting. Keep the current minimum of one chapter and event for this first slice.

### Python boundary and transaction ownership

Create an application service between the web bridge and existing storage classes. Expose explicit commands, never arbitrary SQL or unrestricted Python objects. React owns rendering and transient form interaction; Python owns validation, timeline resolution, durable drafts, commits, and previews.

Use one database worker/command queue. Create, use, and close the SQLite connection on that worker. The current connection uses SQLite's default thread ownership; disabling that check is not a substitute for serialization. Bridge callbacks enqueue work and return structured results.

Every committed command must own one transaction containing all changes, revision advancement, draft cleanup, and activity logging. Audit reused methods before composing them: `save_character`, `Drafts.save_task`, and several storage operations own their transactions. `Chapters.save_event` already demonstrates using transaction-free `Events.write` to avoid premature commits. Extract equivalent write helpers where necessary.

Each response carries an authoritative story revision. Writes include the revision read by the editor; stale requests receive a conflict response and retain their draft. Chronology/deletion previews are pure and receive a fingerprint of their inputs. Applying a preview rechecks that fingerprint inside the transaction. Include profile history, World assignments, drafts, and introduction references, not just relationships, in this check.

### First service contract (proposed names)

| Command | Inputs | Result |
| --- | --- | --- |
| `get_workspace` | Selected event ID | Revision, cast, chapters/events, selected context, capabilities |
| `get_profile` | Character ID, event ID | Resolved fields, baseline/decision source per field, World choices, revision |
| `create_character` | Name, optional summary, expected revision, request ID | New stable ID, updated revision, profile at requested context |
| `save_profile` | Character ID, event ID, changed fields with scope, expected revision, request ID | Canonical resolved profile and updated revision |
| `save_profile_draft` / `get_profile_draft` / `discard_profile_draft` | Character ID, event ID, draft version/payload as appropriate | Durable draft or acknowledgement |
| `preview_story_change` / `apply_story_change` | Proposed move/deletion; preview token on apply | Named before/after differences, removed references, revision |

Commands return `{ok, revision, data}` or `{ok: false, error: {code, message, field?}}`. Error categories include validation, stale revision, missing record, and storage failure. Frontend controls must not show a successful save until Python commits. Request IDs prevent duplicate creation if a request is retried after a lost response. This protocol is a target contract, not an API that already exists.

### Implementation sequence and completion gates

1. **Python profile-history foundation.** Use temporary databases and disposable sample copies. Add schema support, a pure resolver, service-level validation, and an atomic profile save. Test baseline, exact-event override, continuing edits, later explicit decisions, cleared values, renamed World entries, stable IDs across moves, and failed-write rollback. Do not change production UI yet.
2. **Thin React/pywebview slice.** Bundle local assets and implement cast selection, new character, profile editing, shared event selection, and review/save. Use the Python service exclusively. Initial acceptance is create → edit at an event → save → close host → reopen the same copied database → verify fields and history. No graph-library or packaging redesign is bundled into this first slice.
3. **Durable drafts and conflict behavior.** Exercise close/reopen with pending edits, save/discard/stay navigation, duplicate requests, invalid IDs, storage failure, and stale revisions. Verify connection lifecycle through the actual bridge, not just mocked frontend responses.
4. **World and remaining Story/Relationships operations.** Connect reference management, temporal connection edits, participation, and reviewed moves/deletion. Reuse the approved UI while moving all story rules out of JavaScript. Extend imports, exports, backups, recovery, and migration round-trip tests.
5. **Distribution gate.** Build and test on Windows without development tools, including offline launch and renderer prerequisite handling described above. Keep the Tkinter app available until data compatibility and recovery tests pass; do not retire it because the new screen merely looks complete.

Browser localStorage is not a production database migration source. If prototype edits are to be kept, add a separate explicit export/import preview; fixture IDs must be mapped and never assumed to match an existing user's database. Production rollout does not automatically copy browser state.

The immediate coding milestone is step 1 above. The first visible database-backed screen follows in step 2. No existing story database or schema was changed while writing this plan.

### First persistence slice implemented

`story_atlas/profile_history.py` now provides an opt-in experimental `ProfileHistory` service with a pure field resolver, `get_profile`, and atomic `save_profile`. It supports baseline values, event-only and continuing decisions, explicit blank values, stable event IDs, source metadata, and stale-editor rejection. Field writes, activity logging, and cleanup of the matching context draft commit together. Its revision fingerprint covers characters, events, and profile decisions; it is not yet the application-wide revision protocol.

`tests/test_profile_history.py` exercises temporary SQLite files, close/reopen persistence, scope resolution, reordered events, invalid batches, competing writers, and injected logging failure with rollback. Existing creation is used for setup; a revision-aware creation command and request receipts remain pending.

The experimental tables are created only when this service is explicitly constructed. They are not registered in production migrations or enabled by the Tkinter app. Use disposable copies only: export/import, legacy Undo, introduction constraints, World reference IDs/renaming, and event deletion integration are not yet supported by this service. Reference fields are temporarily text. This is the first subset of step 1, not completion of its full integration gate. The browser prototype still saves to localStorage.
