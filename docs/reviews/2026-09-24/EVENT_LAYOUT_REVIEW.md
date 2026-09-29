# Review and corrections: Sol's latest event layout

24 September 2026. This follow-up covers the later work in “Plan chapters and
events UI,” not only the original Sol implementation. The requested three-pane
layout, implicit chronology, participant bullets, collapsible goal/change groups,
and removal of visible character ID suffixes are preserved.

## Issues addressed

| Issue | Correction | Validation |
|---|---|---|
| Every refresh recreated outline items open, undoing the user's collapses and selection even after an unrelated save. | Stable internal item IDs preserve expansion, selection, focus, and scroll for the same event/story. IDs remain invisible. A different event/story starts with fresh outline state. | Collapse both outlines, save unrelated profile data, and verify the collapsed groups and selections remain. |
| Relationship changes displayed type/presence but omitted their saved narrative notes. | Notes appear as children of each change. Multiline notes retain their text. Goal lines no longer lose internal indentation during display. | Check multiline change notes and indented goals against the saved content. |
| The responsive action menu considered pane height only. Dragging the right pane narrow could leave buttons clipped. | The compact menu also activates when the pane cannot fit the widest action. | Drag the pane narrow and wide at large text sizes; verify the menu/buttons switch appropriately. |
| History opened from the event change chooser did not restore its parent's modal grab on close, and did not select the event's effective state. | Open History with the originating event context; on close restore the chooser's grab, action state, and focus. | Open the actual chooser/history flow, verify state selection and grab restoration. |
| Mouse-wheel input over a nested outline also reached the outer ScrollFrame handler. | Treeviews retain their own wheel handling, as text areas already did. Background scrolling continues to move the outer detail area. | Verify the outer scroll callback does not run for a nested tree. |
| Quick-entry dialogs could be destroyed with an initial or return-focus callback still queued, producing a Tcl error. | Cancel pending focus callbacks when quick character/event entry or its relationship parent is destroyed. | Destroy quick entry before idle processing and verify its scheduled callback is gone. |

The outline state helper is in `story_atlas/event_detail_state.py`; narrative
storage and relationship semantics were not changed. No migration was needed.
The remaining event page is still large; further extraction can be done separately
without coupling it to this corrective pass.

## Validation

Baseline: **141 tests passed in 44.444 seconds** before these corrections.
Six new interaction tests in `tests/test_event_layout_review.py` pass.
The existing scaling test now checks the compact action menu when active, including
all three commands, instead of requiring intentionally hidden individual buttons.
Final source validation: **147 tests passed in 46.998 seconds**, including the six
new interaction regressions. The full suite includes relationship batch entry,
history, story switching, migration, recovery, and import/export checks. No queued
focus Tcl error appeared in the final run. The disposable 100-character /
300-relationship benchmark measured 1.398 s initial draw, 0.019 s notes refresh,
and 0.034 s direct-focus refresh. Log: `build-verification/event-layout-fixes-build.log`.

Windows packaging completed with `build_windows.ps1 -Python C:\ProgramData\anaconda3\python.exe`.
`tools/smoke_windows.ps1` passed against the rebuilt executable with Python/Conda
environment variables cleared and a minimal Windows PATH. It verified bundled
Tcl/Tk 8.6.15, TkAgg rendering, fonts, icon, portraits, sample isolation, reopening,
batch relationship reset, historical export, migrations, backup/restore with
assets, and writable external data. This is local packaged verification, not a
clean-machine test. Log: `build-verification/event-layout-fixes-smoke.log`.

- Version: 0.9.0; schema: 8.
- Source fingerprint: `4ebdfd339cc5158045690f4e213679f625cc60c9f2d8de0ddc0f9227c739fddd`.
- `dist/StoryAtlas/StoryAtlas.exe` SHA-256: `5B605911B18C01499C11B9E5374071AEB9D7BF65AD942DDCE6AE4BDD25CE82CE`.
- `dist/StoryAtlas-Windows-x64.zip` SHA-256: `AF3FC148EA923647CDD11CDAACE7024A250934F5D2BEA12ADF02CD449DB4BC57`.

Distribute the ZIP or the entire `dist/StoryAtlas` folder; the executable depends
on the adjacent bundled resources.

No existing user database or preferences were used for verification. Automated
widget checks do not establish manual visual accessibility or physical Windows
DPI behavior. Clean-machine testing and observed writer tasks remain outstanding.
