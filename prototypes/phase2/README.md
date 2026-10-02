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

The first deliverable supports profile editing, timeline navigation and persistence decisions. Connections support tag/notes edits, creation, and deletion through the same event-aware review as profile edits. Event creation, portrait import, World management, and production database integration remain future milestones. The visual palette is a proposal for discussion.

Edits are stored under a versioned browser localStorage key, scoped to this origin. They are not written to a Story Atlas database. About → Reset demo edits restores the fixture after confirmation. If browser storage fails, saving shows a session-only notice. Use this for design exploration, not as the sole copy of real writing.

## Themes and layout

The header's Theme selector offers Storybook (the original direction), Gothic, Cyberpunk, Noir, and Medieval. The preference is remembered separately from demo edits. Switching themes preserves unsaved fields, the selected character, event, and scroll position.

Each `themes/*.css` file defines semantic colors, heading/body fonts, panel/control corner sizes, and shadow/backdrop colors. Component styles consume these variables instead of embedding palette colors. System fonts keep all themes offline. To add a theme, copy an existing theme CSS file and register its filename and display name in `theme.js`. Keep every token so switching themes does not leave missing values. Portrait silhouettes and circular timeline markers remain structural shapes.

The character sheet uses the available workspace width with smaller outer gutters. Lower sections use direct labels (Character details, Goals, Personality, Background, Author's notes). Connections use a semantic table sorted by character name, retaining relationship direction and character navigation with unsaved-edit protection.

`node prototypes/phase2/theme-check.cjs` checks all five themes at desktop, tablet, and phone sizes, remembered selection, draft/event preservation, alphabetical connections, and guarded character navigation. It uses the same `PLAYWRIGHT_MODULE` setup as the browser checks below.

## Validation checks

Review refinements: Short Summary includes a name-aware empty-field prompt; Discard edits is a contrasting button; Review changes is available at both ends of the sheet. Relationship badges use theme tokens for friendly (green), wary (amber), and hostile (red) ties while retaining their text labels. Relationships without clear emotional meaning remain neutral. Story Time Line uses larger, higher-contrast chapter labels. Searchable fields open on click or keyboard focus. Asset revision query strings ensure a refreshed prototype picks up these changes.

### Future design ideas (not implemented)

- World management is the next milestone in [the agreed roadmap](../../docs/PHASE2_UI_ROADMAP.md). Profile relationship editing, character creation, and the first dedicated graph frame are implemented.

- Goals: prefer an optional simple list, one goal per item, over a table unless goals later need attributes such as progress or priority. Preserve existing prose when designing the conversion.
- Personality: optional suggested trait tags alongside free text. Possible later Python interpretation into generic trait categories for automated mechanics; low priority, with original writing preserved and inferred categories treated separately from user-authored facts.

Race/species, class/role, status, location, and affiliation use searchable free-entry dropdowns. Click the arrow to browse existing values, type to narrow them, or use a new value. Arrow keys and Enter select an option; Escape dismisses the list and Tab keeps typed text. Suggestions come from the template, recorded edits, and a per-field option library saved alongside prototype edits. New values enter that library on save, remain available across characters/events and reloads, and are deduplicated ignoring case and surrounding whitespace. Discarded drafts add no options. Reset demo edits clears custom options too.

`node prototypes/phase2/suggestions-check.cjs` verifies filtering, pointer/keyboard selection, custom values, reload persistence, event-only reuse, discarded drafts, case deduplication, and phone popup bounds.

Editable fields have subtle outlines and stronger hover/focus feedback. Changed fields show a textual Unsaved badge alongside theme-aware highlighting; restoring the saved value removes both. Background and Notes share a two-column layout on wider screens and stack on smaller screens. Text areas size to their content up to 240px, then scroll internally, keeping long profiles manageable.

`node prototypes/phase2/editing-check.cjs` exercises a populated profile, long-text growth/shrinkage, edit/revert indicators, review cancellation, event-only versus continuing saves, and layouts in all five themes at three viewport sizes. It writes `editing-desktop.png` and `editing-details.png` using isolated test-browser data; the sample fixture and your browser's edits are unchanged.

`node --test prototypes/phase2/model.test.mjs` runs seven history-model tests.

With the server running and Playwright available, `node prototypes/phase2/browser-check.cjs` runs the browser checks in headless Microsoft Edge. If Playwright is installed outside the project, set `PLAYWRIGHT_MODULE` to its module directory. Screenshots are written beside the script.

Verified: cast search, before/after review, Select/Deselect all, cancel retaining drafts, mixed persistence, local reversion, later explicit decisions, dirty navigation, reload/reset, event context, and no runtime errors. Desktop (1440×1000), tablet (760×900) and mobile (390×844) were checked for horizontal overflow; desktop and save-dialog screenshots were visually inspected. This is prototype validation, not a full accessibility or cross-browser certification.

## Profile connection milestone

Click a relationship tag to edit its type and notes, or use Add connection below the table. Directional choices show a preview and the reverse label; both profiles resolve the same shared record. Delete removes the row with Undo until save. Review changes includes connections and profile fields together with independent carry-forward choices. A connection’s type and notes are saved together. Legacy Greyhaven duplicates and one-way relationships retain their meaning; new duplicate pairs are prevented. Connection records are stored with the existing prototype save, leaving original fixtures unchanged.

Run `node --test prototypes/phase2/relationships.test.mjs` and `node prototypes/phase2/connections-check.cjs` (with the same Playwright environment as above) for temporal history, direction, creation, deletion, pending Undo, reload, reconnection, and mixed-save validation.

## New character milestone

New character below the cast search collects a required name and optional Short Summary, then opens the new profile immediately at the currently selected event. New characters are available at every event, including earlier chapters. Initial name and summary are baseline data; subsequent profile changes use the existing event-aware review. Cast search clears after creation, and cast totals update. Unsaved edits are guarded before opening creation. Added characters and their profile/connection records persist together in browser storage. Reset demo edits also removes added characters. Storage failure retains the new character for the session and shows the existing session-only notice.

`node prototypes/phase2/characters-check.cjs` verifies creation/cancel/validation, dirty navigation, immediate profile, retroactive connections, reload, mobile layout, reset, and storage failure.

Character deletion is available in the top toolbar and bottom action row. Its confirmation explicitly removes the selected character, profile history, and connections across all events, discarding current drafts. Cancel preserves drafts. Deletion persists in browser storage; deleted fixture characters are excluded without modifying the original fixture. Reset demo restores the fixture. The last character can be deleted; the empty state still permits character creation. Run `node prototypes/phase2/delete-character-check.cjs` to verify these paths.

## Relationships workspace

Use the Characters / Relationships navigation in the header. Relationships defaults to the full cast at the selected event, with a binary Full cast / Direct connections switch beside the character selector. The cast sidebar is hidden on this page. Cast right-click, Shift+F10, or the ellipsis menu offers Open direct connections as an additional entry point. The graph shows direction arrows and emphasizes the selected character’s edges; node selection updates the connection inspector. Select an edge with pointer or Enter/Space to edit it. The inspector supports open profile, tag/notes edits, additions, deletion, and pending Undo using the shared review/history model. Changing pages or selected characters protects unsaved work. The initial circle/radial layout supports node dragging, background panning, cursor-centered wheel zoom, a frame-corners Zoom to fit icon, and a Home icon for Reset layout to restore the current scope’s default node positions and camera. Positions and camera are retained per graph scope during the page session, not across reloads; layout gestures never create story edits. World and map tools remain deferred.

`node prototypes/phase2/graph-check.cjs` verifies graph scopes, zoom, keyboard edge editing, dirty-page guards, event-only changes across graph/profile, cast menu shortcuts, and small-screen layouts.

The graph heading names the current event. Its inspector resolves the selected character’s summary, age, species, and role at that event and shows the existing portrait placeholder. Connections have a bounded independent scroll area without a search box, keeping the character summary and Add connection visible. `node prototypes/phase2/graph-gestures-check.cjs` verifies dragging and edge geometry, panning, wheel zoom without page scroll, click suppression after drag, session layout retention, event-aware text, Home/reset behavior, and responsive layout.
