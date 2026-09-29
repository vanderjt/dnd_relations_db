# Story Atlas: visual language cleanup

Draft, 23 September 2026. This began as a proposal based on source and theme
definitions, not a manual visual audit or observed usability study. The status
section below separates the visual-language work now implemented from the
remaining proposals. Preserve the current feature set and dark/light themes.

## Implementation status — 23 September 2026

The subsequent [implementation review](VISUAL_REVIEW.md) records keyboard,
history access, graph scope, detail readability, and duplicate-name fixes.

Implemented in the source UI:

- Shared semantic ttk styles for primary, secondary, navigation, destructive,
  and selected-tool actions; separately tuned navy/slate and teal dark/light
  palettes; visible focus rings independent of selected rows.
- Content, detail, and context surfaces; selectable, copyable scrollable
  read-only detail text used by Relationships, the graph inspector, and the
  selected-event detail area. Editable text fields remain visually inset.
- Relationship workspace regions, cast/context correspondence, perspective
  rows with textual arrows and IDs, selected-record actions, local deletion
  undo, and retained pane sizing.
- Primary/secondary/navigation/destructive action hierarchy in character,
  relationship, event, and history flows, including batch relationship entry
  save/clear/refocus behavior and field-adjacent validation.
- Quiet success feedback and explicit unsaved/historical context. These use
  words and symbols as well as color.
- Graph scope/navigation grouping, selected Zoom/Pan toggles, historical scope
  context, and focus/selected/pinned node labels plus inspector explanation.
- Events chronology scanning columns for order, title, participants, and
  recorded changes; compact participant previews; a bounded scrolling selected
  event detail area with contextual change/graph actions.

Still proposals or validation work:

- A moderated/observed usability study and grayscale or color-vision screenshot
  inspection have not been performed. Palette contrast measurements and widget
  tests do not establish accessibility conformance.
- A physical-laptop visual review and Windows per-monitor DPI transition test
  remain outstanding. The current Windows Tk runtime reported 96 DPI / 100%
  logical scaling; this is not a multi-display verification.
- Not every legacy/support screen has migrated from compatibility `Accent` or
  default button styling. This plan deliberately does not authorize a blanket
  restyle of Activity, Recovery, onboarding, search, or project-management
  screens.
- The Events table uses restrained headings and surfaces rather than an added
  timeline marker; no storage or ordering model has changed.

## Design objective

A user should quickly recognize where they are, what is selected, what can be
edited, and the next action. Build that recognition through consistent hierarchy,
grouping, and state indicators rather than additional permanent instructions.

## 1. Give color a small, consistent vocabulary — first priority

Keep the existing navy/slate surfaces and teal identity. Assign semantic roles
instead of adding a different color to every page or character:

| Meaning | Proposed treatment | Additional cue |
|---|---|---|
| Primary action | Filled teal button | Specific verb: Save relationship, Record change |
| Secondary action | Neutral surface/outline | Clear text label |
| Navigation | Quiet text/menu control | Destination, arrow, or tab underline |
| Selected object | Blue-tinted row or region | Strong outline/marker and named detail heading |
| Keyboard focus | Distinct high-contrast outline | Remains visible independently of selection |
| Active tool | Selected toggle treatment | Pressed state and label, e.g. Pan on |
| Unsaved / historical context | Small amber-tinted status area | Explicit Unsaved changes or Viewing Chapter 5 text |
| Save success | Brief, quiet confirmation | Check mark and Saved text |
| Error / destructive action | Red detail or outline | Error message or explicit Delete label |

The current graph Zoom/Pan modes use Accent.TButton, the same style as primary
save/create actions. Give active tools their own toggle style. Avoid making
success messages, tags, and ordinary headings compete with the primary action.

Use separately tuned light-theme colors, not a simple inversion. Measure all
text, boundaries, selected states, and focus rings on their actual backgrounds.
Color must never be the only way to identify direction, selection, or an error.
This follows [W3C guidance on use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color).

Graph edge colors are a separate, locally explained data legend. Keep their
existing line-style distinctions and labels; do not use graph colors to signal
whether the app has saved successfully. Do not invent emotional categories for
custom relationship types.

## 2. Use three clearly recognizable regions — first priority

Across Characters, Events, and Relationships, organize the page as:

1. Context: selected character/event and concise counts or status.
2. Content: the profile, timeline, connections, or graph being explored.
3. Actions: commands that act on that content, close enough to make their scope clear.

Use a dark canvas, slightly lighter content surfaces, and visible input fields.
Do not put every label inside a bordered card. Define boundaries around meaningful
groups, with more space between groups than between related fields.

For Relationships, distinguish the cast sidebar, connection list, and selected
connection details with subtle surfaces and headings. The selected cast row and
right heading should clearly name the same character. Label the detail area
“Selected connection”; keep full notes readable there.

Group global actions such as Add relationship separately from selected-record
actions such as Edit details and History. Keep selected-record actions adjacent
to the detail area. Maintain a compact menu for less frequent operations. Avoid
repeating the earlier wrapping-toolbar geometry problem when moving controls.

The use of spacing and bounded regions follows [NN/g's proximity guidance](https://www.nngroup.com/articles/gestalt-proximity/)
and [common-region principle](https://www.nngroup.com/articles/common-region/).

## 3. Establish an action hierarchy — first priority

Use one primary action per task region or dialog. Other controls should differ
by purpose rather than all looking like equally prominent rectangular buttons:

- Save/Add/Record: filled primary button in a stable location.
- Edit/View history: neutral secondary button or labeled menu.
- Next: events / Explore graph: quieter navigation treatment with an arrow.
- Delete: clearly labeled destructive action, separated from routine commands.
- Close/Cancel: neutral and consistently placed; remain keyboard accessible.
- Undo: show near the deletion confirmation when relevant rather than giving a
  permanently disabled button the same prominence as routine actions.

Do not automatically navigate after Save. Keep the relationship save/clear/
refocus/stay-open contract exactly as it is. Do not hide the only discovery path
to an action in an unlabeled icon or hover-only control.

## 4. Make read-only information look different from a form — first priority

Currently relationship details and the graph inspector use the same text-area
helper as editable fields, then disable editing. A user can reasonably interpret
the border and fill as an invitation to type.

Create a read-only detail style: content-panel background, quiet border, no input
focus treatment, and a visible Edit details action. Retain text selection, copying,
scrolling, and keyboard access. Avoid recreating a large form just to display data.

Editable fields should have a consistent inset surface and a visible focus ring.
Place labels above inputs and validation messages immediately below the relevant
field. Keep the relationship preview visually distinct from the inputs: it is a
description of the proposed result, not another field to fill out.

## 5. Reduce repeated prose through hierarchy — second priority

Use four levels: page title, section heading, body text, supporting metadata.
Keep the user-selected body size; scale the other levels from it. Use weight and
spacing before increasing font sizes further.

Names and types should dominate relationship rows. IDs, factions, and other
metadata should be quieter but readable. Never hide IDs entirely: duplicate
names and parallel connections need reliable disambiguation.

Replace redundant permanent paragraphs with a short hint, a labeled explanation
control, or the existing F1 help. Preserve safety-critical information about
historical versus Current state, unsaved input, and separate commit boundaries.
Do not fade essential labels until they resemble disabled controls.

Extend the existing spacing tokens deliberately: roughly 6–8 units within a
field/action group, 12–16 within a panel, and 20–24 between sections. Treat these
as starting values to test at supported text sizes, not fixed pixel requirements.

## 6. Make relationship rows easier to scan — second priority

Within a selected-character view, the heading already identifies the character.
Consider concise rows such as:

    ↔  Thorne Blackwood    Friend                 #12
    →  Pip Copperwhistle  Mentor / Mentee        #18
    ←  Garrick Voss       Blackmailer / Victim   #23

Keep an explicit perspective label near the list, e.g. “Connections from Mira's
perspective,” and a compact legend. In All relationships, continue showing both
endpoint names. The detail panel should always show the complete connection and
explain inverse roles so the shorthand cannot imply reversed semantics.

Use arrow shapes and text as the primary signal. If direction receives a tint,
keep it subtle and consistent; do not color every row by its relationship type.
Use row separation and sufficient padding, with restrained alternating surfaces
only if scanning tests show a benefit.

## 7. Visually separate graph scope from graph tools — second priority

Group “what am I viewing?” controls together: event, focus, scope, and filters.
Group “how do I move around?” controls separately: Zoom, Pan, Fit, and View/layout.
Keep a compact visible statement of the current scope rather than a long toolbar
sentence. Examples: “Mira · Direct · Both directions” and “Viewing Chapter 5.”

Use a distinct marker or short label for each node state: focus, selection, and
pinning. Selection and pinning currently share a gold outline, while focus uses
size. Make selected nodes visually identifiable even when already pinned, and
explain the state in the inspector. Do not add faction colors to nodes by default;
edge meaning already needs color and the graph can become visually overloaded.

In historical views, show a persistent event badge and an explicit Current action.
Historical context must not look like an error. Continue making corrections to
Current versus historical states explicit before committing.

## 8. Present events as a readable chronology — later refinement

Retain the existing data and ordering. Visually group each event's title, sequence,
participant summary, and recorded-change count. Use modest separators or a narrow
timeline marker so order is apparent without scanning a dense table.

The selected event's details should contain its relationship changes and their
actions, grouped together. Keep long summaries in a scrolling detail area; do not
let expanded content push the event list off a laptop-sized window. Prototype
this treatment before replacing the existing table.

## Suggested implementation passes

1. **Shared styles:** semantic colors, primary/secondary/navigation/toggle styles,
   focus states, surface styles, and read-only detail presentation in theme.py.
2. **Relationships pilot:** apply the styles and action grouping to one workspace;
   validate that users identify selection, direction, and editing without coaching.
3. **Consistency:** extend the proven patterns to Characters, Events, dialogs, and
   the graph inspector. Consolidate duplicated explanatory text.
4. **Graph and chronology refinements:** separate scope/tools, clarify state
   markers, and prototype a more readable event presentation.

Keep changes within Tkinter/ttk and the existing renderer. No schema changes,
workflow framework, new UI toolkit, or feature expansion should be needed.

## Acceptance checks

- Ask users to identify what is selected, what is editable, and the primary action
  before clicking. Compare accuracy and hesitation with the current interface.
- Correct an incoming relationship without reversing it; distinguish Current
  from a historical view; distinguish a pinned node from the selected node.
- Verify keyboard-only operation, visible focus, text selection/copy, long names,
  duplicate names, long notes, and empty/disabled/error/success states.
- Test both themes at 900×600 and 1280×720, supported text sizes, simulated scaling,
  and actual Windows display scaling when a suitable display is available.
- Inspect screenshots in grayscale and use contrast/color-vision checks; do not
  claim accessibility compliance from a palette change alone.
- Preserve all existing functional tests, especially batch relationship entry,
  failed-save retention, history review, Back navigation, and story-scoped Undo.

The changes should be judged by easier recognition and fewer mistakes, not simply
by whether the interface looks more polished.
