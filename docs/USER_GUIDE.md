# Using Story Atlas

Story Atlas runs locally and stores each story in a `.atlas-preview` SQLite
file. Start with **Create story**, **Try Greyhaven sample**, or **Open story**.
Use the installed Windows shortcut for the bundled release; source setup is
covered in the [README](../README.md).

## Start with a sample

**Try Greyhaven sample** creates a new editable story in your data folder.
The [Frankenstein, Dracula, and Edgerunners examples](../examples/saved-stories/README.md)
are ordinary saved stories. The Windows installer copies them to the default
Stories folder if files with those names are not already present. Source users
can find them under `examples/saved-stories`.

**Open story edits the selected file directly.** To preserve an example, copy it
first or choose **Restore backup as a copy** and select it. The copy becomes a
separate working file. The examples contain spoilers; their README explains
editorial choices and image credits.

## Plan a story

On **Story**, add chapters and events, select an event, and edit its title,
status, purpose, summary, location, participants, and notes. Choose **Save
event** to commit the edits. Selecting an event does not change its status.
The main page scrolls; smaller windows place the outline above the editor.

## Build the world and cast

On **World**, add shared reference entries such as locations, factions, and
species. On **Characters**, create a character and edit their profile at the
selected story event. Relevant profile fields can refer to World entries.

Review profile changes before saving:

- **Carry forward** applies from the selected event until a later decision
  replaces it.
- **Event only** applies at that event; afterward the continuing value resumes.
- Saving an empty optional field explicitly clears it for the chosen scope.

Add characters to an event from its participant search. Open a participant's
profile and use the return action to go back to the event. Portraits are saved
inside the story and apply to the character across all events.

## Track relationships

On **Relationships**, explore the graph for the selected event. Character
profiles also provide connection editing. Review the scope before saving a
change. Directional connections can have an inverse label; mutual connections
represent one shared relationship. Use the graph controls to explore and reset
the view.

## Save, close, and recover

Field edits are kept as pending drafts, but use the save controls to commit
them to story facts. Check for **Draft kept on disk**; a draft-write error means
pending edits may not yet be safely stored. Resolve the error or retry before
closing. Retained drafts are recovered on reopening for you to review.

Closing with pending work offers choices to save, retain a draft, or stay.
Success notices dismiss after three seconds. Error messages remain visible
until cleared or dismissed. If a save reports that the story changed, reload
saved values and review the preserved draft before retrying.

## Back up and move a story

1. Choose **Story file → Back up story**. The app creates a snapshot in the
   `backups` folder under your data root.
2. Keep another copy somewhere separate from the computer if the story matters
   to you. A local backup alone does not protect against losing the computer.
3. To recover or experiment, choose **Restore backup as a copy**. It creates a
   new story instead of replacing the current file.

Use the app's backup command rather than copying an actively open database.
Close the app before moving working files. Avoid opening the same story in
multiple app instances. Copying an installer does not transfer personal stories.

Default data roots:

| Platform | Settings, stories, and backups |
| --- | --- |
| Windows | `%LOCALAPPDATA%\StoryAtlasPreview` |
| macOS | `~/Library/Application Support/StoryAtlasPreview` |

`--home` selects a different data root. `--story` opens an explicit supported
file in place, even outside that root. Source and installed Windows copies
share the default root. Uninstalling the Windows app preserves its stories,
backups, and installed examples. Old `.db` story formats are not imported by
this version; renaming their extension does not convert them.

## Updates and platform limits

See [Windows installation](../installer/README.txt) or
[Mac source setup](../installer/README-MAC.md). Installed Windows copies need a
new installer to receive source changes. Source users rebuild the frontend
after UI changes; the Mac launcher handles this automatically.

The current source can differ from the bundled Windows release. Consult
[release history](RELEASE_HISTORY.md) before assuming a source fix is in an
installed copy. Native Mac validation and clean-machine/offline WebView2
installation remain outstanding.
