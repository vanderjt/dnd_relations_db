# Story Atlas: interface research and upgrade roadmap

Research date: September 23, 2026.

## Scope and recommendation

This is a qualitative competitive feature review using official product pages
and documentation, combined with inspection of Story Atlas's current source.
It is not a hands-on competitor usability study, customer survey, market-size
estimate, or proof that particular features increase adoption. Priorities below
are product judgments to validate with storytelling tasks.

Recommended direction: a focused desktop workspace for quickly recording
characters and exploring how their relationships change through a story.
Preserve local SQLite storage and the existing Python/Tkinter project. Keep
the user's requested add-relationship behavior: save the record, clear every
field, keep the dialog open, and provide an explicit Close button.

## Competitive observations

| Product | Verified capabilities relevant to our scope | Design implication for Story Atlas |
|---|---|---|
| [Campfire](https://campfirewriting.com/character-builder) | Character templates, configurable panels, portraits, relationship webs, character arcs, and a notes sidebar | Offer a readable character overview, optional detail, and connections within the profile |
| [Kanka](https://docs.kanka.io/en/latest/overview.html) | Linked categories, mentions, characters associated with locations/families/organizations, and relations between entries | Make faction/location information consistent and navigable |
| [LegendKeeper](https://www.legendkeeper.com/features/) | Full-text search, reusable templates, auto-linking, tags, offline support, and export | Reduce navigation effort and keep information portable |
| [World Anvil](https://www.worldanvil.com/learn/diplomacy-webs/diplomacy-webs) | Organization diplomacy webs with separate directional scores and tag-based webs | Make relationship direction explicit and support meaningful subsets; this example concerns organizations, not its character system |
| [Obsidian](https://obsidian.md/help/plugins/graph) | Local graphs with adjustable connection depth | Let users explore one character's nearby connections instead of always showing the entire network |

These are documented features, not comparative quality rankings. Plan restrictions
and pricing were not evaluated. Obsidian is an adjacent knowledge-management
reference rather than a dedicated character manager.

## Current implementation findings

- `characters.py`: searchable roster and editable profile, but no overview,
  portraits, tags, relationship summary, or configurable fields.
- `relationships.py`: batch additions now clear all fields and stay open.
  Selection lists are not searchable; custom relationship types are not added
  to the editor's fixed suggestion list. Success feedback does not identify
  the saved connection. New dialogs initially preselect two characters.
- `graph.py` and `graph_view.py`: spring/circle layouts, type filtering, node
  clicks, and export exist. Every filter retains every character. Node positions
  are recomputed; graph clicks switch away to the profile tab.
- `app.py`: every save refreshes all views, including rebuilding the graph.
- `database.py`: durable transactions and logging exist, but no JSON import,
  revisions, recovery UI, or incremental migration runner. Initialization sets
  the schema version to 1 unconditionally, which must change before upgrades.
- `theme.py`: consistent dark colors exist, but no user text scaling, light
  theme, or shared design rules for all interactive states.

## Ordered implementation backlog

### 1. Polish relationship entry — high priority, small scope

1. Begin new relationship forms empty. Add searchable character selectors and
   suggestions combining built-in and previously saved relationship types.
2. Show a sentence preview such as “Mira → Thorne: Mentor.” Display validation
   next to the affected field; keep all input when saving fails.
3. After a successful addition, show the saved pair/type, clear every field,
   return keyboard focus to Source, and leave the dialog open.
4. Add Ctrl+Enter to save, logical Tab navigation, and a Close action that
   handles an unfinished entry. Preserve separate edit-versus-add behavior.

Implementation: extract a small relationship dialog module from
`relationships.py`; put the searchable selector in `widgets.py` or its own file.
Acceptance: enter ten different relationships without reopening the dialog;
every successful addition resets every field, invalid entries retain their data,
and keyboard-only entry works. Custom types reappear as suggestions.

### 2. Establish visual consistency and resizing — high priority, medium scope

1. Extend `theme.py` with named spacing, typography, focus, disabled, selected,
   error, and destructive-action styles. Keep teal for primary actions.
2. Add a compact workspace header, consistent page titles, clear primary actions,
   and empty states that explain the next step.
3. Add adjustable text size, a light theme, scrollable forms, and persistent pane
   widths. Check menus, dialogs, text areas, and graph controls together.
4. Replace the exposed generic graph toolbar with clearly labeled controls
   such as Zoom, Pan, Fit, Reset layout, and Export snapshot.

Acceptance: no clipped fields or inaccessible buttons at a 1280×720 display
with Windows scaling at 100%, 125%, and 150%; a keyboard user can identify focus;
relationship meaning remains understandable without color.

### 3. Turn profiles into useful reference pages — high priority, medium scope

1. Add an Overview section with name, role, status, faction, location, optional
   portrait, and a short summary. Keep a name-only quick-create path.
2. Show incoming/outgoing relationships in the profile, with links to the other
   character and an Add relationship action.
3. Group detailed editing into Story, Abilities, Inventory, and Notes. Keep the
   existing saved text intact during conversion.
4. Add character duplication and a few optional templates: minor NPC,
   protagonist, and antagonist. Defer a general custom-form builder.

Implementation: keep roster and editor coordination in `characters.py`; extract
profile summary and relationship panels. Store portrait copies in a managed
assets folder and include them in backups.
Acceptance: a user can find a character's faction and allies from the overview
without opening the relationship list; existing profiles retain all content.

### 4. Make graph exploration the central feature — high priority, medium/large scope

1. Add a selected-character focus mode: direct connections, two connections
   away, or all characters. Add a show/hide isolated characters control.
2. Add a side inspector for the selected node or relationship so browsing
   does not immediately navigate away from the graph.
3. Add a legend and distinct edge styles for relationship categories, with
   text labels and arrows. Show long relationship notes in the inspector.
4. Preserve positions across refreshes; add drag/pin and explicit Reset layout.
   Persist saved views, including positions and filters.
5. Replace unconditional full redraws with invalidation: refresh the graph when
   visible and affected, while preserving selection, zoom, and layout.

Implementation: extend `graph.py` for graph queries, `graph_view.py` for controls,
and separate layout persistence from rendering. Keep Matplotlib initially;
evaluate a Tk Canvas renderer only if interaction/performance tests justify it.
Acceptance: with 100 characters and 300 relationships, find a named character's
direct allies in under 10 seconds during user testing. Saving unrelated notes
does not move nodes or reset zoom. Measure rendering time on the user's machine.

### 5. Add reliable recovery and draft handling — high priority, medium/large scope

1. Introduce ordered, transactional schema migrations and back up before applying
   them. Stop resetting the schema version at startup.
2. Save recoverable drafts after typing pauses; show Draft saved separately from
   committed Save. Avoid creating activity entries on every keystroke.
3. Add timestamped SQLite backups, retention settings, and a restore picker.
4. Implement validated JSON import into a new database first. Preview record
   counts, validate references, and leave the active story untouched on failure.
5. Add Trash/restore for deletions, preserving the relationships needed to
   restore a character coherently.

Implementation: add `migrations.py`, `backup.py`, and `drafts.py`; keep storage
operations transactional. Backup formats must include managed portrait assets.
Acceptance: recover an interrupted draft; restore a deleted character with its
links; export/import round trips preserve text and connections. Invalid imports
make no changes to the active database.

### 6. Introduce projects, tags, and faster retrieval — medium priority, medium scope

1. Add New story, Open story, and Recent stories in the GUI using one database
   per story initially; display the active story name prominently.
2. Add tags and filters for faction, location, and status. Suggest existing values
   while allowing custom entries; do not silently merge similar names.
3. Add a global search palette covering characters and relationship notes, with
   preview snippets and direct navigation to the matching item.
4. Add saved filters such as “Greyhaven / missing characters.” Persist search
   and selection when users move between views.

Implementation: add project/settings management and tag tables after migration
support. Delay a full faction/location entity system until there is a concrete
need for independent profiles and links.
Acceptance: open a second story without a command line; search finds a phrase
found only in relationship notes; story data remains isolated.

### 7. Model mutual and directional relationships clearly — medium priority, medium scope

1. Define relationship types with a display label and optional inverse label:
   Mentor/Mentee, Employer/Employee, or mutual Friend.
2. Add a deliberate Directional/Mutual choice and preview both perspectives.
3. Represent a mutual connection with one canonical stored relationship rather
   than two independently editable copies; adapt duplicate detection.
4. Provide a preview for consolidating existing reciprocal records. Never infer
   that two existing arrows are mutual without user confirmation.

Acceptance: editing a mutual friendship updates both profile views; a one-way
enemy connection remains one-way; legacy data is preserved through migration.

### 8. Track narrative events and relationship changes — later priority, large scope

1. Add an event log with title, summary, participating characters, and optional
   chapter/session ordering. Begin with sequence numbers rather than a custom
   calendar engine.
2. Allow relationships to begin, end, or change at an event while retaining their
   previous state.
3. Add a graph “as of event” selector and a simple chronological event view.
4. Keep story events separate from the technical activity log.

Implementation: add event and relationship-history tables plus focused views.
Acceptance: a character pair can be allies in chapter 2 and enemies in chapter 5;
both graph states can be reproduced and exported without overwriting history.

### 9. Improve first-run experience and distribution — later priority, medium scope

1. Add Start empty, Open story, and Try sample story on first launch. The sample
   Greyhaven cast must live in a separate database.
2. Add brief contextual help for direction, graph controls, saving, and recovery.
3. Provide a Windows launcher first, then test a packaged build on a clean machine
   without Anaconda. Keep Anaconda for development.
4. Store user data outside the packaged application folder so updates preserve it.

Acceptance: a new tester launches the app and creates two characters and their
relationship without terminal commands or coaching.

## Delivery sequence and validation

1. **Usability release:** items 1–2 plus lazy graph refreshing from item 4.
   Regression-test the recently requested save/clear/stay-open behavior.
2. **Foundation and exploration release:** migrations/backups from item 5,
   followed by profile summaries and graph exploration from items 3–4.
3. **Organization release:** finish recovery/import; add projects/search and
   relationship semantics from items 6–7.
4. **Narrative release:** events/history and distribution from items 8–9.

Scope labels are relative engineering estimates, not delivery promises. Data
migrations, asset storage, and graph interaction carry more uncertainty than
form styling. Preserve small modules instead of growing `app.py` or
`database.py` into catch-all files.

Use the same scripted tasks before and after changes: create five characters,
add ten connections, find someone's allies, correct a relationship, recover a
deleted character, and reopen a saved story. Test with several writers or GMs
(ideally 5–8 initially); record completion time, mistakes, confusion, and whether
help was needed. These observations validate priorities; they do not establish
market-wide demand. Add larger synthetic casts for graph performance testing.

Defer real-time collaboration, mobile synchronization, AI generation, a full map
editor, and manuscript publishing until the core character/relationship workflow
is demonstrably easy to use. Their value and cost require separate research.
