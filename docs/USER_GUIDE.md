# Using Story Atlas

Story Atlas runs locally and stores each story in a `.atlas-preview` SQLite
file. Start with **Create story**, **Try Greyhaven sample**, or **Open story**.
The included examples are in `examples/saved-stories`.

## Plan a story

On **Story**, add chapters and events, select an event, and edit its title,
status, purpose, summary, location, participants, and notes. Choose **Save
event** to commit the edits. The main page scrolls; smaller windows place the
outline above the editor. Selecting an event does not change its status.

## Build the world and cast

On **World**, add shared reference entries such as locations, factions, and
species. On **Characters**, create a character and edit their profile at the
selected story event. World entries can be selected in relevant profile fields.

Review profile changes before saving. **Carry forward** makes a value apply
at subsequent events until another decision replaces it. **Event only** applies
at the selected event, after which the previous continuing value resumes.
Saving an empty field explicitly clears it for the chosen scope.

Add characters to an event from its participant search. Open a participant's
profile and use the return action to go back to the event.

## Track relationships

On **Relationships**, choose characters, add or edit a connection, and review
its scope before saving. Directional connections can have an inverse label;
mutual connections represent one shared relationship. The graph shows the
selected event's relationships. Use its controls to explore and reset the view.

## Save, close, and recover

Field edits are kept as pending drafts, but use the save controls to commit
them to story facts. Closing with pending work offers choices to save, retain
a draft, or stay. Retained drafts are recovered on reopening. Success notices
dismiss after three seconds. Errors remain visible until resolved or dismissed.

Use **Back up story** in the file menu. **Restore backup as a copy** creates an
independent story rather than overwriting your working file. Keep additional
backup copies when sharing or moving between computers.

Default data locations:

| Platform | Stories and backups root |
| --- | --- |
| Windows | `%LOCALAPPDATA%\StoryAtlasPreview` |
| macOS | `~/Library/Application Support/StoryAtlasPreview` |

The `--home` option selects a different data root, and `--story` opens an
explicit supported story file. Uninstalling the Windows app preserves its
stories and backups. Old `.db` story formats are not imported by this version.

## Install and update

See the root [README](../README.md), [Windows instructions](../installer/README.txt),
and [Mac instructions](../installer/README-MAC.md). Installed Windows copies
need a rebuilt installer to receive source changes. Source users must rebuild
the frontend after UI changes; the Mac launcher handles this automatically.

The app has been exercised on the Windows development machine. Native Mac
testing and clean-machine testing of offline WebView2 setup are still pending.
