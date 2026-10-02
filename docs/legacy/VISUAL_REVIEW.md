# Visual-language implementation review

23 September 2026. Reviewed the source implementation and exercised real Tk
widgets with disposable stories. No packaged application rebuild.

## Corrected issues

- Read-only Text widgets inherited Tab's text-insertion behavior, trapping
  keyboard navigation. Tab/Shift+Tab now move focus, Ctrl+A selects all, and
  normal copying still works. Content remains non-editable.
- The shared detail helper assumed its immediate top-level window owned the
  palette, preventing reuse inside child dialogs. It now uses the root theme.
- Unchanged detail refreshes discarded text selection and scroll position.
  They now leave the widget untouched.
- Moving History into selected-record actions concealed ended connections
  when they had no current row. All relationship history is accessible without
  selecting a current relationship.
- The graph inspector always described a focused node's scope as Direct,
  even in Two steps or Full graph. It now reports the selected scope.
- Event details omitted participant IDs, making duplicate names ambiguous.
  IDs now appear in both the chronology preview and full participant list.
- One-line relationship/event detail panes made multi-line descriptions hard
  to read. Relationships now show three lines; events use up to three while
  retaining at least 100 pixels for chronology where window space permits.

## Validation

Final full-suite result: **118 tests passed in 36.255 seconds**. Output is in
`build-verification/visual-review-tests.log`. The 100-character/300-relationship
benchmark measured 1.406 seconds initial display, 0.019 seconds notes refresh,
and 0.037 seconds direct-focus refresh.

Four new regression tests cover keyboard traversal/copy/edit prevention,
unchanged refresh preservation, child-dialog theme inheritance, ended-connection
history access, actual graph scope descriptions, and duplicate-name participants.
Existing narrative expectations now include participant IDs.

The existing appearance checks cover 900×600 and 1280×720 windows, large text,
both themes, and simulated 100/125/150% Tk scaling. The complete suite also
checks relationship save/clear/refocus/stay-open behavior and failure retention,
history, recovery, search, graph interaction, and sample-story isolation.

Manual screenshot review, physical Windows DPI changes, per-monitor transitions,
and usability testing with writers were not performed. Automated geometry and
interaction checks do not establish visual accessibility conformance. Run the
source with `python main.py`; the launcher may prefer an older packaged build.
