# Story Atlas — asset-driven visual and menu roadmap

Prepared 28 September 2026 for Story Atlas 0.18.0.

Status updated 29 September 2026: phases 0–3 implemented and independently reviewed on `gui_overhaul`; supporting screens and release verification are being completed for 0.19.0. The sections below preserve the original design proposal and baseline observations. Current evidence and unresolved limitations are recorded in `docs/reviews/gui-overhaul/`. Portrait graph nodes and the other P2/data-model features remain future scope; physical mixed-monitor DPI and representative-user studies are not established by local screenshot tests.

## 1. The direction: an illustrated story atlas

Make Story Atlas feel like a carefully organized storyteller's desk: deep ink surfaces, readable typography, crisp miniature illustrations, and clear relationships between the cast, their events, and their connections.

Use the HAS packs as the main illustration family. Their compact fantasy objects and architecture give the application a recognizable personality. Let typography, alignment, spacing, and state styling provide most of the interface structure. Artwork should help a user recognize a destination or understand story content.

Three visual layers:

1. **Application controls:** quiet surfaces, familiar action symbols, explicit labels, teal primary actions, visible keyboard focus.
2. **Story identity:** character portraits, section emblems, small chapter illustrations, selected inventory and ability motifs.
3. **Atmosphere:** a restrained illustration on Welcome, a chapter overview, or a true empty state. Keep reading and graph surfaces visually quiet.

The target is attractive enough to feel inviting during a long campaign session and calm enough for someone writing a non-fantasy story. Offer an **Illustrated / Minimal** appearance preference, independent of dark/light theme and text size. Illustrated adds decorative section art; Minimal keeps all content and controls with reduced decoration. User-imported portraits remain visible in both.

### What the current app already provides

- Shared dark and light palettes, Segoe UI named fonts, and semantic styles in `story_atlas/theme.py`.
- A graph-first Simple workspace with a task pane and bottom timeline.
- An Advanced notebook with Characters, Chapters & events, Relationships, and Graph.
- Existing selection, unsaved, historical, focus, error, and success treatments.
- Imported portraits stored through `story_atlas/assets.py`, including database-backed bytes and thumbnail support.
- Wrapping action bars and scrolling forms, useful foundations for narrow windows and larger text.

Build on these foundations. The first release can achieve substantial improvement within Tkinter, ttk, and the existing Matplotlib graph.

## 2. Assign each asset pack a specific job

| Pack | Verified local contents | Recommended role | Scope boundary |
|---|---|---|---|
| HAS IconPack v1.2 | 2,762 PNGs, mostly 16×16; equipment, weapons, jewelry, books, artifacts, skill sheets, original/outline variants | Section emblems, inventory/ability headings, curated story symbols | Counts include variants and sheets. Individual icons need visual selection and tagging. |
| HAS Buildings Pack | 288 PNGs and a GIF; towns, castles, mines, mills, landmarks, resources, overworld sheets | Welcome vignette, chapter decoration, future location illustrations | A building illustration does not establish a location database or geographical position. |
| Canari TopDown | 16×16 tiles, 35 item images, three animated heroes, four enemy types; 121 PNGs, 85 GIFs; three music tracks and 16 sound effects | A later optional retro theme, sample-story decoration, optional sprite avatar exploration | Its bright cartoon style differs from HAS. Keep it out of the initial shared interface vocabulary. |
| Hex Kit Classic | 240 PNG tiles, mostly 210×210, with 330×330 variants; terrain and map utilities | Future geographical atlas work or a reviewed static chapter map | Bundled in a Linux application. The relationship graph is not a geographical map. |

The current inventory contains 3,411 ordinary PNG files in total. It is not a count of distinct illustrations. The icon pack also has 27 files with `.png1` through `.png9` extensions; inspect their actual contents during ingestion instead of silently treating them as normal assets.

### First curated set: approximately 30–45 assets

Start with a small reviewed library:

- 6–8 section emblems: identity, story, goals, abilities, inventory, notes, chapter, event.
- 8–12 content motifs: books, equipment, artifacts, jewelry, selected resource objects.
- 6–10 architectural illustrations: towers, castles, towns, mines or mills for scene-setting.
- 3–5 restrained empty-state compositions made from approved artwork.
- A small separate family of simple action symbols for search, add, edit, close, arrows, undo, redo, settings, and connection direction.

The packs do not establish a complete general-purpose application icon system. Create the missing action symbols in a consistent code/vector source and export raster variants for Tkinter, or retain text-only actions. Do not force a sword to mean Edit, a skull to mean Delete, or a potion to mean Recovery.

## 3. Establish the visual grammar

### Color and surfaces

Retain the existing palette as the starting point:

| Role | Dark baseline | Light baseline | Use |
|---|---|---|---|
| Canvas | `#101722` | `#f3f6fa` | Workspace background |
| Content | `#192333` | `#ffffff` | Main grouped content |
| Detail | `#1d2939` | `#f7f9fc` | Read-only information |
| Main text | `#e6edf7` | `#18283d` | Names, controls, prose |
| Primary accent | `#61d4bf` | `#146d61` | Main commit action |
| Selection | `#315469` | `#c8e4ef` | Selected row or destination |

Prototype an optional warmer light canvas only after the first screens are assembled. Treat it as a palette experiment requiring contrast checks. Do not place parchment textures under prose or draw game terrain behind the relationship graph.

Artwork keeps its authored colors. Place it in a consistent small badge or reserved image area when contrast against the surrounding surface is weak. Asset colors never determine whether an action is destructive, selected, successful, or disabled.

Keep character-type colors and relationship-line styles as a separate data vocabulary with the existing legend. An item's rarity color, if ever introduced, must remain separate from both application state and character type.

### Typography and spacing

- Retain Segoe UI for all controls and writing. Keep user-selected 9–16 point body sizes supported.
- Use the existing body, heading, and title roles. Avoid a pixel font for prose or navigation.
- Preserve the existing 6/12/20 spacing rhythm; add smaller icon gaps and larger section margins only as named tokens.
- Use compact 16-pixel assets in dense rows and 32-pixel illustrations in headers where space permits. Larger art belongs to Welcome or selected detail, not every row.
- Reserve consistent image slots and baseline alignment. Transparent padding must not make one icon appear half the size of its neighbor.
- Size the interactive control around its label and padding. A 16-pixel image must not imply a 16-pixel click target.

### States must stay understandable without artwork

| State | Treatment |
|---|---|
| Hover | Small surface change; no movement or bouncing |
| Selected | Selected fill and a clear marker or outline |
| Keyboard focus | Independent high-contrast outline |
| Active graph tool | Pressed styling and an explicit tool label |
| Disabled | Disabled widget behavior and legible subdued text |
| Unsaved | Explicit text beside the active task |
| Historical view | Named event/chapter context; Current remains reachable |
| Saved | Quiet text confirmation near the task |
| Error | Field-adjacent explanation and a useful correction path |
| Destructive | Explicit verb and separated placement |

Select illustrated variants deliberately. Do not assume an asset's supplied Outline version has adequate contrast on both themes.

## 4. Reorganize the menu system around scope

The first menu pass should reduce visual competition while keeping all current commands reachable and retaining their behavior.

### Global header

Proposed wide arrangement:

```text
Story Atlas · Greyhaven     Story ▾    Search    Help ▾    Settings ▾    Mode: Simple
```

The active story title should be visible in both modes. In Simple mode the current implementation filters the header down to Story, Maintenance, and Mode; restore a compact story identity and direct Search access as part of the redesign.

At narrow widths, wrap coherent groups or put less-used commands into labeled menus. Prioritize story identity, Story, Search, and Mode. Do not shrink labels or hide Mode behind an unexplained symbol. The existing `ActionBar` is a useful starting point, but grouping will need explicit layout logic.

### Proposed menu contents and migration

| Menu | Groups | Change from current source |
|---|---|---|
| Story | New / Open / Recent; sample stories; Export; Undo / Redo | Preserve existing commands and shortcut behavior; add separators by task. |
| Help | Help and shortcuts; About; Artwork credits | Move the separate About button here and make provenance easy to find. |
| Settings | Appearance; Recovery, Trash, and drafts; Activity log | Rename Maintenance for discoverability; keep the technical log explicitly labeled. |

This is a proposed label and organization change. Update help text, recovery notifications, documentation, and relevant navigation tests together so users are not directed to a menu that no longer exists. Preserve a migration note in release documentation.

Menu items use clear verbs, optional familiar icons, and a consistent shortcut column. Only show shortcuts that actually work. Use ellipses consistently for commands requiring more input. Submenus should group coherent choices, such as sample stories, rather than contain one orphan command.

Keep actual Tk menu behavior for keyboard navigation, Escape dismissal, disabled entries, and focus return. Platform rendering can constrain menu decoration; reserve larger illustrations for the adjacent workspace instead of replacing menus with custom-painted controls.

### Simple workspace toolbar

Proposed grouping:

```text
New character    Add relationship    New event    |    Next event    |    View ▾    More ▾
```

- Creation controls use restrained secondary styling until a task is opened. Save/Create inside the active task is the strong primary action.
- **View** groups Fit view, graph filters, the existing legend, Zoom/Pan, and information-pane visibility.
- **More** groups saved graph views, export, chapter creation, and infrequent event operations.
- Keep editing and destructive operations tied clearly to the selected event. Display its name in the relevant context.
- Retain the narrow Undo recent character creation behavior separately from general saved-change Undo/Redo; do not imply that the two have identical scope.
- Keep source/target selection controls adjacent to the relationship task. Selected names, Remove, Make source, and Exit selection must remain discoverable.

Evaluate toolbar width with maximum text size before committing the exact grouping. If View hides a frequent action, promote that action based on observed use rather than adding another permanent row.

### Advanced navigation

Keep the four established destinations and add small, consistently spaced emblems where appropriate:

- Characters: a neutral identity motif.
- Chapters & events: a book or scroll motif.
- Relationships: a simple connection symbol created for the interface.
- Graph: a simple node-and-edge symbol created for the interface.

The active tab receives a strong selected treatment; inactive tabs remain quiet. Keep full text labels. A permanent left navigation rail is a later experiment because the current graph and detail panes already compete for horizontal space.

## 5. Screen-by-screen art direction

### Welcome and story setup — first impression

Use one compact HAS architectural vignette above or beside the story title. Keep its size bounded so the actions remain visible in the existing 500×350 minimum Welcome window.

Make Start empty the primary action, Open story secondary, and samples a quieter grouped section. This corrects the present pattern where all four Welcome actions use the same accent style. For Greyhaven, a harbor/town composition is a candidate after exact assets are curated. Use neutral books or architecture for the Frankenstein sample; avoid implying that every story uses a fantasy RPG setting.

Story setup gets a compact book emblem and clear title/opening fields. Artwork must not prepopulate story text or change the user's selected opening.

### Character overview and editor — the first implementation pilot

Create a shared identity header: portrait or neutral fallback, name, character-type text, and concise secondary details. Give imported portraits priority. A fallback should not assign a person's appearance, ancestry, morality, or profession.

Advanced profile overview already renders portraits. Simple summary currently presents text and connections; bring the same identity treatment into it through a reusable component.

Use small HAS emblems beside section headings:

| Section | Illustration candidate | Behavior |
|---|---|---|
| Identity / optional details | Neutral emblem | Opens the existing fields |
| Story | Book or scroll | Existing narrative text |
| Goals | Reviewed artifact or simple target symbol | Existing goals text |
| Abilities | Curated skill-sheet crop | Existing traits/skills fields |
| Inventory | Equipment or chest motif | Existing inventory prose |
| Notes | Book motif distinct from Story, or plain note symbol | Existing notes field |

Keep optional sections collapsed as they are now; show a restrained filled-content indication. Decoration must not make empty sections look complete. Keep Save and Close in their stable bottom action area.

Inventory illustrations initially label the section. Automatically transforming prose into collectible item cards would require an explicit structured-inventory feature and should not be included in this visual pass.

### Cast roster and search — recognition at a glance

Give a cast row a consistent identity area, name, textual type, and concise supporting detail. Preserve duplicate-name IDs where they disambiguate records. Keep selection independent of type color.

The shared table helper uses `Treeview(show="headings")`. Standard Treeview item images belong in its tree column; they cannot simply be added as arbitrary images to existing data cells. Prototype an identity tree column with `show="tree headings"` and preserve existing sorting, selection, keyboard traversal, and scrollbar behavior. Avoid replacing the whole roster with a custom canvas list just to add thumbnails.

Search results should show a small content-type marker and readable context: character, event, chapter, or relationship. Empty search results should explain the search outcome and offer a useful adjustment, without displaying the same illustration as an empty story.

### Relationships — a readable connection ledger

Focus the visual hierarchy on names and direction:

```text
[portrait] Alden  →  Employer of  →  Bryn [portrait]
Effective: Opening scene                    Active

Notes and history
Edit details    History    Change at this event
```

Use the existing semantics to render both perspectives accurately, including mutual relationships. Keep effective-event context, historical changes, inactive states, and correction actions explicit.

Artwork belongs in the identity headers. Relationship meanings remain text and graph line styles. Do not infer friendship, hostility, or romance from a custom label and assign decorative symbols automatically.

### Chapters and events — a browsable chronicle

Use a book emblem for chapters and a simpler marker for events. Improve indentation, spacing, selected-row emphasis, and the detail heading. Let the selected chapter have a small architectural illustration, initially application decoration or sample-specific presentation rather than new saved metadata.

Keep event order and titles dominant. Participants can gain small identity thumbnails where space allows, but retain names and IDs. Historical context must remain distinguishable from selection and unsaved changes.

The bottom Simple timeline stays compact. Show the selected event clearly and keep Current, stepping, and chapter selection operable without relying on artwork. Do not add a building thumbnail to every timeline point.

### Graph and inspector — preserve the app's main working surface

First improve the surrounding controls, legend spacing, scope text, and selected-character inspector. Keep graph dots, type colors, relationship direction, planned/provisional outlines, pins, and focus cues intact.

Prototype portrait nodes only after the surrounding design ships. Use a bounded image cache and separate image decoration from the existing pickable node geometry. Validate dragging, keyboard movement, zoom, pinning, historical filtering, and exports. At dense or distant views retain simple nodes; portrait display should be optional and its threshold established through measurement.

Never decorate the graph with hex terrain. A relationship position represents layout, not where a character lives.

### Empty states, dialogs, and recovery — complete the experience

Use one small illustration, a concrete explanation, and a relevant action in a true empty story. Filtered-empty views should offer Reset filters or change-focus guidance. A missing portrait should use a neutral fallback and keep the rest of the record readable.

Dialogs get the same spacing, labels, and action hierarchy. Recovery and Trash need clear counts, record identity, and explicit restore/delete behavior; elaborate treasure or graveyard imagery would obscure their meaning. Preserve the existing Save / Discard / Stay and chronology-conflict workflows.

## 6. Asset integration architecture

### Separate built-in presentation from user content

Proposed additions:

```text
story_atlas/resources/ui/
  manifest.json
  icons/
  illustrations/
  licenses/
story_atlas/ui_assets.py
tools/build_ui_assets.py
```

Keep `story_atlas/assets.py` responsible for managed user portraits. A separate `ui_assets.py` should resolve packaged artwork by semantic key, such as `section.inventory`, rather than scattering pack filenames through widgets.

Each manifest entry should record:

- Stable semantic key and bundled relative path.
- Source pack, exact original relative path, checksum, and crop rectangle when applicable.
- Native dimensions, output variants, intended roles, and human-reviewed description.
- Author, local license reference, and distribution-review status.
- Fallback key and supported theme/state variants.

Curate from a configurable source directory at build time. Do not depend on `C:\Users\Jonathan\Documents\asset_packs` at runtime. Package only selected assets and retain their provenance. Keep full pack contents out of public source/distribution artifacts unless their terms permit that use.

The included HAS license files explicitly permit product use/modification, request attribution, and restrict standalone public hosting. Preserve the full supplied text and add artwork credits. The inspected Canari README describes the pack but does not establish comparable distribution terms; the Hex Kit application license is not sufficient evidence of artwork rights. Resolve those two packs' artwork terms before including them in a distributed build. This does not block the HAS-first design pilot.

### Image loading and scaling

- Use the existing resource resolver and Pillow/ImageTk dependencies.
- Cache by semantic key, requested size, theme, and state; retain `PhotoImage` references for the lifetime of displayed widgets.
- Create Tk images on the Tk thread and avoid decoding images during graph redraw or repeated row refresh.
- Use nearest-neighbor scaling for authored pixel art. Use the normal high-quality portrait pipeline for photographs and painted portraits.
- Favor 16→32→48 pixel integer multiples where the layout allows. At Windows fractional scaling, compare a centered integer-sized image against nearest-neighbor scaling to the actual target size. Choose based on readability and geometry; do not promise uniform pixel blocks at every fractional factor.
- Load only the artwork needed for the visible interface. Keep caches bounded and release resources when windows close.
- Missing or invalid decorative files fall back to text or a neutral symbol without preventing startup or access to records.

Ttk supports image-plus-text controls and state-aware image choices; its standard styling APIs provide the required foundation. See [Python's ttk documentation](https://docs.python.org/3/library/tkinter.ttk.html). Nearest-neighbor is one of Pillow's supported resampling filters; see [Pillow filter documentation](https://pillow.readthedocs.io/en/stable/handbook/concepts.html#filters). Validate the implementation against the project's pinned runtime rather than adopting APIs solely because they appear in newer documentation.

### Packaging and identity

`StoryAtlas.spec` already includes the resources directory. Verify nested assets and license files in the actual Windows package. Add an asset-manifest digest to build metadata or extend build identity: the current `source_fingerprint()` hashes Python sources but does not identify artwork changes.

The initial presentation pass needs no story-database schema migration. The Illustrated / Minimal choice is an application setting. User-selected per-character symbols or chapter covers would introduce saved content and require a separate persistence, export, backup, and compatibility design.

## 7. Delivery phases and acceptance gates

Effort ranges below are planning estimates for one developer, including focused verification, not calendar commitments. They assume the present stack remains in place and no new story data model is introduced.

| Phase | Work | Estimated effort | Reviewable output / exit gate |
|---|---|---|---|
| 0 — Baseline and curation | Capture current screens; catalog and deduplicate candidates; record provenance; identify semantic gaps | 1–2 days | Contact sheet and approved 30–45 asset shortlist; baseline captures for both modes/themes |
| 1 — Foundation and pilot | Asset manifest/cache, fallback behavior, reusable icon-label and identity header; implement one character overview | 2–4 days | Same character rendered well in Simple and Advanced; readable at small window and largest text |
| 2 — Menus and navigation | Global header, menu grouping, shortcuts, Advanced tab treatment, Simple toolbar | 2–3 days | Every old command accounted for; keyboard routes and unsaved guards preserved |
| 3 — Core reading and editing | Profile sections, roster/search markers, relationship details, event/chapter hierarchy, compact timeline polish | 4–6 days | Complete create → connect → event → inspect workflow with consistent visuals |
| 4 — Supporting screens | Welcome, setup, empty states, dialogs, recovery, credits, Minimal preference | 2–3 days | Complete first-run and recovery flows; settings persist; no decorative dependency on data access |
| 5 — Release verification | Visual matrix, functional regressions, performance comparison, packaged build and DPI checks | 2–3 days | Verified screenshots and release report; clean-machine package resolves all included assets |

**Core release planning range: 13–21 developer-days.** Review the estimate after the Phase 1 pilot. Windows scaling or Treeview layout issues may materially affect the range.

Phase dependency: baseline → shared foundation → navigation → core screens → supporting screens → release verification. Do not begin a second icon framework in a later screen; extend the shared one.

### First vertical slice

Build these together before styling the entire app:

1. One HAS book, equipment, and ability emblem with verified source metadata.
2. Asset cache and text fallback.
3. Shared character identity header with imported portrait support.
4. Matching section headings in the profile editor and Simple summary.
5. One revised labeled action group with proper hover, focus, disabled, and primary states.
6. Dark/light and narrow/large-text captures of the same character.

This slice answers whether the art reads at real sizes and whether the composition feels coherent. If it feels too busy, reduce artwork density before spreading it to other screens.

## 8. Concrete implementation backlog

| Priority | Ticket | Primary files | Completion condition |
|---|---|---|---|
| P0 | Inventory and asset provenance | New build tool and manifest | Every bundled image traceable to original bytes and terms |
| P0 | Asset loading and fallback | New `ui_assets.py`, `paths.py` | Works in source/package, handles missing image, retains Tk references |
| P0 | Reusable illustrated components | `widgets.py`, `theme.py` | Shared sizing, spacing, focus, icon/text and theme behavior |
| P0 | Character pilot | `profile_overview.py`, `simple_summary.py`, `profile_editor.py`, `simple_profile.py` | Clear read/edit distinction with shared identity treatment |
| P1 | Header and command map | `app.py`, `simple_workspace.py`, `guidance.py` | All commands preserved; updated help/menu references |
| P1 | Chronology and relationships | `event_view.py`, `simple_timeline.py`, `relationship_roster.py`, `graph_inspector.py` | Accurate direction/history and readable selected detail |
| P1 | Roster and search markers | `character_roster.py`, `global_search.py`, shared table helper | Images do not disrupt selection, IDs, sorting, or keyboard use |
| P1 | Welcome and supporting screens | `onboarding.py`, `story_setup.py`, `appearance.py`, `settings.py`, recovery dialogs | Cohesive first-run and smaller-window behavior |
| P1 | Package assets and credits | `StoryAtlas.spec`, `version.py`, build metadata tooling, About/help | Curated assets, credits, and artwork identity present in build |
| P2 | Optional portrait graph prototype | `graph_render.py`, graph interaction/export modules | No loss of pick/drag/pin/history behavior or measured responsiveness |

File ownership here identifies likely implementation seams, not a claim that edits are already made. Review callers and current tests before changing shared helpers.

## 9. Verification: prove that it is prettier and still useful

### Capture matrix

Review the same representative states in both themes and modes:

- 1180×720 default workspace; 900×600; 760×480 supported minimum.
- Body text at 10 and 16 points; spot-check the full supported 9–16 range.
- Windows 100%, 125%, 150%, and 200% display scaling, including an actual move between monitors with different scaling where hardware is available.
- Empty story, populated Greyhaven, duplicate names, long names/prose, missing portrait, active form, validation error, historical event, planned character, and filtered-empty graph.
- Welcome at its own minimum and default sizes.

Simulated Tk scaling is useful but does not establish correct Windows per-monitor behavior. Record which physical configurations were actually reviewed.

### Functional acceptance

- All existing commands remain reachable by keyboard and menus close/return focus correctly.
- Save/Discard/Stay, drafts, restore, chronology validation, and relationship save/clear/refocus behavior remain intact.
- Changing theme, mode, illustration preference, or window size does not lose edits, scroll position, selection, graph positions, pins, or historical scope.
- Relationships retain meaningful directional text; planned/provisional nodes retain their visual distinctions.
- Inspecting records does not create drafts or modify content.
- Missing artwork produces a useful fallback, not an exception.

### Visual and performance acceptance

- No labels, controls, section headings, or primary actions clip at the supported dimensions.
- Artwork stays legible against both themes. Focus and selection remain recognizable in grayscale.
- Ordinary text targets at least 4.5:1 contrast; essential large text and non-text boundaries target 3:1. Treat these as design acceptance targets, not a claim of complete accessibility conformance.
- Users can identify their active story, workspace, selected record, and next action without interpreting an icon.
- Record first paint, view switches, theme changes, image cache behavior, graph redraw, and memory use on the current build before implementation. Investigate regressions above a provisional 10% relative threshold, using repeated measurements and absolute timings to distinguish noise.
- Exercise the established 100-character/300-relationship case with portraits absent and present. Preserve keyboard and pointer responsiveness.
- Have a few representative users create a character, connect two characters, move to an event, find a historical connection, and recover a draft. Record hesitation and wrong turns rather than merely asking whether they like the artwork.

Run the existing appearance and workflow checks plus focused tests for the asset loader, fallbacks, preference persistence, and packaged resource completeness. Screenshot review supplements these checks. This roadmap itself makes no claim that those future checks have passed.

## 10. Later opportunities with separate product scope

| Opportunity | Asset fit | Prerequisite |
|---|---|---|
| User-chosen chapter covers | HAS buildings/landmarks | Persisted cover reference, picker, exports/backups, neutral default |
| Structured inventory cards | HAS equipment and artifacts | Item records, quantities, ownership, notes, history decisions, migration |
| Location atlas | HAS architecture plus reviewed Hex Kit terrain | Stable location IDs, map coordinates, placement tools, character-location semantics, rights verification |
| Expanded avatar picker | Curated sprites or symbols | Deliberate user choice, storage/export rules, sufficient representation |
| Optional retro presentation | Canari art | Rights verification and a complete alternate style specification |
| Subtle ambient animation/audio | Canari GIF/WAV or animated HAS art | Explicit opt-in, mute/reduced-motion support, lifecycle/performance controls |

These should not delay the core visual release. In particular, background music, animated menu sprites, a custom-painted menu engine, and a geographic map editor add complexity with little benefit to the immediate readability problem.

The first milestone should produce a polished character overview and editor with coherent section emblems, then carry that same vocabulary into menus, chronology, and connections. That gives Story Atlas a recognizable identity while making its everyday workflows easier to read.
