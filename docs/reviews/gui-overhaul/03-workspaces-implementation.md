# Stage 03 — core workspaces (integration review in progress)

Identity headers place imported portraits beside names and populated metadata. Missing-image feedback wraps with available width; a record without a portrait keeps the neutral `No portrait` label contract without reserving display space. Advanced metadata omits unset fields. Simple and Advanced retain the same managed portrait pipeline in Minimal mode.

`tree_art.install_tree_art` adds a fixed Treeview image column while preserving all existing values, selection IDs and navigation callbacks. Character/relationship rosters display managed portraits or optional identity motifs; search and chronology use semantic section markers. Images refresh in place through `atlas_refresh_art`, preserving dirty forms and selection. The root-owned portrait LRU holds 128 entries keyed by database path and immutable portrait filename; misses are not cached so recovery works without restarting.

Character and relationship workspaces compact secondary headings/action groups at short heights. Secondary actions remain in labeled menus. Simple short-window toolbars relocate New event/Next event into More and collapse summary actions to Edit/Actions. Normal-sized controls return on resize. Active compact graph filters remain explicitly summarized. Global contextual tips collapse in short windows; Help/F1 retains the complete guidance.

Chapter/event outlines and prose sections use restrained motifs. Relationship direction, selected-record details and historical state remain text. No schema, chronology or inferred relationship semantics changed.

Tiny graph canvases omit the in-plot legend/title and expose legends through native menus in both modes. Compact Advanced filters offer Focus character, Focus scope and Show labels through the existing Filters menu. Timeline marker positions use actual canvas height rather than clipping at fixed y=61 in a 40-pixel canvas.

## Validation after minimum-layout review

- Initial 41 existing focused tests passed in 27.912s.
- Added tests exercise portrait miss/recovery, unchanged tree values/selection, dirty-form preservation, Minimal artwork removal, populated minimum-size reading regions, and timeline bounds.
- Independent reviewer added portrait persistence and cross-database cache tests.
- Screenshot review exposed additional minimum-window starvation. Advanced graph controls now use natural widths and force a presentation refresh when compact mode changes; the stale long summary no longer consumes the plot. Compact relationships keep the list and move selected-record operations into the global More menu; Read selected connection provides its full selectable text.
- Reviewer implemented compact Character guidance/status/roster fixes, independently checked by the implementation agent. Saved status no longer competes with the overview; true unsaved/error context stays visible. Selected character names and cast rows are tested at the minimum window size.
- Graph export temporarily uses a bounded full presentation size so exported PNGs keep their scope title and legend, then restores the live figure size/layout in a finally block. Limits, graph positions and pins are preserved.
- Latest focused workspace/art/independent-review/appearance/visual run: **19 passed in 15.149s**, no skips. Includes minimum reading regions in all Advanced destinations and compact PNG export scope/restore verification. Reviewer's separate compact Character/profile/UX run: **21 passed in 10.766s**.
- Source frozen for the primary's corrected window captures. Full regression and final visual acceptance remain integration gates.

The second capture exposed an initialization-specific graph issue absent from the simple fixture: loading 16-point preferences before startup caused Configure before Map, so the compact controls appeared but their summary stayed verbose. Compact transitions now refresh presentation even before mapping. The regression uses the real Greyhaven sample, its first historical event and planned cast, and checks the selected relationship cast row is actually visible. Narrow graph names wrap to two lines with an ellipsis where necessary; inspection and full-size exports preserve complete names. Compact relationship roster padding/labels leave room for cast rows.

Final focused repeat after these fixes: **20 tests passed in 17.199s**, no skips. A 10-case minimum-window capture is the next visual gate; no claim of final acceptance is made before that review.

The minimum capture then confirmed graph geometry but showed density problems with 19 names in a tiny plot. Label budgets now derive from actual axes area and font size (2–35 names), while preserving selected/nearby, pinned and ordered-selection identities. Edge labels use a corresponding density budget. Narrow names and state cues wrap; full names/explanations remain in inspection and exports. Compact Advanced graph navigation moves into Filters → Graph navigation & layout, returning another toolbar row to the plot and restoring the normal toolbar at larger heights. Selected planned characters retain explicit PLANNED/SELECTED labels and full inspector explanation.

Latest focused repeat: **21 tests passed in 17.848s**, no skips. Added tests compare 18-name visibility in large/small canvases, deliberate selection/pin/ordered exceptions, and navigation-menu reachability. Source frozen again for the final minimum capture/full regression gate.

Final review refinements preserve visible checked Zoom/Pan menu state in compact mode, prove full long names are present during enlarged export, and keep sparse graph labels centered with boundary clamping only when their actual rendered boxes exceed the canvas. The two-node long-name test verifies boxes do not overlap and remain inside the canvas. Latest focused run: **23 tests passed in 20.695s**, no skips. Frozen source fingerprint: `447711b9629de7fac5577b2e1e2724f985c9744bd346948d06c61524865d73f0`.

The full regression run found a transient provisional-node cleanup failure: its model position can disappear before the queued redraw removes its annotation. Alignment now uses the annotation's existing data anchor (`label.xy`), which is also updated during ordinary dragging. The reviewer independently confirmed this preserves steady-state geometry. Added an explicit missing-position regression. **47 focused Simple mode/rework/undo/workspace tests passed in 39.154s** after the fix; the full suite is rerunning as the final integration gate.

Full regression, capture review and repeated performance comparison remain integration gates. Physical Windows per-monitor DPI remains an external validation limitation.
