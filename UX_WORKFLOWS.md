# Story Atlas: simpler goal-based workflows

Assessment: 23 September 2026. This began as a source-based UX review, not an
observed usability study or a manual visual inspection. The implementation status
below reflects code and automated checks; proposed benefits still require testing
with writers.

## Implementation status

The following recommendations are implemented in the current application:

- Main story tabs now follow Characters → Events → Relationships → Graph, with
  contextual Next actions and Activity log available through Maintenance.
- Relationships uses a searchable cast pane and a resizable connection/notes pane;
  arrow labels keep source/target roles explicit from either character's perspective.
- Choosing graph Focus switches to Direct connections, fits the view, and enlarges
  the focused node. Inspector selection and stored graph views remain independent.
- Fresh expanded Greyhaven samples contain 18 characters, 50 stored connections,
  and ten narrative events; the Story menu creates a separate sample database.

- Profile, graph-inspector, and relationship-search actions open the exact
  relationship editor/history and return to their originating context.
- Profile-link and Graph → profile navigation use descriptive Back destinations,
  preserving the recorded graph context where applicable.
- Relationship entry supports in-flow name-only character creation, explicit
  profile Source selection, and save/clear/refocus batch entry.
- Events show recorded relationship changes and provide the event-bound review
  flow, including creation of a missing event without committing the change.
- Completion feedback and Trash-backed Undo are available for character and
  relationship deletions.
- Profile editing retains its section and scroll position on save; overview
  section edits and collapsible long sections are available.
- Story and maintenance actions are grouped; Events and Activity log are
  distinct. Graph focus/scope/Fit remain visible while secondary filters and
  view/layout actions are grouped, with active filters and historical context
  always summarized.

Remaining recommendations are user research rather than unimplemented product
claims: observe writers completing the goals in the Validation section, assess
discoverability of the new menus and recovery notification, and make changes only
from those findings. No observed usability improvement is asserted here.

## Main recommendation

Let users finish an action from the character, relationship, graph selection,
or event they are already looking at. Carry their context into the action,
show its result there, and provide a clear return path when navigation is needed.

The app currently organizes many actions by feature area. A writer thinks
“Mira and Thorne stop being allies in chapter five”; the app requires them to
know how Events, Relationships, History, and Graph fit together. More general
help text alone will not remove that coordination work.

Keep Characters, Relationships, Graph, and Events as useful browsing views.
First connect their existing capabilities. A wholesale navigation redesign
would add migration and relearning costs before proving the simpler changes.

## Original gaps and implemented outcomes

This table records the baseline that motivated the work. Its “Current behavior”
column is historical context; the listed completion paths have been implemented
as summarized above.

| User goal | Current behavior verified in code | Proposed completion path |
|---|---|---|
| Connect the character I am reading about | Profile → Add relationship opens a fully empty dialog, including Source. With fewer than two characters, a message tells the user to create another elsewhere. | Open the dialog locally, offer an explicit “Use Mira as Source” action and “Create character…” beside selectors. Return newly created characters to the same pending entry. |
| Fix a relationship shown on a profile | Profile connection rows link to the other character; they do not expose editing or history. | Relationship row → Edit relationship → Save → same profile and scroll position. |
| Change a connection while exploring the graph | Inspector displays selected edge details. Its actions concern nodes: Open profile, Pin, Focus here. | Selected edge → Edit details / Record story change / View history. Close the action to return to the same graph selection and camera. |
| Record a betrayal in chapter five | Events creates an event and can open its graph; recording relationship changes is under Relationships → History → Record story change. | Event → Add relationship change → choose connection → describe change → review → Record change. Show the result under that event. |
| Add a missing prerequisite mid-task | Relationship entry requires two existing characters. The historical state editor offers existing events without a create-event action. | Create the missing character or event inside the current workflow, then resume it without re-entering information. |
| Follow a connection and return | Opening another profile changes the selected character; there is no profile navigation history. | Back to Mira, preserving search, filters, selection, editor state, and scroll position. |
| Correct something found through search | A relationship search result closes search and selects a Relationships table row. The user must discover the next action. | Offer explicit View, Edit details, and View history for the result; retain “Back to search results.” |
| Recover something just deleted | Deletion directs the user to Recovery; Trash is another tab there. | “Mira moved to Trash · Undo.” For older deletions, a direct “Open Trash” action remains available. |
| Make a small profile update | The editor contains all identity and long-text sections; saving always switches to Overview. | Edit the chosen section; Save stays in the editor. A separate Done action returns to Overview. |

Source anchors: `characters.py` (`add_relationship`, `save`, `open_character`),
`profile_overview.py` (`refresh`), `graph_inspector.py`, `event_view.py`,
`history_dialog.py`, `global_search.py` (`open_selected`), `recovery.py`, and
`profile_editor.py`.

## Implemented workflow details

The Priority 1–3 sections below are retained as implementation specifications and
acceptance criteria. Their described interface changes are implemented; the
Validation section is the remaining recommendation for observational testing.

## Priority 1: complete actions in place

### A. Give each relationship the same action entry points

1. Add a compact relationship action menu to profile rows and graph edge details.
2. Offer **Edit details**, **Record story change…**, and **View history**.
3. Reuse the same underlying editors from the relationship table and search.
4. Name both characters and the relationship type in the editor heading. Multiple
   connections between a pair must remain individually identifiable.
5. On successful save, refresh the originating content without navigating away.
   On failure, keep input, focus, and the originating view intact.

Use one visible primary action and a labeled More menu where space is limited;
do not add every possible command beside every row.

Acceptance: a relationship found on a profile or in the graph can be corrected
without visiting the Relationships tab. Closing the editor restores keyboard
focus to its launch control or a sensible replacement if that item disappears.

### B. Add an explicit return path

1. Introduce a small navigation controller with typed destinations and a Back
   stack. Capture story ID/path, object ID, selected tab, filters, scroll, graph
   camera/focus, and event context where relevant.
2. Use descriptive labels such as **Back to graph** and **Back to Mira**.
3. Preserve unsaved edits with the existing save/discard/cancel rules; do not
   force a save merely to browse another top-level view.
4. Invalidate destinations when switching stories. Handle deleted objects with
   a clear message and a valid fallback instead of navigating by a stale ID.
5. A historical graph must retain a visible **As of Chapter 5** label. Opening
   a current profile should explicitly say it shows Current; returning restores
   the historical graph. Never silently correct Current from historical context.

Acceptance: Graph → profile → connected profile → Back → Back restores the
original graph view, selection, event, positions, and zoom.

### C. Turn prerequisite warnings into continuation actions

1. Add **Create character…** beside relationship selectors and in the fewer-than-
   two-characters state. Require only a name; show optional details on demand.
2. Keep the pending relationship values while presenting a small creation step.
   Prefer replacing the dialog body with a Back link over stacking modal windows.
3. After explicit creation, return the new character to the selector the user
   started from. Duplicate names still show IDs; never merge by name.
4. Provide equivalent **Create event…** continuation in the story-change editor.
5. Label commit boundaries: “Character created. Relationship not saved yet.”
   Canceling the relationship should not secretly delete an independently saved
   character or event. Failed creation must retain both pending forms.

Important existing contract: general relationship forms must still start empty.
Every successful addition must save, clear ALL fields, focus Source, and remain
open. Failed saves retain input. Keep Close explicit. A profile-context action
such as “Use Mira as Source” is an explicit click, not automatic preselection.
After saving, do not restore Mira or the last relationship type automatically.
Any future retained-source batch mode would be a separate product decision.

Acceptance: create and connect two new characters from relationship entry,
without a top-level tab change; then verify that a second entry is fully blank.

## Priority 2: guide genuinely multi-step tasks

### D. Build an event-centered “record what changed” flow

An event needs a readable detail area with participants and the relationship
changes already recorded there. Add **Add relationship change** next to them.

Suggested path:

1. **Choose connection** — show connections involving event participants first,
   with a searchable option to include any character. Do not exclude nonparticipants.
2. **Describe the change** — Begin, Change, or End. Show the state immediately
   before this event and the proposed state after it.
3. **Review and record** — for example, “At Chapter 5, Mira and Thorne stop being
   mutual Allies. From this event, Mira regards Thorne as an Enemy. Thorne's
   hostility is not implied.” Show effects until the next recorded change.

The selected event can be explicit context for this history operation; this is
separate from the blank, batch-add relationship form. Never silently overwrite
an existing state at the same event. Direct users to review/correct it instead.
For a new connection, use the existing semantics and duplicate validation.

Keep **Record story change** and **Correct a mistake** distinct. Use a short
explanation beside these choices, with additional history detail available on
demand. Do not require a wizard for a simple notes correction.

After recording, show **Change recorded at Chapter 5**, with **Add another change**,
**View graph at this event**, and **Done**. For multiple changes, show what is
already saved and what is still pending; cancel does not undo earlier commits.

Acceptance: record an alliance at chapter two and enmity at chapter five from
Events, inspect both graphs, and return to the event without searching again.

### E. Offer next steps at actual completion points

Replace general instructional paragraphs with concise, relevant completion states:

- New character saved: **Add relationship**, **Add more details**, **Done**.
- Relationship added: readable saved-connection confirmation; the next entry is
  blank, with **Close** and an optional **View saved connection** action.
- Event saved: **Add relationship change**, **View event**, **Done**.
- Character deleted: **Undo** and **Open Trash**.
- Draft recovered: **Review recovered changes** followed by explicit **Save character**.

These are optional next actions, not mandatory steps or automatic tab switches.
Avoid a full-screen checklist on every visit. Empty-story guidance can introduce
“Create characters → connect them → explore,” then disappear once it is useful
no longer. Feedback should be near the action rather than only in the global footer.

## Priority 3: reduce choices without hiding capabilities

### F. Separate writing tools from application maintenance

Retain the main story browsing views. Group New/Open/Recent/Import/Export under a
labeled Story menu. Group appearance, backups, Trash, and the technical Activity
log under clear settings/data menus, with direct contextual links where needed.
Keep story name, Search, and the current task's main action prominent.

Activity does not need equal visual weight with the fictional Events timeline.
Recovery drafts should have an actionable notification, not depend on users
remembering which maintenance tab contains them. Validate discoverability before
moving existing controls; keep keyboard access and familiar labels.

### G. Simplify small profile edits and ordinary graph browsing

- Quick character creation: name, optional role, then optional details.
- Profile: retain overview, offer section-specific Edit actions and collapsible
  Story/Abilities/Inventory/Notes sections. Preserve every saved field.
- Save keeps the current editing section and scroll position. Done explicitly
  returns to the overview; Save/Discard/Cancel handles unfinished changes.
- Graph: keep focus, scope, and Fit visible. Group less-used direction/type/isolate
  filters and layout/view management under labeled controls. Display active
  filters and the selected event so hidden options cannot silently hide characters.
- Disable selection-dependent actions and show a brief explanation when needed.
  Current event and relationship handlers sometimes simply return when nothing
  is selected; this gives the user no visible next step.

## Implementation order and boundaries

1. Add shared contextual action routing and return-navigation state. Reuse existing
   editors; do not introduce a new relationship implementation for each view.
2. Expose those actions on profiles, graph inspector, and search. Add focused
   navigation/unsaved-edit integration tests.
3. Add quick prerequisite creation and explicit contextual selector actions.
   Regression-test batch entry before release.
4. Add event detail and the guided story-change flow. Put orchestration outside
   widget callbacks, reusing the current history store and semantic validators.
5. Add actionable completion messages and recoverable Undo backed by Trash.
   Undo must report connection conflicts, not promise restoration it cannot do.
6. Evaluate menu/toolbar regrouping and profile section editing after measuring
   the first changes. Avoid changing every navigation convention in one release.

Suggested focused modules: `navigation.py` for locations/Back, `context_actions.py`
for shared launch commands, `quick_character.py` for minimal creation,
`event_detail.py` for event outcomes, and `story_change_flow.py` for staged change
entry. Start with small interfaces and avoid a general workflow framework.
Most of these changes need no schema migration or renderer replacement.

## Validation: measure completed goals

Observe 5–8 writers or GMs working independently with disposable stories. Give
goals, not instructions naming tabs. Compare the existing app and a prototype;
vary task order to reduce practice effects. These small sessions identify
usability issues, not statistically representative market preferences.

| Test goal | Proposed acceptance target |
|---|---|
| Connect Mira to a new NPC while reading her profile | No top-level tab changes; no lost input; new character remains clearly saved if connection is canceled. |
| Correct a selected graph edge's notes | No tab changes; selection and camera survive; correct individual edge changes. |
| Follow two profiles and return to the graph | Back returns to the original filters, selection, event, and zoom. |
| Record and view a chapter-five betrayal | Complete from event context without visiting the Relationships table; historical/current meaning is understood. |
| Find a relationship by a phrase in its notes and fix it | Editing available directly from the result; return preserves the query/results. |
| Recover an accidental deletion | Visible Undo restores what is valid; conflicts are explained with a useful next action. |
| Add ten independent relationships | Every successful save clears every field, focuses Source, stays open; failure retains input. |

Record unassisted completion, time, wrong turns, view switches, repeated data
entry, requests for help, and whether the user knows what was saved. Establish
a baseline before claiming improvement. A useful release target is at least
four of five participants completing each core task unaided, with fewer wrong
turns and no data-loss or historical-state misunderstandings. This is a proposed
gate, not a measured result. Also test keyboard-only navigation and laptop sizing.

## Research supporting the approach

These principles inform the recommendations; they do not demonstrate that the
specific Story Atlas changes have been validated with users.

- [NN/g: Task Analysis](https://www.nngroup.com/articles/task-analysis/): study
  the activities needed to reach a goal and observe actual work, not only reports
  of how users think they work.
- [NN/g: Recognition and Recall](https://www.nngroup.com/articles/recognition-and-recall/):
  make relevant choices and context available instead of requiring users to
  remember information across screens.
- [NN/g: Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/):
  surface common needs first and reveal optional complexity when it becomes relevant.
- [NN/g: Help and Documentation](https://www.nngroup.com/articles/help-and-documentation/):
  use task-oriented, contextual assistance. Help complements a coherent flow.
