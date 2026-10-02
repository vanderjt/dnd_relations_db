# Phase 2 UI roadmap

Agreed during the October 1, 2026 design review. Build small, separately reviewable milestones. Keep the character profile focused; the dedicated Relationships and World pages have their own layouts. The current browser prototype remains a design study. Production architecture is documented in [WEB_UI_ARCHITECTURE_DECISION.md](WEB_UI_ARCHITECTURE_DECISION.md).

## Minimum frames and navigation

Four main pages: Story, Characters, Relationships, World. Supporting dialogs: New character, Add/Edit connection, and the existing shared Review changes dialog. The Relationships page may use a side panel for its connection editor. Do not put graph controls or world management on the character profile.

- Characters → New character → new profile immediately.
- Profile → click relationship tag → compact connection editor → shared Review changes.
- Profile → Add connection at the table bottom → connection picker → shared Review changes.
- Characters → Relationships → full cast graph at the selected event.
- Cast context menu → Open direct connections → Relationships filtered to that character.
- Relationships itself always provides Full cast / Direct connections controls, with a character selector for Direct connections. The cast menu is an additional shortcut, also accessible by keyboard.
- World reference entries feed profile dropdowns. World and character interfaces share records rather than separate copies.

## Milestone 1: profile connections

Implemented in the prototype for review. Click a tag to choose a type and edit notes. Delete removes the row immediately and exposes pending Undo. Add connection lists other characters without an active connection to this character at the selected event. Changes remain drafts until Review changes; canceling review retains them, and leaving the character/event offers the existing save/discard/stay choices.

One shared connection per pair for new connections, with one type and notes. Mutual types display consistently on both profiles. Directional types expose both roles in the picker (Mentor / Student, Employer / Employee, Distrusts / Distrusted by, Hostile toward / Target of hostility) and preview the direction. Enemy represents mutual hostility for new selections. Custom relationship types are deferred.

All additions, edits, and deletions receive independent carry-forward choices. An unchecked change applies only at its event; the previous continuing state returns next event, unless there is a new explicit decision. Checked changes continue until a later explicit decision. Deletion uses an absent value with these same rules. No Undo after saving; reconnect instead. Type and notes are reviewed as one connection change in this milestone.

Greyhaven migration constraint: existing snapshots contain several multiple-connection pairs and directional Enemy/Ally/Rival records. Preserve those legacy records and their identities without silently changing their meaning. Prevent new duplicate pairs. Existing snapshot transitions act as later decisions; unchanged snapshots do not interrupt a continuing edit.

Acceptance: direction from both profiles; add/change/delete; pending Undo; shared profile-and-relationship review; reload; event-only reversion; later-decision preservation; duplicate prevention; theme and small-screen layout.

## Milestone 2: character creation

Implemented in the prototype for review. New character button above the cast list. Name required; Short Summary optional. After creation, navigate directly to the new profile to complete it. A new character is available at every event, including earlier chapters; creation at chapter 7 must not prevent retroactive connections in chapter 1. Preserve dirty-navigation safeguards when starting this workflow.

## Milestone 3: dedicated Relationships page

First interactive frame implemented for review. Default to the full cast graph at the current event. Provide Full cast / Direct connections switching on the page, not only through a context menu. Support connection creation, edits, removal, and opening character profiles. Reuse milestone 1's shared connection/history rules. Keep graph tools on this page; retain the simple profile table and quick actions.

## Milestone 4: World page

First interactive frame implemented for review. Reusable named lists for Races/species, Roles, Factions, Locations; name and optional description for each entry. Values saved from profile dropdowns become reusable entries. Languages, Religions/beliefs, and Titles/ranks feed a collapsed World details section on character profiles. Each currently supports one choice per event, with free entry, shared review, and carry-forward controls. Entries can be added, renamed, and described. Renaming updates character baselines and saved assignments throughout the story while retaining event scope. Only entries unused by characters across their history can be deleted. Do not automatically add more profile fields before reviewing placement.

Reserve distinct space for World summary, Lore, Author's notes, and a world map. Map interactions are deferred. The future concept is an image with pins: hover reveals a name; Place pin lets the user click the image and name the location. No region drawing is requested. Linking pins to shared Locations remains deferred.

## Later ideas

- Goals as an optional simple list rather than a table, preserving existing prose.
- Optional personality trait tags alongside free text. Possible later Python classification into generic trait categories for mechanics; low priority, original writing preserved, inferred categories kept distinct from authored facts.
- No architecture migration, map editor, custom relationship-type designer, or post-save Undo bundled into milestone 1.

## Milestone 5: Story planning

First frame implemented: expandable chapter/event outline, chapter and event creation, chapter summaries, and event title, summary, Planned/Happened status, purpose, shared location, participants, and author notes. Events are flexible in duration. Participants do not change character existence or relationships.

The selected event is shared with Characters and Relationships. Opening a chapter preserves that event; new events become selected immediately. Participant shortcuts open profiles at the selected event. Dirty forms use save/discard/stay navigation. Story edits save directly, without character carry-forward choices.

New chapters append to the outline; new events append within their chapter. Insertion shifts saved profile and connection event indices to preserve existing event identity and seeds original relationship continuity from the preceding event. Event moves within or between chapters now have an impact preview. Saved records are remapped through event IDs, and the preview lists events whose resolved character or connection values change. Chapter reordering now uses the same impact preview, moving its events together in their existing order. Empty chapters can also be moved. Deletion remains deferred. Added chapters/events and planning details persist in browser storage; reset restores the fixture.

Story refinement: full-height themed outline on desktop, independent editor scrolling, story purpose before summary, and prominent chapter headings. Participants use searchable removable tags; clicking a tag opens the profile at the selected event. The relationship shortcut lives beside participants; the separate Work at this event section has been removed.

## Integration handoff

The October 2 repository audit and the next implementation sequence are recorded in [WEB_UI_ARCHITECTURE_DECISION.md](WEB_UI_ARCHITECTURE_DECISION.md#integration-plan-after-the-ui-checkpoint). The first implementation slice is Python-owned character field history and atomic profile persistence on disposable databases, followed by the React/pywebview create/edit/save/reopen workflow. No production migration has been run.

The initial opt-in persistence service and temporary-database acceptance tests are implemented. Dated text fields can now resolve and save atomically with conflict detection; close/reopen and failed-save rollback are covered. World references, production migration/export compatibility, and the UI bridge remain pending. See the architecture document's first persistence slice status for the exact boundary.

## Native preview checkpoint — October 2

The separate React/TypeScript preview now connects to Python/SQLite through pywebview. Native create/edit/save/reopen, dated profile and connection scopes, chapters/events, participants, graph interaction, stable World choices, durable drafts, and SQLite backups/restored copies are implemented and tested. See [MVP_DELIVERY.md](MVP_DELIVERY.md) for the exact launcher and evidence.

The browser prototype remains the approved visual reference and has not been converted into the production persistence layer. Legacy/prototype imports, chronology moves/deletion, destructive World operations, combined profile/connection batches, and clean-machine packaging remain pending. Normal preview files are stored outside the repository in a separately identified format; the Tkinter editor rejects them.
