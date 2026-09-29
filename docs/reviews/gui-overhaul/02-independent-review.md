# Stage 02 — independent navigation review

Reviewed `bc42f0d` against integrated `gui_overhaul` (`aacf783`) as an agent separate from the implementation agent. This is independent agent evidence, not a separate human GitHub approval.

## Findings and corrections

- Active README/distribution guidance initially retained Maintenance and the old standalone Help button. Implementation updated those routes to Settings and Help → Help and shortcuts. The implementation report records the menu migration.
- Initial title elision used a fixed 16-character cutoff even in wide windows. It now measures the named heading font against a bounded responsive width; the full name remains in the native window title.
- Independent review flagged that explicit row placement can suppress size propagation after a font or decoration change at fixed window width. ActionBar now participates in appearance refresh and coalesces child Configure events into an idle reflow, canceling pending work on destruction. A focused regression covers fixed-width 10→16-point changes and Minimal tab-art removal.

The final shared-row implementation keeps controls grid-managed while placing independently measured row frames. Reviewed every dynamic item-list callsite: header mode filtering, Simple ribbon/timeline compact layouts and batch step navigation explicitly forget controls before replacing subsets. Selection-chip destruction removes both widgets and row frames, with stale entries pruned before reuse. The reviewer later made the minimal keyboard-order correction described below; both the foundation agent and primary independently reviewed it.

## Command and state audit

Compared previous callbacks with the new native menus. New/Open/Recent, both samples, export, saved-change Undo/Redo, search, help, About, appearance, recovery and activity remain reachable. Search retains Ctrl+K and Help retains F1; text-entry undo handling is unchanged. The compatibility alias `maintenance_menu` remains for callers.

Simple View now owns Fit, planned-cast visibility, filters, the existing legend menu, pane visibility, zoom and pan. More retains chapter/event operations, saved views/export and the separately scoped recent-creation undo. The existing legend object and filter callbacks are retained. Source/target selection and unsaved guards are unchanged. Characters and Chapters & events tabs retain full text with optional art; image references are retained and Minimal removes only decoration.

## Execution and visual evidence

**A blocking rendering defect was independently confirmed in the first navigation capture and corrected.** The first control of ActionBars (including the story title and Edit profile) was obscured by a row frame created later in Tk stacking order, despite passing viewability/bounds checks. Visual QA, primary and this reviewer confirmed the defect. The implementation agent added an explicit `widget.lift(frame)` and a center hit-test regression using `winfo_containing`.

The pre-fix suite passed **237 tests in 130.104s**, demonstrating why geometry assertions alone were insufficient. Its log is `build-verification/gui-stage2-review-tests.log` and is not final fix validation.

Independently inspected corrected captures in `build-verification/gui-overhaul/navigation-fixed-20260929-060001`: Advanced dark default now paints the story title and primary Edit profile; Simple dark 760×480/16pt paints New character, View/More and timeline arrows. The Simple minimum-size graph scope/legend still overlaps and task content remains starved: this remains a core-workspace/final-release gate, not a passing visual state. The separate visual-QA agent reviews the wider matrix.

The first stacking correction, `widget.lift(frame)`, restored painting but reversed sibling traversal order. The full rerun caught a deterministic relationship-dialog Tab regression (Save went to Source rather than Close): **236 passed / 1 failed in 135.248s**, retained in `build-verification/gui-stage2-review-final-tests.log`. A focused repeat reproduced it. At the primary's request, this reviewer changed the call to `widget.lift()` in item order, preserving visibility and native traversal. The foundation agent and primary independently checked that correction.

Extended the ActionBar test with forward and reverse `tk_focusNext`/`tk_focusPrev` checks over multiple rows and 520→760→520 resizes, alongside the actual center hit-test. Relationship-dialog and navigation suites passed **14 tests in 4.377s** after the correction.

Final complete execution of `.build-env/Scripts/python.exe -m unittest discover -s tests -q`: **237 tests passed in 136.815 seconds**, no skips or failures, exit 0. Log: `build-verification/gui-stage2-review-complete-tests.log`. Only existing dependency deprecation warnings were emitted. The benchmark reported initial 0.760s, note refresh 0.036s, direct focus 0.047s and Simple 0.292s; this single run is not a controlled performance comparison.

**Recommendation: approve Stage 02 integration after committing the reviewed fixes and evidence.** Both rendering and traversal findings are resolved with meaningful regression coverage; no unresolved navigation finding remains. The primary may recapture once more on final `lift()` source before merging. Minimum-window graph/body crowding and physical-DPI/package checks remain subsequent release gates.
