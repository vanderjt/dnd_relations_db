# Unified character type and free-space node placement

24 September 2026 — Story Atlas 0.12.0, schema 11, export format 7.

## Changes

Both profile editors now expose one **Character type** dropdown: Minor NPC, Protagonist, Antagonist, NPC Enemy, Player Enemy, Neutral, NPC Ally, and Player Ally. It replaces classification, narrative role, and the separate writing-template selector. The optional writing-prompt button uses this choice and fills only empty prose fields. Graph badges, colors, filters, summaries, and profile details use the unified type.

Migration preserves existing pairs such as `NPC Ally · Protagonist` as a single retained value instead of discarding either label. Legacy storage fields remain synchronized for compatibility. Older exports and drafts are still readable; migration creates a backup before changing the schema.

New graph nodes search for free space around the viewport center with screen-space clearance. Placement checks all saved positions, including hidden characters. Existing coordinates remain unchanged, and provisional nodes keep their position after saving. When the viewport is full, Simple mode pans to reveal the new node while retaining the zoom span. Clearance accommodates typical names and badges; arbitrarily long labels can still overlap.

## Verification

- Full build suite: **193 tests passed in 91.451 seconds**. See `build-verification/unified-build.log`.
- Added coverage for schema-10 migration and backup, all character types through duplicate/Trash/restore/export/import, old draft recovery, both editors, twelve consecutive provisional/save cycles, direct additions, and sixty placements in a zoomed viewport.
- Packaged smoke: **passed**, `frozen=true`, version `0.12.0`, schema `11`. Includes unified-type persistence and distinct provisional placement. See `build-verification/packaged-smoke.json` and `build-verification/unified-packaged-smoke.log`.
- Source and packaged fingerprints match: `d4c4ca064a3b799782bfacbb577e83f17345588bb41d6f5a27b87992e4921557`.
- This follow-up uses automated real-Tk interaction and packaged smoke checks. No additional manual native-window, DPI, or clean-machine review was performed.

## Built artifacts

- `dist/StoryAtlas/StoryAtlas.exe` SHA-256: `846fd913e0747a319df028774fc551b4a9192133c15524fd37c7c00ddd4dba5f`
- `dist/StoryAtlas-Windows-x64.zip` SHA-256: `3129d6b8db7b4c3d6f5ac5428366a2ca31dab217314995a9353fface0552be9c`

The Windows archive was rebuilt locally and has not been published.
