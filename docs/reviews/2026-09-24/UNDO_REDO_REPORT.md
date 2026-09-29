# Undo and redo — Story Atlas 0.15.0

Ctrl+Z and Ctrl+Y dispatch before Tk's default bindings. Editable text fields use
local editing history; single-line entries and comboboxes have bounded local
history too. Read-only detail panels and the rest of the workspace dispatch to
saved-story undo/redo. Story also exposes explicit saved-change commands.

Committed transactions retain before/after snapshots of characters, connections,
relationship history, events, participants, chapters, and story metadata. Undo and
redo restore these atomically with foreign-key and story-chronology validation.
Deletion/restoration and relationship batches remain complete undo steps with
stable IDs. Node dragging, keyboard movement, pinning, and layout resets share
the same ordered session history. New changes clear the redo branch.

History retains at most 30 actions, reducing depth for large snapshots. It starts
fresh on opening/switching a story or restarting. External database writes reset
history instead of being overwritten. Unsaved forms and modal dialogs block
saved-story undo; local text undo remains available. Loading another character
resets editor history so text cannot be undone into a different profile.

Drafts, activity entries, immutable portrait assets, and saved-view preferences
are not rewound. Navigation, zoom and pan are not saved-story edits. Saved-story
undo refreshes the graph using normal placement; graph move undo restores its
recorded positions and pin state.

## Verification

- Final build: **212 tests passed in 118.441 seconds** (`build-verification/undo-build.log`).
- Ten focused undo tests cover keyboard dispatch, typed-text isolation, deletion
  and relationship history, atomic batches, redo branching, chapter references,
  SQL failure rollback, external changes, modal/unsaved protection, story-switch
  isolation, graph positions/layout choice, and profile text-history reset.
  Latest focused run: `build-verification/undo-focused.log`.
- Source smoke and final packaged smoke passed. Packaged smoke undoes and redoes
  a character restoration with all attached connections in the Prometheus model.
  Evidence: `build-verification/undo-source-smoke.json`,
  `build-verification/undo-packaged-smoke.log`, `build-verification/packaged-smoke.json`.
- Source and packaged fingerprint match:
  `8069cc818065c9160f07b8f720dcb0eae0b9ffa68ca5f7651c6121405f318725`.

The final directory is `dist/releases/0.15.0/StoryAtlas`; the workspace launcher
selects it, and `dist/StoryAtlas-Windows-x64.zip` was rebuilt from it. Schema 12
and portable format 8 are unchanged.
