# Stage 02 — navigation and command grouping

The header now shows the active story in both modes, followed by Story, Search, Help, Settings and a grouped Mode selector. Advanced retains Back. The full title remains in the OS window title; the header uses font-measured elision bounded by available window width. Help contains native menu entries for shortcuts, About and Artwork credits. Story groups file operations, samples/export and saved-change undo/redo. All existing callbacks and unsaved guards remain in place.

Simple toolbar keeps New character, Add relationship, New event and Next event, then View and More. View groups presentation commands; More groups chapter/event operations, saved views/export and the narrowly scoped undo-creation action. The legend's existing menu object remains available to tests/callers and is now reachable as a native View submenu. Character-selection controls are unchanged.

ActionBar now measures independent row containers, eliminating shared grid-column widths across different rows. Rows use explicit measured geometry to avoid requested-size feedback; individual controls retain grid management and existing `grid_forget` callers. Destroy/recreate selection-chip flows prune stale row containers. Native ttk focus and keyboard behavior remain intact. Clam control bevels inherit semantic border colors instead of pale default chrome.

Advanced Characters and Chapters & events tabs use existing semantic book emblems; Relationships and Graph retain their readable text labels. Composite widgets can provide `atlas_refresh_art()` for live appearance updates; tabs retain their own image references and remove decoration in Minimal mode.

## Command migration map

| Previous location | Current location |
|---|---|
| Header Search / Story Search | Header Search; Ctrl+K unchanged |
| Header Help / Story Help | Help → Help and shortcuts; F1 unchanged |
| Header About / Story About | Help → About Story Atlas |
| Maintenance → Appearance | Settings → Appearance |
| Maintenance → Recovery, Trash, drafts | Settings → Recovery, Trash, and drafts |
| Maintenance → Activity | Settings → Activity log (Advanced) |
| Story sample commands | Story → Sample stories |
| Story new/open/recent/export/undo/redo | Story, grouped with separators |
| Simple More → Fit/planned/filters/pane/zoom/pan | Simple View |
| Simple Legend button | View → Legend · dots & links (same filter commands) |
| Simple More → chapter/edit/remove event/saved views/export/undo creation | More, grouped with separators |
| Header Mode / Advanced Back | Header Mode / Advanced Back |

README, distribution instructions and runtime recovery/help text now use Settings. This is a menu-label migration only; recovery data and command semantics are unchanged.

## Validation

Focused navigation, appearance, character-type placement and legend suite: **24 tests passed in 17.161s**. New tests exercise a long story title at 760×480 and 16-point text in both modes, fixed-width 10→16-point appearance changes, Minimal tab-art removal, command destination completeness, existing callback routes, independent toolbar widths and destroyed-row recovery. ActionBar refreshes on appearance changes and coalesces child geometry changes through an idle callback, canceled on destruction. Existing command-location expectations were updated for Fit view moving from More to View. Full regression and screenshot review remain integration gates.
