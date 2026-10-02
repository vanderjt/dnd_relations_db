# Review of Terra's UX changes

Reviewed 23 September 2026 against UX_WORKFLOWS.md and the implementation task.
The workspace has no Git repository, so this review used the current source,
earlier source inspected in this task, and Terra's task history rather than a Git diff.
The original review did not change production code. Its pre-fix reproduction script:
`build-verification/review_checks.py`.

## Remediation

The seven findings below were subsequently fixed in source. Undo resets when a
story is installed; event graph navigation targets the application and closes
the chooser; profile focus uses widget references; Done reloads committed values
after Discard; navigation performs one leave check and preserves canceled Back
destinations; reopened sections remain beneath their headings; all event-change
save paths await review. Review cancellation restores the editor's modal focus.

Validation after remediation: **106 tests passed**, including seven new
interaction regression tests. The packaged Windows build was not rebuilt.

`tests/test_ux_regressions.py` exercises these interaction paths, including
overlapping IDs across stories, actual button/keyboard activation, cancellation,
and failed persistence. The original findings below are retained as review history;
they describe the pre-fix implementation, not outstanding defects.

## Findings

### 1. P1 — Undo can modify the wrong story

Location: `story_atlas/projects.py:90`, `characters.py:222`, `relationships.py:62`.

Story switching clears navigation history but does not clear either view's
`undo_target` or disable its Undo button. Those targets contain bare record IDs.
After switching, Undo executes against the new database with the old story's ID.

Reproduced: delete character #1 in A; open B where a different character #1 is
already in Trash; click Undo. The unrelated B character is restored.
The relationship Undo implementation has the same story-scoping defect.

Fix: invalidate Undo on database installation, or store the originating story
identity and enforce it before restoration. Test overlapping IDs across stories
for both characters and relationships.

### 2. P2 — View graph after recording an event change raises an exception

Location: `story_atlas/event_view.py:182`.

`EventRelationshipChangeDialog.show_graph()` calls `self.winfo_toplevel()`.
Because the caller is itself a Toplevel, this returns the chooser, not StoryAtlas.
Accessing `app.graph` raises AttributeError. The new completion action cannot
complete its advertised task. Existing tests check that the button is enabled,
but do not invoke it.

Fix: retain the application reference or resolve it through the originating
EventView. Close/release the modal chooser appropriately before graph interaction.
Verify an actual button invocation selects the right historical event and allows
graph interaction without a callback error.

### 3. P2 — Edit identity raises an exception

Location: `story_atlas/profile_editor.py:77`.

`focus_section('identity')` resolves `fields['name']`, which is a StringVar,
then calls `focus_set()` as if it were an Entry widget. Clicking Edit identity
switches tabs and raises AttributeError rather than focusing/revealing the field.

Fix: keep widget references separately from value variables and use those for
focus and scroll reveal. Invoke every section-edit button in a Tk test.

### 4. P2 — Done → Discard leaves discarded edits in the editor

Location: `story_atlas/characters.py:201`.

Done calls `can_leave()` and selects Overview. Choosing Discard only removes the
recovery draft; it does not restore the committed values in the editor. Unlike
older navigation callers, Done does not subsequently load another profile.

Reproduced: rename Mira without saving, click Done, choose Discard. The editor
still contains the new name and remains dirty. Returning to edit or saving later
can commit text the user explicitly discarded; later navigation prompts again.

Fix: on Done's discard branch, reload the committed profile (or blank new form)
and reset dirty state. Preserve existing Save and Cancel behavior. Test all three
choices and verify both database contents and editor contents.

### 5. P2 — Navigation asks twice about the same unsaved changes

Location: `story_atlas/navigation.py:49`, also `open_from_graph` and profile Back.

The controller calls `characters.can_leave()`, then `open_character()`, which
calls it again. When the first response is Discard, the fields remain dirty until
load, so the second check repeats the prompt. Back also ignores the return value
from the second `open_character()` check and can consume a destination despite
the user canceling there.

Reproduced: dirty profile → connected profile, answer Discard then Cancel.
Two prompts appear and navigation fails after the first answer authorized it.

Fix: give one layer ownership of the leave check. Only change the Back stack
after a successful transition. Test Discard and Save, not only first-prompt Cancel.

### 6. P2 — Reopening a profile section moves its contents below other sections

Location: `story_atlas/profile_editor.py:73`.

Collapsing uses `pack_forget()`; expanding calls `pack()` without a placement
anchor. Tk appends the section body after the other packed widgets. Reopening
Story places its fields at the bottom, away from its Story heading and beneath
unrelated sections. The values survive but the form grouping becomes misleading.

Fix: pack the body immediately after its heading, or keep heading and body in a
dedicated section container. Verify widget ordering after collapsing/reopening
each section in different orders.

### 7. P2 — Keyboard and close-save paths bypass the required change review

Location: `story_atlas/history_dialog.py:122`, `147`, `172`.

With `review=True`, the main button opens the before/after review, but Ctrl+Enter
still calls `save()` → `commit()`. Closing with unfinished edits and choosing Save
also calls `commit()` directly. These paths persist the change without the review
that the event-based workflow presents as its next step.

Reproduced: construct an event-context editor with review enabled, change Ally to
Enemy, call the same save handler bound to Ctrl+Enter. The history is committed
without a review dialog.

Fix: route all save intentions through the review when enabled; reserve the
commit operation for its confirmation action. Test keyboard and window-close
paths and assert history remains unchanged until confirmation.

## Validation and assessment

- Full existing suite: **99 tests passed** on the local Windows runtime.
- Seven additional failure scenarios reproduced with disposable databases and
  real Tk objects. Existing production stories were not used.
- The review did not rebuild or test the packaged executable, which was explicitly
  left unchanged during Terra's work.
- No manual visual assessment or observed writer usability sessions were performed.

The additions cover useful parts of the plan: contextual relationship actions,
Back navigation, quick prerequisite creation, event details, completion actions,
and simpler menus. They largely reuse existing storage semantics. However, the
passing suite does not establish that all new user paths work: several tests
invoke persistence methods directly or check button state without executing the
button. Fix the findings above and add interaction-path regression tests before
rebuilding the distribution.
