# Five character types, menus, and round layout

Story Atlas 0.13.0 — schema 12, portable format 8. 24 September 2026.

Both editors and the graph legend now offer exactly **Player, Merchant, Allied NPC, Neutral NPC, Enemy NPC**, in that order. New characters default to Neutral NPC. Existing Player Ally/Enemy and standalone Protagonist map to Player, NPC Ally to Allied NPC, NPC Enemy and standalone Antagonist to Enemy NPC, and Neutral/Minor NPC to Neutral NPC. Combined labels use their classification component. Migration covers Trash as well as active characters, creates a backup, and retains exact original labels in the hidden `legacy_character_type` column. Exports and duplication preserve this archive. Older exports and recovery drafts remain readable.

Simple More no longer duplicates New event, Next event, Character selection controls, or the character-type legend. Their controls remain visible through toolbar wrapping on narrow windows. Fit, zoom/pan tools, export, and saved views remain in More because Simple mode hides the separate graph toolbar. Advanced Events More actions omits New chapter, Start relationship's duplicate, and event correction (available by double-click or Enter on the event). Context-specific profile connection menus remain unchanged.

Graph workspaces and standalone graph rendering default to Circle (round). Explicit saved views retain their selected layout and positions. The previous free-space placement behavior for newly added nodes remains active.

## Verification

- Full build: **195 tests passed in 91.336 seconds** (`build-verification/five-types-build.log`).
- Focused migration/type/menu/layout tests: **7 passed** (`build-verification/five-types-focused.log`). Tests cover schema-11 conversion including Trash, exact dropdown values, narrow-window access, round defaults, type round-trips, old drafts, and distinct node placement.
- Packaged smoke: **passed**, version 0.13.0, schema 12, frozen=true (`build-verification/packaged-smoke.json`, `build-verification/five-types-packaged-smoke.log`).
- Source and packaged fingerprints match: `94e323790834716ac8b9e162f315e3bfddb89b6b3491c20ab7e6e4220c0a8596`.
- Verification used automated real-Tk interaction and local packaged smoke. No additional manual native-window, DPI, or clean-machine review was performed.

## Local package

- `dist/StoryAtlas/StoryAtlas.exe` SHA-256: `a1e8e3a65a0830f59b2a66ad9acd396dc641c9a586276f6bc456bf27b8109daf`
- `dist/StoryAtlas-Windows-x64.zip` SHA-256: `9e9eea5af7031b3af5973474d2e6fc864c5b7f1d7a3864903036195cca247cb6`

The archive was rebuilt locally; no publication was performed.
