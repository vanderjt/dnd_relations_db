# Phase 2 — Greyhaven character studio

An interactive design prototype on `phase2-ui-design`, branched from `main`. Phase 1 remains a reference for useful techniques; this browser interface is independent of the Tk application and does not alter its databases.

## Open

Run `Launch Phase 2 Prototype.cmd` from the repository root, then open http://127.0.0.1:8765. Keep the server window open. Alternatively run `.build-env/Scripts/python.exe prototypes/phase2/serve.py`.

The prototype uses native browser components, CSS and JavaScript modules. No build step or network dependencies are required. Its server binds only to loopback and serves only this directory.

## Try the agreed interaction

1. Select a character from the searchable cast and choose an existing timeline event.
2. Edit character fields. Review changes shows each before/after value.
3. Checked changes carry forward; unchecked changes are saved only at the selected event. Select all and Deselect all control the checklist.
4. Move to the next event. Event-only values return to the previous continuing value, unless the new event has its own explicit change. Continuing edits stop at later explicit continuing changes; a later event-only edit overlays only that event.
5. Cancel review to keep editing. Switching character or event with unsaved edits offers review, discard, or stay.

For example, set Mira's health to 12 and inventory to a silver lantern at event 5. Uncheck Health and save. At event 6, health is back to unspecified and the lantern remains. A previously saved inventory decision at event 7 remains intact when you later edit event 4.

Ctrl/Cmd+S opens review; `/` focuses cast search. Native dialogs support Escape and keyboard focus containment.

## Data and boundaries

`export_greyhaven.py` generates a temporary fresh sample using the existing storybook template. The checked-in fixture includes 18 characters, 3 chapters, 10 events and original event-aware relationship snapshots. Character profiles are template starting points, not reconstructed historical profiles. Ages and numerical statistics are unspecified. Portrait monograms are placeholders.

The first deliverable supports profile editing, timeline navigation and persistence decisions. Relationship cards display the original event history and navigate to the other character; relationship editing, event creation, new characters, portrait import and production database integration remain outside this prototype. The visual palette is a proposal for discussion.

Edits are stored under a versioned browser localStorage key, scoped to this origin. They are not written to a Story Atlas database. About → Reset demo edits restores the fixture after confirmation. If browser storage fails, saving shows a session-only notice. Use this for design exploration, not as the sole copy of real writing.

## Validation

`node --test prototypes/phase2/model.test.mjs` runs seven history-model tests.

With the server running and Playwright available, `node prototypes/phase2/browser-check.cjs` runs the browser checks in headless Microsoft Edge. If Playwright is installed outside the project, set `PLAYWRIGHT_MODULE` to its module directory. Screenshots are written beside the script.

Verified: cast search, before/after review, Select/Deselect all, cancel retaining drafts, mixed persistence, local reversion, later explicit decisions, dirty navigation, reload/reset, event context, and no runtime errors. Desktop (1440×1000), tablet (760×900) and mobile (390×844) were checked for horizontal overflow; desktop and save-dialog screenshots were visually inspected. This is prototype validation, not a full accessibility or cross-browser certification.
