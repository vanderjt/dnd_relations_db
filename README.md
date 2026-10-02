# Story Atlas

A local storytelling notebook built with Python, Anaconda, Tkinter, SQLite,
NetworkX, and Matplotlib. No account or server required.

The accepted future UI direction is React and TypeScript hosted in pywebview,
with Python controlling application logic and authoritative state. See the
[web UI architecture decision](docs/WEB_UI_ARCHITECTURE_DECISION.md) for the
alternatives, rationale, offline distribution requirements, and proposed first
milestone. This is a direction decision; the current application remains Tkinter.

A separate native web preview is now available through **Launch Story Atlas Preview.cmd**.
See [the preview delivery guide](docs/MVP_DELIVERY.md) for working features, local storage,
recovery, verification, and remaining distribution limitations. The original launcher
still opens Tkinter; preview stories use a separate format.

## Start with Anaconda

Open Anaconda Prompt in this project folder:

```console
conda env create -f environment.yml
conda activate story-atlas
python main.py
```

If your existing Anaconda environment already has Tkinter, Matplotlib, and
NetworkX, you can run `python main.py` directly. The tested local runtime is
Anaconda Python 3.13.9. Create the dedicated environment above to isolate dependencies.

You can also double-click **Launch Story Atlas.cmd**. It opens the packaged
build when present, otherwise your `story-atlas` Conda environment. For a build
that needs no Anaconda, see [Windows distribution](DISTRIBUTION.md).

On first launch choose **Start empty**, **Open story**, or **Try sample story**.
Each sample is a fresh Greyhaven database containing **18 characters, 50 stored
connections, and ten events across three chapters**. The original five characters now share a cast
of dockworkers, witnesses, healers, smugglers, and council officials. Explore
family, employment, mentorship, debts, patronage, blackmail, and other connections.
Some links begin at events, change, end, or resume; 49 connections remain active
at Current. From an open story choose **Story → Try expanded Greyhaven sample…**
to create a separate sample after the normal unsaved-edit checks.
Sample creation never inserts into or overwrites an existing story.

Later launches reopen the last available story. Use `python main.py --welcome`
to return to startup choices. Canceling a file picker creates nothing; a missing
last story returns to the welcome screen. **Help · F1** explains saving,
relationship direction, graph navigation, and recovery. Contextual tips can be
dismissed individually and restored from Help.

Default user data lives in `%LOCALAPPDATA%\StoryAtlas`, outside the application:
`settings.json`, `stories`, and the Matplotlib cache. Existing source-checkout
stories at `data/story_atlas.db` remain untouched; use **Open story** to continue
them. Existing per-folder preferences are not automatically moved.
Use `--data-dir "D:\Story Atlas data"` or `STORY_ATLAS_HOME` to choose a different
data root. Packaged builds refuse story/data paths inside their own program folder.

To open or create a specific story directly:

```console
python main.py --database data/my_campaign.db
```

## Simple and Advanced modes

The labeled **Mode** selector changes presentation of the same story database.
First-run Welcome uses **Simple**; existing preferences remain **Advanced** until
you choose otherwise. Both modes share records, assets, history, settings and recovery.

**Start a story:** enter its title and choose **Create story**. The filename is
derived safely from the title in your user-data `stories` folder. The displayed
title keeps its spelling; invalid Windows filename characters are replaced and
reserved names are prefixed. Existing filenames receive an available numbered
suffix. Exclusive publication never overwrites an existing story. **Change
location…** is optional. **Customize opening** starts collapsed with **Chapter 1**
and **Opening scene** already supplied.

**New character** adds an unsaved dashed node and opens Name, Character
type and Save. Optional details, Story, Goals, Abilities, Inventory and
Notes start collapsed, retain input and indicate filled content. Save and Close
remain below the scrolling form. Occupation, ancestry, status and tags offer
starter suggestions plus exact custom values from the story; nothing is inserted
just by opening a list. Type directly in selectors, or use their arrow / Down key.
Tags add to the current selection and can be removed individually. Typed pending
tags are included when saving or recovering a profile.

**Character type** offers exactly Player, Merchant, Allied NPC, Neutral NPC,
and Enemy NPC. It replaces the
classification, narrative-role and writing-template selectors in both modes.
**Add writing prompts for this type** optionally fills empty prose fields using
the chosen type; selecting a type itself never inserts text. The graph uses the
same type for its badge and color. **Legend · dots & links** explains current character dot colors and relationship
link colors, styles and direction. Dot entries filter the graph. The plotted key
includes both sets of swatches and sits above the graph so it does not cover nodes.

Upgrading maps Player Ally/Enemy and standalone Protagonist to Player, NPC Ally
to Allied NPC, NPC Enemy and standalone Antagonist to Enemy NPC, and Neutral/Minor
NPC to Neutral NPC. Combined labels use their classification component. Exact
original labels remain archived in the database and exports for recovery; only
the five current options appear in the selector. Occupation and relationship types
remain separate. Character type describes Current when viewing historical graphs.

New characters are placed in free graph space instead of stacking at the center.
Existing positions, pins and zoom scale are retained. Simple mode pans only when
necessary to reveal a new node outside a crowded viewport; saving retains the
provisional node's position. Hidden cast positions also reserve space.

Click a saved character to read its summary, goals and individual connections,
including ended connections. **Edit character** opens the complete profile.
**Connect…** makes that character Source; click other nodes to add/remove targets.
Selected labels provide Remove and Make source. **Exit selection** leaves graph
selection mode without discarding the form. Shift-click remains an ordered-selection
shortcut. Keyboard selectors provide the same actions. **Add relationship** also
opens with no selection and guides you through Source and targets. Empty lists and
unsuccessful searches explain the result; Create character / Create event preserve
the parent task. A committed nested character or event remains saved if the parent
task is later discarded.

Friends, Parent / Child, Employer / Employee and Mentor / Student presets fill
visible, editable meaning and inverse-label fields. Notes are optional. Review
shows every proposed pair, both perspectives, notes and the effective event.
Alden, Bryn, Cora proposes only Alden → Bryn and Alden → Cora. Shared validation
saves the whole batch or nothing. Conflicting targets can be explicitly excluded.
Success clears every entry field, notes, targets and graph selection, focuses
Source and leaves the pane open. **Use graph selection** and **Use selected event**
are explicit reuse actions; unrelated refreshes never refill cleared fields.

**Change at this event** records development. **Correct entry** edits the exact
effective entry, including the latest ended state at Current. Endings keep history;
Trash is separate. The shared review and chronology safeguards remain in both modes.

**Next event** navigates to the next event, or opens an editable suggested scene
in the current chapter. New chapters and their first event commit together. Events
never become permanently locked. Introduction timing appears as **Introduced in
Opening scene · Change introduction…**; the explanation appears when changing it.
Characters appear from their introduction onward. **More → Show planned cast** reveals
future characters with dashed outlines and PLANNED labels, without future links.
Chronology conflicts require an explicit later event or introduction reassignment.

Close, navigation and mode switches offer **Save / Discard / Stay** for unfinished
Simple tasks. Unchanged inspection needs no prompt. Character, Simple event,
relationship batch and relationship-state drafts are stored separately from saved
records in the story database. **Maintenance → Recovery, Trash, and drafts** lets
you review them after restart. New event/batch tasks also resume their existing
draft. Recovery retains stable IDs and revalidates references; missing targets or
participants require explicit exclusion or restoration. Missing exact correction
contexts require restoration rather than guessing a replacement. Recovery never
commits automatically. Successful commits clear their draft transactionally.

**More → Undo recent character creation** moves the recent character to Trash only
while no later committed action exists. Later edits disable this narrow Undo;
Trash restoration remains available. There is no general history undo engine.

Drag empty background to pan, wheel to zoom and nodes to pin them. Arrow keys move
the selected node with graph keyboard focus. The bottom timeline navigates without
changing chronology. Positions and zoom survive navigation and mode changes.
More exposes graph filters, exports, saved views, event editing and explicit
reference reassignment. NetworkX and Matplotlib remain the graph implementation.

This release is **0.18.0**, database schema **13**, portable story format **9**.
Older formats 1–7 remain readable. Migration backs up existing databases before
making transactional changes. See the [Simple rework completion report](docs/reviews/2026-09-24/SIMPLE_REWORK_COMPLETION_REPORT.md)
for the prior rework. The [combined legend and worked examples report](docs/reviews/2026-09-24/EXAMPLES_REPORT.md) records this release.

## Advanced workflow

The main tabs follow **Characters → Events → Relationships → Graph**. Contextual
Next actions link the steps, but none is mandatory: undated relationships remain
supported. **Maintenance → Activity log** opens technical activity separately.

1. Use the **Story** menu for New, Open, Recent, and Export actions. **Search · Ctrl+K**
   and **Help · F1** remain directly available. **Maintenance** contains Recovery,
   Trash, drafts, and appearance settings; the separate **Activity log** is the
   technical audit trail, while **Events** is the fictional chronology.
2. On **Characters**, choose **New character**, enter a name and profile, and save.
   Only the name is required. Profiles include role, ancestry, location, faction,
   status, summary, portrait, backstory, traits, skills, inventory, and notes.
   Ctrl+S saves the current profile.
   Search matches saved profile fields, chapter and event text, and current or
   historical relationship states. Duplicate names are identified by ID.
3. Create chapters/sessions on **Events**, with summaries and participants.
   **Start a new relationship here** opens blank relationship entry beside the
   selected event. Its participants are suggested, and **Use this event as beginning**
   explicitly fills the optional event field. Successful saves clear the entire
   batch form; **Inspect saved relationship here** opens that exact record's history.
   **Return to event** checks unfinished input. Existing connections change through
   **Record change**, with review.
   In the event editor, search participants and use checkboxes (Tab/Space on the
   keyboard). Filtering preserves selections; focus a checkbox for current saved goals.
   **Save and close** reveals a newly created event in its destination chapter.
   **Cast goals** in Characters shows committed goals across the active cast,
   including a clear empty-goals state. Goals remain verbatim free text.
4. On **Relationships**, add a source, target, type, meaning, and context. Choose
   **Directional** or **Mutual** deliberately; optionally add an inverse label
   for a directional link. Custom types are supported. Multiple different
   types can connect the same characters. New forms start empty. Type part of a
   character's name to filter suggestions, then press Down and Enter to select
   a match (the IDs distinguish duplicate names). Click its arrow or press Down
   to open the list; press Escape to dismiss the list before typing a new search.
   Type suggestions include built-in types and custom types in saved relationships;
   you can also enter a new type. A live preview explains both characters' perspectives.
   Validation messages appear beside fields and failed saves preserve your entry.

   After adding a relationship, the dialog stays open, clears the source, target,
   type, meaning, inverse label, start event, and notes, and returns focus to Source. A confirmation identifies the
   saved connection. Ctrl+Enter saves; Tab moves through Source, Target, Type,
   Meaning, Inverse label, Begins at event, Notes, Save, and Close (Shift+Tab moves backward). **Close**, Escape outside
   a dropdown, and the window close button offer Save / Discard / Cancel if
   an entry is unfinished. Edit by double-clicking a row; saving an edit keeps
   its fields and updates the same record instead of adding another relationship.
5. On **Graph**, choosing a focus character switches to **Direct** connections
   and fits that view. Choose **Two steps** or
   **Full graph**. Direction, relationship type, isolate visibility, and layout
   are grouped in **Filters & layout**; the active filters and selected historical
   event are always summarized below the controls. Zoom, Pan, and Fit remain visible;
   graph navigation, saved views, reset layout, and export are in **View & layout**.
   Click a node or arrow to inspect it beside the graph. **Open profile** opens
   character editing. Drag a node to move and pin it; save arrangements using
   **Saved views…**. See the graph exploration guide below.
6. **Export snapshot** writes a PNG and a matching JSON snapshot of the displayed
   graph using the selected theme. This records an entry in **Activity log**.
7. **Export all data** writes saved characters, relationship starting states and
   dated history, story events/participants, and activity
   to readable JSON. Activity records creations, edits, deletions, and exports;
   it is an audit trail, not full profile version history or an undo facility.

Unsaved character changes prompt you to save or discard before switching
profiles or closing. Deleting a character moves it and its active relationships
to Trash after confirmation. Skills, traits, and inventory are flexible text fields.

### Relationship workspace

Search the cast by name in the left pane; IDs distinguish duplicate names. The
right pane shows all Current connections involving the selected character, with
the other endpoint, arrows, types/inverse labels, and notes. **All relationships**
shows the whole story. Selecting a row exposes its complete notes in a scrollable
area. Parallel types and reverse links remain distinct records.

The selected character is placed on the left: **→** points to the other character,
**←** points from the other character toward the selected character, and **↔** is
shared. Inverse labels retain their source/target roles; reversing the display
does not reverse the stored relationship. A legend explains the arrows. Profiles
and the graph inspector use the same arrow presentation; forms retain the explicit
Mutual/Directional choices and their explanations.

Use **Connection actions** for correction, History/story changes, consolidation,
or deletion. Undo and Add relationship remain available. Global search selects
an appropriate character and the exact matching connection. Cast search, character,
and relationship selection are retained across story switches in this session.
Drag the divider to resize the panes; its width is saved on normal application exit.

### Greyhaven's chapter arc

The dockside fever leads to a fragile pact and a missing archivist. The party
finds witnesses beneath the quay, reveals the ledger, and faces a blockade.
Testimony and a flood rescue lead to a hearing and reconstruction. Mira and
Seraphine are shared Allies in chapter 2; Mira regards Seraphine as an Enemy
from chapter 5. Thorne and Sable cooperate in chapter 4, break contact in chapter
6, and resume the same alliance in chapter 8. Compare these states using the
graph's event selector. Profiles always describe Current, not the selected chapter.

## Event-centered tasks (September UX update)

New events are selected in their destination chapter immediately after **Save and
close**. Searchable native participant checkboxes work with Tab and Space; the
persistent selected summary survives every search. Duplicate names include IDs and
role/faction context. Trash characters cannot become new choices; previously linked
Trash participants remain marked and preserved. Focus a checkbox for a compact
preview of **current saved goals**, without opening another window.

**Record change** opens one task dialog: search for a connection, describe its
state, then review before/after. **Event-participant connections only** narrows the
choices. If a state already exists here, use **Correct entry** to update that same
record. Ctrl+Enter follows the same edit → review → commit path as the primary
button; Escape goes back from review. Back/Close asks before abandoning edits.
Failures keep all input. A committed result highlights the change at the event and
offers **Add another change**, **Graph at event**, and **Close / Return**.
The History browser uses the same internal editor/review steps.

Event and graph scope reads **After: Chapter / Event**; Current reads **Current —
after the last event**. All character profile fields and goals are current, not
historically versioned. **Event → Graph → Profile → Back → Back** restores event
chapter, outline selection/expansion, reading scroll, graph positions, filters,
selection, and zoom. Select a participant in the event goals outline and choose
**Edit current goals**; save, then use the named **Back** action to return.
**Cast goals** searches current goals and names and opens the chosen profile.

Long event prose wraps in the main reading pane. Compact outlines expose full
copyable goals/notes in their selected detail. **Expand details** hides the chapter
and event panes; **Show chapters and events** restores them. Profiles use
**Edit profile** in read mode and **Save changes** in edit mode; **Profile actions**
contains Duplicate/Delete. Saving a profile keeps editing open; **Done** leaves it.

Relationship entry starts empty. Optional **Timing and notes** can be expanded or
collapsed without losing content. The inverse field appears for Directional or
when it already contains text. **Add relationship** saves, clears every field,
focuses Source, and stays open. **Save correction** updates the same relationship
and stays open. **Close / Return** is separate. Recovery drafts remain uncommitted.

Graph **Previous / Next** changes the selected event while retaining positions and
zoom. **Filters → Highlight changes at selected event** marks changed connections.
**Changes only at selected event** is a separate scope including ended connections,
marked **ENDED HERE**; full historical graphs omit inactive connections.
**Clear filters** keeps time and focus. PNG titles and JSON `time_scope`,
`display_scope`, and `profile_scope` identify the displayed scope and current-only
profiles. Changes-only exports mark ended records inactive. General story exports
and all history remain unchanged. Named views store presentation options without
requiring a database migration.

## Relationship meaning and conversion

**Directional** stores one connection from Source to Target. `Mira → Pip: Enemy`
means Mira is hostile toward Pip; it says nothing about Pip's feelings toward
Mira. Pip sees an incoming Enemy connection. An independent opposite-direction
record may be added if that hostility is reciprocated. Existing relationships,
including reciprocal pairs, remain directional after migration.

An optional **Inverse label** describes the target's role in that *same*
directional connection. `Mira → Pip: Mentor`, inverse `Mentee`, shows Mira as
Pip's Mentor and Pip as Mira's Mentee. Employer/Employee works the same way.
The inverse is descriptive: it does not create another record or reverse the
graph arrow. Leave it empty when no inverse is intended. Labels are entered per
connection; no automatic type pairing, renaming, or shared type-definition editor
is introduced. The preview explains the source role and receiving perspective.

**Mutual** stores one shared connection, such as Friend, visible once in the
↔ section of each profile. `Mira ↔ Pip: Friend` and `Pip ↔ Mira: Friend`
refer to the same connection. Endpoint IDs are stored in canonical order, so
Source/Target may appear swapped after saving a mutual entry. Mutual uses the
same type for both characters and does not accept an inverse label. If an inverse
was entered, the form asks you to clear it or choose Directional; it never clears
that input automatically. Editing or deleting the shared record affects both
profiles. Use Directional for relationships with distinct source/target roles.

Duplicate prevention compares exact, case-sensitive labels and the perspectives
each record represents. A mutual Friend conflicts with another mutual Friend in
either order and with a directional Friend on either side. Mentor/Mentee also
conflicts with a reversed Mentee record. Distinct types may coexist. No fuzzy
matching or assumptions about similarly spelled labels are made. The same rules
apply to entry, editing, JSON imports, SQL writes, and Trash restoration.

To correct a single record, choose **Correct entry**, deliberately change Meaning,
review the preview, and save. It keeps its ID. If a reciprocal record conflicts,
conversion is refused and both records remain unchanged. For tracked records this
corrects the latest dated state; use History to record a fictional change instead.
Consolidation is limited to undated records so it cannot silently remove a timeline.
To consolidate an undated pair:

1. Select a directional record and choose **Consolidate reciprocal…**.
2. Explicitly choose its reverse record and enter the resulting mutual type.
   Different original labels are allowed; you decide the shared label.
3. Choose **Preview**. Review both original IDs, labels, inverse labels, and notes.
   The resulting notes concatenate both originals with provenance, even when
   notes are identical; no conflict resolution discards or deduplicates text.
4. Choose **Confirm consolidation** to create one new mutual record and move
   both original directional records to Trash unchanged, all in one transaction.
   Cancel changes nothing. Changing either choice requires a new preview, and
   changes to records after preview require reviewing again.

To undo consolidation, move the new mutual connection to Trash and restore both
original records from Recovery. A conflicting active record prevents restoration;
it is never overwritten. Character deletion and restoration handle a mutual link
as one record and restore it only when both characters are active. SQLite backups
retain semantic fields and the original records in Trash. JSON exports include
active records and combined provenance notes but exclude Trash.

Graphs draw one single-headed arrow for Directional and one double-headed arrow
for Mutual. Mutual is traversable from either endpoint in incoming/outgoing focus
views and counted once in graph totals and snapshots. Inverse labels are displayed
alongside the type, searchable, and available as type filters, but do not add a
reverse traversal edge. Search results identify the stored record, so searching
either label opens the same relationship.

## Stories, organization, and search

Use **New story**, **Open story**, and **Recent stories** in the application.
Each story is a separate SQLite database. Its filename supplies the story name
in the header and window title; the status bar shows the full path on opening.
Long names are shortened in the header but remain complete in the window title.
New story requires an unused filename and never overwrites an existing story.
Open story requires an existing, versioned Story Atlas database; a missing file
is never silently recreated. Supported older stories are backed up and migrated.

Switching stories offers Save / Discard / Cancel for uncommitted character edits.
Cancel or a failed save keeps the current story open. Opening failures retain the
current connection and editor; edits remain recoverable even if Discard was
chosen before the failure. Finish or close an open relationship-entry dialog
before switching. Successful switches cancel pending draft callbacks, close the
old database connection, and start backups for the new story.

Recent stories lists up to 12 full paths and marks missing files. **Remove from
list** forgets a path without deleting its database. Use Open story to locate a
moved file. Recents and appearance use `settings.json` in the user data root;
switching stories does not change that settings file. The last available story
reopens automatically unless `--welcome` or `--database` overrides that choice.

Character **Identity** now includes **Tags (comma separated)**. For example,
`Mage, Witness, Chapter 2` adds three tags. Commas delimit tags and cannot occur
inside a tag. Surrounding separator whitespace is ignored when matching tags;
spelling and case remain distinct (`Mage` and `mage` are different tags).
Faction, location, status, and tag dropdowns suggest values from active characters
in this story and accept custom text. Choosing a tag suggestion replaces the
field; type comma-separated values to keep multiple tags. Similar values are
never automatically merged or renamed. Tags appear in the overview, are included
in drafts/duplication/Trash, and survive JSON export/import and SQLite backups.

Choose **Filters / saved filters…** above the roster. Search text uses literal,
case-insensitive substring matching. Faction, location, and status require exact,
case-sensitive values; a blank filter means any value. Multiple filters combine
with AND, and a tag filter requires every listed tag. **Apply** updates the roster;
**Clear**, then Apply, removes all constraints. The roster displays active filters
and keeps the current profile open even if that profile is outside the results.

Name a filter and choose **Save preset** to store search text and filter values
inside this story. **Load preset** fills the controls; Apply activates them.
Replacing/deleting a saved filter requires confirmation. Presets persist across
restarts and are included in SQLite backups, but not JSON data exports. They
store criteria, not snapshots of matching characters.

Press **Ctrl+K** or choose **Search story** for global search of all committed
character fields (including tags) and relationship notes, types, and endpoint
names. Results show IDs, matching field labels, and snippets around the match.
Duplicate character names remain separate results. Down moves from the query to
the result list; arrow keys select a result; Enter opens it; Escape closes search.
Character matches open the profile overview with the normal unsaved-edit prompt.
Relationship matches select and reveal the exact record on Relationships; use
Correct current state for its full notes/editor. Search uses current relationships
and excludes ended relationships, historical states, Trash, and recovery drafts.

Changing tabs preserves roster search/filter/character selection and relationship
selection. Closing and reopening global search retains its query/result selection.
Switching away and back also restores these states separately for each story
during this app session. Automatic session state is not persisted on exit: use
named filters for reusable searches. Direct profile navigation leaves roster
filters intact, so a profile opened from search may be outside the filtered roster.

## Character profiles

Selecting a saved character opens **Overview**, showing the name and ID, role,
status, faction, location, short summary, and optional portrait. Incoming,
outgoing, and mutual relationships are listed separately. Incoming links show
the inverse label when present. Click a character name to open that
profile; IDs distinguish characters sharing the same name. Navigation still asks
what to do with unsaved edits. **Add relationship** opens the existing batch-entry
dialog with empty fields; every addition clears the fields and keeps it open.
When launched from a profile, **Use &lt;name&gt; as Source** is an explicit action; it
does not prefill a new relationship. Each relationship row has a compact menu for
editing its exact record or viewing its history. Profile links and Graph → profile
navigation provide descriptive Back actions that restore the originating context.

Use **Edit profile** for changes. Identity contains the name, role, ancestry,
status, faction, location, and portrait controls. **Story** contains summary and
backstory; **Abilities** contains traits and skills; **Inventory** and **Notes**
retain the original freeform text. Existing fields are preserved during migration.
The overview shows committed data; unsaved changes and recovered drafts stay in
the editor until **Save changes**. Saving preserves the editor position;
**Done** returns to the overview, with Save/Discard/Cancel for unfinished edits.

Optional **Add writing prompts for this type** supplies prompts based on the
selected Character type. Prompts leave names and
existing content alone, do not save automatically, and are never required.

**Duplicate** creates a new committed character named `<original name> (copy)`
after confirmation. It copies every saved profile field and the portrait reference.
It does **not** copy relationships or recovery drafts. The duplicate opens for
editing. Its portrait initially shares an immutable asset; replacing/removing the
duplicate's portrait does not change the original character's portrait.

### Portrait storage and portability

**Import portrait** copies an image into `<database filename>.assets/` beside the
database. Originals are never modified. Images are normalized to PNG, corrected
for orientation, and reduced to at most 1024×1024 while keeping their aspect ratio.
Inputs are limited to 20 MB and 20 megapixels; animated formats use their first
frame. **Remove portrait** clears the profile reference when you save.

The normalized image bytes are also stored in SQLite. Automatic/manual backups
therefore contain the portraits without needing a separate folder or archive.
After restoring a backup, managed files are rebuilt from those bytes when the
portrait is displayed. A missing original or deleted cache copy does not lose a
portrait. Invalid or unavailable image data shows a placeholder without blocking
the rest of the profile.

Image imports are retained even if you later discard the profile edit, remove a
portrait, or move its character to Trash. Automatic unused-image cleanup is not
implemented, so backups can grow as portraits are added. This preserves assets
needed by drafts, duplicates, and deleted profiles. JSON exports preserve summary
and portrait references but do **not** embed image bytes; use SQLite backups for
portable profiles with portraits. A JSON-only import shows an unavailable-image
placeholder until a portrait is imported again.

## Character goals

Open a character and choose **Edit goals**, or expand **Goals** in Edit profile.
Write immediate objectives, long-term ambitions, obstacles, and progress in this
free-form field; use separate lines for multiple goals. **Save changes** commits
them. The overview displays saved goals, and roster/global search includes them.
Goals use the same recovery drafts, duplication, Trash restoration, JSON exports,
and SQLite backups as the rest of the profile. Goals are writing notes, not
individual task records with automated status or historical state.

## Chapters, story events, and relationship history

The **Chapters & events** tab is the fictional chronology. Choose **New chapter**
to give a chapter a title and summary. Select it in the chapter outline, then
choose **New event** to add a title, summary, participants, and position within
that chapter. Position 1 is first; new events default to the end of the chapter.
Use **All chapters** for the complete chronology. Empty chapters and Unassigned
are visible in the outline. Events appear in story order; the event editor uses
position within its chapter. No calendar, dates, or real-time clock are inferred. Participants
are optional and do not restrict which relationships can change at an event.
IDs distinguish duplicate character names. Character references in Trash are
marked `[Trash]` and retained in the event editor.

Double-click an event or choose **More actions → Correct selected event** to
change its details, chapter, or position. **Move earlier / Move later** exchanges
its position with its neighbor in the same chapter after confirmation. Select
a chapter and use **More actions** to edit its title/summary or move the chapter
and its events earlier/later. Relationship states stay attached to event IDs and follow the new
order. Reordering can change the current relationship; it is transactional and
refused if it would introduce duplicate perspectives at any point in the timeline.
Event and chapter deletion are not provided, so referenced history cannot be removed accidentally.

Schema version 8 adds goals and chapters with a pre-migration SQLite backup.
Existing events retain their IDs, titles, participants, order, and history under
**Unassigned events**. Assign them to chapters deliberately through the event
editor. Unassigned events follow all chapters once organizing/reordering begins.
Moving events into chapters can change chronology and current relationships;
invalid timeline overlaps roll back the entire save. Chapter/event editors retain
failed input and prompt before discarding unfinished edits, but have no crash drafts.

Every relationship has an **undated starting state**. Existing relationships are
present before the first event and remain so until a dated change. New entry has
an optional **Begins at event** selector: blank keeps this undated behavior;
choosing an event makes the relationship absent beforehand. Successful batch
entry clears this selector along with all other fields and keeps the dialog open.

On **Relationships → All relationship history**, choose a relationship (including
an ended relationship) and inspect its starting state and dated states in order.
The selector identifies the timeline using its original starting label and ID.

- **Record story change** adds a complete state at an event. Choose **Present**
  to begin, change, or restart the connection; choose **Ended** to make it absent
  from that event until a later Present state. Choose the source deliberately
  when changing a mutual connection into a one-sided one. The character pair
  stays fixed, but type, direction, inverse label, and notes can change.
- **Correct entry** fixes a mistake in the selected baseline or dated
  state. A dated correction can change the effective event too. It updates that
  state rather than creating another fictional change. Later full states remain
  unchanged. The baseline's presence can also be corrected.
- **Correct entry** on the relationship list edits the latest dated
  state, or the baseline if there are no dated states. Use this for typos and
  mistakes; use Record story change when something happened in the story.

There is one state per relationship per event. A second state at the same event
is refused; correct the existing state or create a separate event. Each full
state lasts until the next state in sequence order. Ended states retain their
labels and notes for reference but draw no edge. Corrections are intentional
revisions, not an unlimited undo history; backups preserve older database copies.
Neither event nor relationship-state editors have crash-recovery drafts. They
prompt before discarding unfinished input, and failed saves retain the form.

### Example: allies in chapter two, enemies in chapter five

1. Create chapters “Chapter 2” and “Chapter 5”. Add “The pact” to Chapter 2 and
   “Betrayal” to Chapter 5, each at position 1 with Mira and Pip as participants.
2. Add Mira/Pip, type **Ally**, meaning **Mutual**, and Begins at event **Chapter 2 / The pact**.
3. Open that relationship's History and choose Record story change. Select
   Chapter 5 / Betrayal, Present, type **Enemy**, meaning **Directional**, and choose Mira
   as Source if only Mira is hostile. Record the betrayal in Notes.
4. Graph **Before first event** shows no connection. Graph at Chapter 2 shows one
   mutual Ally connection. Graph at Chapter 5 and **Current — after the last event**
   show Mira's directional Enemy connection. The earlier pact remains in history.
5. Correct the Chapter 2 notes to fix a typo: Chapter 5 remains unchanged. Move
   Chapter 5 earlier than Chapter 2: Enemy now takes effect earlier and Ally is
   the final/current state. This follows the new sequence, not creation timestamps.

The graph's event selector evaluates state **after** changes at the selected
event. Its title and exported PNG identify the selected event; snapshot JSON
includes `as_of_event` with the event ID, sequence, title, and summary and contains
the displayed relationship states, each counted once. Named graph views remember
the event ID, including across reordering. Current means after all stored events;
there is no separate “campaign has reached this event” setting.

Profiles, relationship lists, and global relationship search always use Current,
regardless of the graph selection. Character names, traits, and portraits are
current profile data in every graph; character biographies are not versioned.
Trash is recovery storage, not a fictional event: moving a relationship or its
character to Trash hides it in every graph date while retaining its full timeline.
Restoration checks for semantic conflicts throughout the timeline and restores
the history when both characters are active. To end a connection in the story,
record Ended at an event rather than deleting it.

Fictional events live in their own tables, separate from **Activity**. Activity
records technical actions such as saving, correcting, reordering, and exporting;
it does not supply event order or become a source of fictional history.

## Graph exploration

Choose a character (IDs distinguish duplicate names) to show and fit **Direct**
connections automatically. The focus node is enlarged independently of inspector
selection and pinning. Choose **Two steps** for two. **Outgoing** follows arrows from that character;
**Incoming** follows arrows toward them; **Both** follows either direction and
shows connections among the resulting characters. Directional views show edges
progressing away from/toward the focus through those steps. **Full graph** shows
all characters and directions. The type filter applies before traversal.
Turn off **Isolates** to hide characters without a connection in the current
filtered view. A limited-depth view needs a focus character.

The inspector shows committed character summaries or complete relationship notes
in a scrollable text area. Click a node or arrow without leaving Graph. The
inspector's relationship list identifies every relationship by ID, including
parallel types and reverse links; select a row when arrows overlap. Selecting a
node narrows that list to its visible connections; click the plot background to
clear selection and list all visible relationships. **Open profile** opens the
selected character's read-only overview; **Focus here** shows their direct connections.

Each relationship has its own arrow and optional type/ID label. Types default to
neutral **Other**; names such as Mentor do not imply support or conflict.
**Filters → Visual categories** explicitly assigns optional Support, Conflict,
Personal, or Other styling. This affects presentation only and is retained in
**Saved views**, not in relationship meaning. The legend pairs color with line style.
Above 35 characters or 60 connections, labels favor selection, nearby characters,
and highlighted changes. The inspector still exposes each complete connection.

Drag a character to move and automatically pin it. **Pin / Unpin** changes whether
**Reset layout** may move it. Pinned characters have a thicker gold outline and
can still be moved manually. Select Spring or Circle to reset unpinned positions.
Ordinary edits preserve all surviving node positions, selection, and zoom; new
characters receive positions without moving existing ones. Deleted selections
are cleared safely. Hidden graphs defer data refresh until shown, and unrelated
profile/relationship notes refresh inspector details without rebuilding artists.

Choose **Zoom** and drag a rectangle, or **Pan** and drag the view. Click the active
tool again to return to selection/dragging. **Fit** frames the whole filtered view;
**Back / Forward** navigate view history. **Reset layout** recomputes unpinned
positions, fits the result, and clears navigation history.

**Saved views…** saves a named arrangement inside the current story database:
filters, positions, pins, selection, zoom, time, change highlighting, and visual categories. Choose a name and **Load** to restore
it after restarting. Saving over a name and deleting a view require confirmation.
Views are explicit snapshots, not automatically saved workspace state. Loading
ignores characters/relationships since deleted and places newly added characters.
SQLite backups include saved views. General JSON imports/exports do not restore
them. Graph snapshot JSON includes view metadata for reference alongside the
displayed records; its positions may also include characters hidden by filters.
The PNG captures the current viewport, labels, selection, and theme, and each
successful export is logged in Activity.

## Appearance and resizing

Choose **Appearance** in the header to switch between dark and light themes or
set text size from 9 to 16 points. **Apply** updates open views, custom dialogs,
text areas, tables, dropdowns, and the graph immediately. Native Windows file
pickers and message boxes retain the operating system's appearance.

Preferences are saved in `settings.json` in the user data root and shared across
stories opened by the launcher. Drag the character roster divider
to adjust its width; its width is remembered on normal app exit and constrained
when reopening in a narrower window. Invalid preferences fall back to defaults.

Character profiles use one scrolling form with clearly labeled sections. The
relationship editor also scrolls. Save/Close actions remain outside the scrolling
area, and keyboard focus reveals fields automatically. Use the scrollbar or mouse
wheel over form labels/entries; the wheel over a notes box scrolls its text.
Tables have horizontal and vertical scrollbars. Action bars wrap at narrow widths.
Destructive actions use an explicit Delete label and a separate color; focused,
disabled, selected, and invalid controls have shared styles.

### Visual-language status

The current source UI implements the shared action vocabulary: teal is reserved
for the primary save/add/record action, neutral controls are secondary, movement
uses quieter navigation controls, Delete is explicit and destructive, and active
graph tools use a labeled selected-toggle treatment. Selection, arrows, errors,
historical/unsaved context, and save confirmation also include text, labels, or
symbols, so color is not the only cue.

Relationships separates cast, connection list, and selected details; graph and
event details are scrollable selectable read-only information rather than forms.
The Events list shows order, title, a compact participant preview, and recorded
change count while its selected-event region retains complete details and
contextual actions. Compatibility styling remains on some support screens;
Activity, Recovery, onboarding, search, and project-management screens are not
yet a complete visual-language migration.

The dark and light palettes have measured normal/action/status text contrasts
of at least 5.53:1 and 5.90:1 respectively for the reviewed pairs. Borders are
intentionally subtler, and disabled controls are not treated as normal content.
These measurements, automated geometry checks, and keyboard-focused widget
tests are useful engineering evidence, not an accessibility-conformance claim.
See [VISUAL_DESIGN_PLAN.md](VISUAL_DESIGN_PLAN.md) for implemented work and
remaining validation proposals.

## Data evolution and recovery

Choose a new database at first launch or with **New story**. The default picker
location is the user data root's `stories` folder. Data survives app restarts.
Use **Recovery** in the header for backups, imports, Trash, and character drafts.

### Schema migrations

The app upgrades version 1–8 databases to version 9 on opening them. Version 4
added named graph views; version 5 added character tags and story-local saved
filters. Version 6 adds relationship meaning and inverse labels with every
existing record defaulting to Directional and an empty inverse. Existing profile
fields, relationship IDs/notes, and graph views are preserved. Version 7 adds
events, participants, relationship starting-state presence, and dated full states.
All existing relationships start present and undated; migration invents no events.
Version 8 adds profile goals, chapters, and optional event chapter membership.
Legacy goals start empty and legacy events remain unassigned in their original order.
Version 9 adds stable introduction-event references, separate narrative role, and story-title metadata. Legacy introductions are undated and narrative role is neutral.
Before changing an existing database, it writes a `pre-migration-vN-…db` SQLite
snapshot. All pending migrations run in one transaction: an error rolls back
schema, records, and version together. A failed backup prevents migration.
Existing IDs, profile fields, relationships, and activity records are retained.
Newer unsupported versions and unrecognized databases are rejected with a clear
startup error. Do not open upgraded databases with an older Story Atlas version.

### Backups and restoration

Automatic snapshots run on startup and every 15 minutes while the app is open.
**Recovery → Backups & import → Back up now** creates an additional manual copy.
Snapshots use SQLite's backup API, so the database may remain open. Files are
timestamped in UTC under `backups/<database filename>/` beside the database.
They include committed data, activity, recovery drafts, Trash, portrait bytes,
saved graph views, saved character filters, events, participants, and complete
relationship history (including timelines in Trash).

The default retention is seven automatic snapshots. Change **Automatic backups
to keep** (1–100) and click **Save retention**; the next automatic snapshot prunes
older automatic copies for this database. Manual and pre-migration copies are
never automatically pruned. Backup failures appear in the status area.

Select a backup and click **Restore selected**, or use **Browse backup**. Choose
a NEW `.db` filename. Restore validates the snapshot and upgrades the copy if
necessary; it never overwrites the current database or modifies the source
backup. After success, you can open the restored story immediately. Declining
leaves the new database on disk for later use with `--database`.

If the active database is too damaged to start the app, close Story Atlas, copy
a known-good backup to a new filename, then start with
`python main.py --database path/to/recovered.db`. Keep the damaged original for
investigation. Backups live on the same disk by default: copy important backups
to another disk separately for protection against disk failure. Snapshots are
not encrypted. The app remains intended for one local user/process.

### JSON import and export

**Recovery → Import JSON** accepts `format_version: 1`, `2`, `3`, `4`, and `5`
Story Atlas exports. Complete story exports use version 5 for introductions, narrative roles, and story title;
graph snapshots remain version 3 with their displayed state and event/chapter
metadata. Legacy records without semantic
fields import as directional with no inverse label, even if reciprocal records
exist. Version-2 records carry `semantics` (`directional` or `mutual`) and
`inverse_label`. Version 3 additionally exports `baseline_active`, `story_events`,
`event_participants`, and `relationship_history`; missing timeline fields default
to an undated, present relationship. Imports validate event order, participant and
relationship references, fixed character pairs, and duplicate perspectives at
every event boundary before creating a new database. Mutual endpoints are
canonicalized, and conflicting perspectives
are rejected before any new database is created. A validated preview lists
character, relationship, and activity counts before you choose a destination.
Imports require a NEW database filename. Existing files are refused even if the
file picker offers to replace them. Character IDs and text are preserved; missing
optional profile fields become empty text. Activity is optional for graph snapshots.

Validation rejects unsupported formats, malformed text fields, invalid/duplicate
IDs, missing character references, self-links, and duplicate relationship types
for the same directed pair. Data is built transactionally in a temporary database
and published only after success. Failed imports leave the active story unchanged.
There is no merge-into-current-story option.

Full JSON exports contain active characters, non-Trash relationship baselines
(including ended connections), all their dated states, events, and activity.
Participation references to characters in Trash are omitted from JSON; SQLite
backups retain them. Restore the character before exporting if those references
must be portable in JSON.
They do **not** include Trash, recovery drafts, portrait bytes, saved graph views,
saved character filters, or appearance settings; use a SQLite
backup for full recovery. A graph snapshot only contains its displayed subset
and event metadata, not the complete event/history tables. Importing a graph
snapshot creates a static, undated story at that exported state; use Export all
data or a SQLite backup to preserve the editable chronology.
The export's own activity entry is recorded after writing the file and therefore
is not inside that same export.

### Character drafts

After typing pauses for one second, the editor saves a recovery draft separately
from committed characters. The draft status explicitly says whether changes are
uncommitted. Graphs and regular exports continue to use committed profiles.
Keystrokes and draft updates do not create activity entries.

On restart, the status bar reports available drafts. Open **Recovery → Drafts**,
select a draft, and choose **Recover selected**. Recovery loads the editor only:
review the information and click **Save changes** to commit it. A successful
save removes its draft in the same transaction. **Discard selected** removes the
draft without changing the committed profile. Choosing Discard in the ordinary
unsaved-profile prompt also removes that editor's draft and cancels pending saves.

There is one latest draft per existing character and one for a new character;
drafts are not version history. Subsequent edits to that character replace its
draft. A crash before the one-second pause can lose the most recent typing.
Relationship-dialog drafts are not included. Moving a character to Trash discards
its uncommitted draft; its committed profile is retained.

### Trash

**Recovery → Trash → Restore selected** restores a character or relationship with
its original ID and details. Restoring a character also restores its automatically
trashed connections when both endpoints are active. If the other character is
still in Trash, the connection waits there and returns when that character is
restored. Relationships explicitly deleted on their own stay in Trash until
restored explicitly.

If an equivalent active relationship was created since deletion, restoration
refuses to overwrite or merge it. Move the conflicting relationship to Trash and
retry. Restorations are transactional. Trash does not expire automatically, and
permanent deletion is not provided in this release.

## Project layout

```text
main.py                       Command-line entry point
environment.yml               Anaconda environment
Launch Story Atlas.cmd         Packaged Windows launcher
Launch Story Atlas Source.cmd  Development launcher; never runs an older EXE
build_windows.ps1             Pinned standalone Windows build
StoryAtlas.spec                PyInstaller resources and runtime configuration
requirements-build.lock.txt   Complete pinned packaging dependencies
DISTRIBUTION.md                Build/run instructions and release limitations
story_atlas/
    paths.py                  Upgrade-safe data and bundled-resource locations
    onboarding.py             First-run story choices
    sample_story.py           Isolated sample publishing and dated changes
    greyhaven.py              Expanded cast, connection seeds, and chapter outline
    guidance.py               Dismissible tips and accessible help
    diagnostics.py            Disposable packaged-runtime checks
    version.py                Application version and source fingerprint
    event_editor.py           Modal event editing and participant inspection
    event_change_dialog.py    Contextual relationship-change chooser
    goals_view.py             Read-only cast and participant goals
    resources/                Original icon in ICO and PNG formats
    app.py                    Window composition and shared actions
    projects.py               Story file actions, safe switching, recent paths
    retrieval.py              Global queries, exact filters, saved-filter storage
    global_search.py          Keyboard search palette and result navigation
    filter_dialog.py          Combined roster filters and named presets
    models.py                 Shared profile fields
    database.py               SQL storage, validation, logging, JSON export
    migrations.py             Version checks and transactional schema upgrades
    backup.py                 SQLite snapshots, retention, safe copy restoration
    imports.py                JSON validation and new-database import
    trash.py                  Soft deletion and connection-safe restoration
    drafts.py                 Uncommitted draft persistence
    draft_controller.py       Debounced editor draft saves
    recovery.py               Backup, import, Trash, and draft interfaces
    characters.py             Character selection and save coordination
    character_roster.py       Searchable character list
    profile_overview.py       Saved profile and relationship navigation
    profile_editor.py         Grouped fields, templates, portrait controls
    profile_templates.py      Optional writing prompts
    assets.py                 Managed portraits and backup-safe image bytes
    relationships.py          Cast-centered relationship workspace and actions
    relationship_roster.py    Searchable cast pane with All relationships
    relationship_display.py   Shared read-only arrow and role labels
    relationship_dialog.py    Batch entry, validation, preview, safe closing
    relationship_semantics.py Shared meanings, canonical identity, perspectives
    relationship_store.py     Transactional relationship writes and consolidation
    events.py                 Fictional event storage, participants, sequence order
    event_view.py             Chronological event table and modal editor
    history_model.py          Pure as-of resolution and timeline duplicate checks
    history.py                Dated state writes and deliberate corrections
    history_dialog.py         Timeline browser and state editor
    history_imports.py        Portable event/history validation
    consolidation_dialog.py   Reciprocal preview and explicit confirmation
    searchable_combo.py       Searchable character/type suggestions
    graph.py                  GUI-independent graph construction/rendering
    graph_view.py             Graph interaction and selective refresh
    graph_state.py            Focus queries, stable layouts, saved-view validation/storage
    graph_render.py           Individual arrows, legend, selection, movable artists
    graph_inspector.py        Character/relationship details and link selection
    graph_actions.py          Saved-view dialog and logged snapshot exports
    graph_controls.py         Labeled navigation controls and view history
    activity.py               Activity history
    theme.py                  Colors and ttk styling
    settings.py               Persistent appearance and pane preferences
    appearance.py             Appearance settings dialog
    scroll_frame.py           Scrollable forms with focus reveal
    widgets.py                Reusable text and table widgets
tests/                        Storage, graph, and relationship dialog tests
```

## Verification

The latest [event-layout review](docs/reviews/2026-09-24/EVENT_LAYOUT_REVIEW.md)
preserves the three-pane chapter/event/overview design. Collapsed goals and
relationship groups retain their state through refreshes of the same event;
relationship notes are available beneath each change. Narrow detail panes use
the compact action menu. Nested History returns focus to the event change chooser.

The follow-up senior-review fixes add a bounded, scrollable chapter-move preview
with persistent Confirm/Cancel controls. Chapter/event selection is remembered
per story during the session. **Inspect saved relationship here** selects the
state effective at the originating event, including baseline, earlier changes,
and ended states. Discarding profile edits while opening chapter/event/history
search results now resets the editor so those edits cannot be saved later.
Regression coverage includes a 300-event preview in both themes, historical
inspection before/at/after a beginning, discarded new/existing profile buffers,
and switching stories with overlapping numeric IDs.

The [visual-language review](VISUAL_REVIEW.md) documents follow-up fixes and
validation limits. Read-only details support Tab/Shift+Tab, Ctrl+A, and copying;
unchanged refreshes preserve selection and scrolling. **All relationship history**
opens ended connections even when the current relationship list is empty.
The inspector reports the actual graph scope. Event overviews omit visible ID
suffixes; selection controls still distinguish duplicate names. Event detail
height adapts to compact windows.

The UX regression suite exercises story-scoped Undo, Done with Save/Discard/Cancel,
single-prompt Back navigation, section-edit buttons and collapse ordering, and
event-change review through keyboard and close-save paths. It also verifies the
completion button opens the correct historical graph and releases the dialog.
The expanded-workspace checks also cover sample chronology/isolation, tab order,
event-to-entry navigation, Focus and saved views, incoming/outgoing/shared arrows,
duplicate names, global search, editing/Undo, and pane persistence. Laptop geometry
checks cover 900×600 and 1280×720, including simulated 150% Tk scaling in both themes.
These automated geometry checks are separate from native visual inspection of
the dark 1280×720 and light 900×600 workspaces on this development machine.
Actual Windows per-monitor DPI testing and observed writer tasks remain pending.

The competitive UX pass adds task-level coverage for event reveal, searchable
checkbox retention, correction versus recording, complete contextual Back,
current goals, export scopes, and 100-character / 300-link interaction. See
[the completion report](docs/reviews/2026-09-24/UX_IMPLEMENTATION_REPORT.md)
for the current test counts, benchmark, package identity, and validation limits.

Goals/chapter tests cover version-7 migration with a pre-migration backup, goals
search/duplication/Trash recovery, recovery drafts in backups, JSON round trips,
invalid chapter references and ordering, chapter/event moves, transaction rollback,
stable relationship-history event IDs, and the chapter/profile editing workflow.
The current source/package run is recorded in `build-verification/ux-build.log`.

```console
python -m unittest discover -s tests -v
```

Tests use disposable databases and cover persistence, Unicode, literal search,
validation, rollback, cascading deletion, graph filters, multiple edges,
isolated characters, image rendering, JSON export, and activity history.
First-run tests also cover all three startup choices, canceled pickers, missing
recent stories, reopening saved data, sample isolation, help dismissal, and
upgrade-safe storage. See DISTRIBUTION.md for packaged smoke results and
checks still requiring a clean Windows machine.
Relationship dialog tests additionally cover ten consecutive additions, input
retention after errors, custom suggestions, duplicate names, editing, safe close,
and native keyboard selection/navigation. These tests use real Tk widgets and
require a graphical desktop; they skip if Tk cannot open a display.

Recovery tests cover original-schema upgrades, pre-migration backup failures,
transactional migration rollback, unsupported newer versions, retention, backup
restoration, malformed JSON, mid-import failures, export/import round trips,
Trash endpoint dependencies and duplicate conflicts, atomic draft clearing,
and interrupted editor draft recovery. UI tests exercise import previews and
opening restored copies while preserving the original story.
Profile tests cover all-field preservation from schema version 2, name-only
creation, template preservation, duplicate names, directional navigation,
duplication without relationships, missing portraits, and restoration of image
bytes after both the original image and managed copy have been removed.

Organization tests cover version-4 upgrades, tags and preset backup restoration,
tag JSON round trips, exact combined filters, distinct similar values, duplicate
names, relationship-note-only matches, keyboard result navigation, retained tab
state, story isolation, closed old connections, missing recent files/removal,
canceled/failed switches, and recovery after an opening failure. All test stories
are disposable; these checks do not modify an existing story database.

Semantic tests cover canonical mutual friendships, unilateral hostility, inverse
labels and reversed duplicates, legacy reciprocal migration, one-edge mutual graph
rendering/traversal, inverse search, version-1/2 import and export round trips,
backup/Trash restoration, consolidation provenance, stale previews, cancellation,
transaction rollback, record-preserving edits, and clearing all fields after batch
additions. These use disposable databases and real Tk widgets.

Narrative tests cover allies in chapter two/enemies in chapter five, mutual to
directional changes, beginnings/endings, historical notes/date corrections,
current-state views, event reordering and conflict rollback, version-6 migration,
full history import/export, malformed references, backup/Trash restoration,
historical graph snapshots, saved event views, participants, and batch-entry reset.

Appearance integration tests check preference persistence, live light/dark themes,
scrolling, focus reveal, navigation, and logged graph exports. Geometry checks use
1280×720 windows at simulated 100%, 125%, and 150% Tk scaling with 14-point text,
plus a 900×600 window with 16-point text and a 460×360 relationship dialog.
These are automated widget-boundary checks, not screenshot-based visual approval.
Actual Windows display scaling, multiple-monitor DPI transitions, and visual
inspection on a physical laptop were not verified.

Graph exploration tests exercise directional one/two-step filters, isolates,
parallel/reverse relationships, inspector selection, dragging/pinning, saved-view
reopening and backup restoration, filtered exports, and deferred rendering.
They verify that unrelated notes do not redraw and that relationship additions
retain positions, selection, and zoom. The relationship batch-entry regression
tests still verify save/clear/refocus/stay-open behavior.

The disposable benchmark creates **100 characters and 300 relationships**. A
local Anaconda Python 3.13.9 run measured **1.37 s** for initial display including
layout/rendering, **0.013 s** for an unrelated notes refresh with no graph redraw,
and **0.032 s** to focus direct connections. Reproduce it with
`python -m unittest discover -s tests -p test_graph_exploration.py -v`.
Timings vary with hardware and window size and are not performance guarantees.
NetworkX and Matplotlib remain in use. Dense-label overlap remains a reason to
use focused views; no renderer replacement was needed for this measured dataset.
The research roadmap's timed task with writers/GM participants has not been
performed; automated timings do not establish that usability result.

Graph rendering follows the official
[NetworkX layout documentation](https://networkx.org/documentation/stable/reference/generated/networkx.drawing.layout.spring_layout.html)
and uses the standard
[Matplotlib Tk embedding API](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_tk_sgskip.html).

### Corrective review follow-up (September 24)

Graph Current corrections load the latest entry even when it ends the relationship; only a timeline without dated entries uses the baseline. History opens at the graph's inspected time, selecting the effective entry (including the preceding entry between changes). Its context identifies both the inspected time and the exact entry a correction updates. Returning retains graph time, selection, filters, positions, and zoom.

Mouse-wheel input belongs to the nearest scrollable form or participant list. At a list boundary it stays in that list; it does not spill into the surrounding form. Text areas and Treeviews retain their native scrolling. Keyboard focus still reveals controls inside nested lists.

See `docs/reviews/2026-09-24/ASTRA_UX_CORRECTIVE_REPORT.md` for reproduction, regression, and release evidence.

New graph workspaces default to the Circle (round) layout. Explicit saved views retain their chosen layout. More menus omit operations already available in visible controls; the Simple toolbar wraps on narrow windows.

## Worked examples

Story and the welcome screen offer updated Greyhaven and **the modern prometheus**. Each creates a separate database. The latter models the 1831 Frankenstein with 17 characters, 20 events, six editorial chapters and 33 connections. Both open with a round overview, five character types, and explicit link colors. Use More → Saved graph views for guided scenes. See [the example walkthrough](examples/START%20HERE.md) for steps, source attribution, and modeling choices. A saved view named Example overview supplies the initial positions, layout, label visibility and link categories when a story opens; other saved views load only when selected.

Click a character to inspect it, then use **Delete** beside **Connect…** at the bottom of the info panel. After confirmation, the character and every attached connection (including ended connections) move to Trash and disappear from the graph. Restore the character from **Maintenance → Recovery** to recover those connections and their history.

## Undo and redo

**Ctrl+Z** undoes and **Ctrl+Y** redoes. In an editable text field, these shortcuts change that field's unsaved text. Elsewhere they undo/redo saved character, relationship, event, chapter, introduction, and Trash changes, plus graph node moves, pin changes, and layout resets. **Story → Undo saved change / Redo saved change** always targets committed history. A batch save is one undo step; undoing a deletion restores its character and connections together.

Save or discard unfinished forms before undoing a saved change. Modal dialogs keep their own text editing; close them before undoing the story. New saved changes clear the redo branch. Up to 30 changes are retained in memory (large stories may retain fewer); opening/switching stories or restarting starts fresh history. External database changes reset history rather than being overwritten. Draft recovery, audit entries, immutable portrait assets, and saved-view preferences are not rewound. Navigation, zoom and pan are not saved-story changes.

Connection forms include **Link category**: Support, Conflict, Personal or Other. This sets the legend color for that individual connection and is retained in dated history, undo/redo and exports. Older connections keep saved-view category defaults until explicitly categorized. The wheel over a closed dropdown scrolls its containing form without changing the selected value; open suggestion lists retain their native scrolling.

Simple connection creation starts with **Who are you connecting?** Choose a searchable character card or graph node to immediately open **Connect to…**. Cards show names, role, ancestry, faction, location, and ID to distinguish characters. Tab focuses a card; Enter or Space chooses it. The chosen character stays above the target list beside **Change character**, which preserves relationship details and other targets while excluding the new source. Connecting from a character summary opens target selection directly. Continue through **Relationship → Review** as before. Back preserves input. Mutual direction and the current timeline event are prefilled (Current uses the last event, or Before first event for an empty timeline). Duplicate links and invalid introduction dates are shown beside the relationship fields before Review. Graph clicks cannot silently change the pair during review.
