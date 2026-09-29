# Stage 03 — independent review

Reviewed the core workspace implementation separately from the foundation agent. The reviewer also implemented the minimum-size Characters correction; both the foundation agent and primary independently reviewed that patch. This is agent review evidence, not a separate human approval.

## Resolved findings and independent checks

- Portrait-row cache misses originally persisted indefinitely. Misses now remain uncached so importing/restoring the same immutable reference can recover immediately. Independent tests cover a real portrait surviving Minimal mode with values/selection unchanged and an absent same-named reference in another story not borrowing cached artwork.
- Missing-portrait feedback now wraps as the identity header resizes. Identity portraits remain user content in both appearance preferences.
- Compact Characters originally spent its initial reading area on context and generic saved-state messaging. The reviewer shortened compact context to Current saved profile, retained the full non-historical explanation in prose, hid generic status for saved records, retained real dirty/error notices and reduced roster chrome. A regression verifies the selected name and a cast row are visible at 760×480/16pt, editing remains uncommitted until Save, the notice clears after Save and full context returns in a larger window. Profile/UX/independent tests passed 21 tests in 10.766s.
- Compact relationship routes preserve selected IDs and original edit/history/consolidation/delete callbacks. A read-only selected-connection dialog keeps full directional text accessible when the expanded inline details are hidden.
- Compact graph legends remain available through native menus. Export temporarily enlarges the figure so its scope and legend render, then restores figure size/layout in finally; the focused regression also verifies unchanged graph state. Reviewed the implementation and test independently.
- Treeview identity columns preserve existing data-value indices and stable row IDs. Image updates occur in place; per-widget image references protect visible rows from cache eviction.

## Validation tooling

Reviewed the primary's disposable repeated benchmark and QA's expanded capture helper. Requested and checked callback-error failure reporting, timing real mode switches, safe cleanup, historical graph/timeline consistency, planned-node verification and source-fingerprint drift rejection. The benchmark identifies same-process first Tk paint separately from cold startup and does not claim memory or physical-DPI coverage.

## Current gate

The first full Stage 03 suite was deliberately interrupted after the actual Greyhaven planned-graph minimum-size capture exposed a remaining graph-body regression; it is **not a passing run**. Log: `build-verification/gui-stage3-review-tests.log`. Source fingerprint for that run/capture: `c6e88f50b120fb0bbbcc557295850b0a08b5608e9980c00d97503ba1aa7c7168`.

The populated Greyhaven failure was traced to Configure occurring before Map: the compact transition skipped refresh while hidden, then the clean graph reused its verbose scope summary. Foundation now refreshes presentation on the transition regardless of map state. The exact populated first-map sequence has a regression, including planned selection and native navigation submenu reachability.

Further visual review led to a physical-area label budget, full selected/pinned/ordered cues, short wrapped labels on narrow canvases and separate sparse-label alignment so the two-character fixture does not overlap. Independent source review checked the density behavior and the real rendered bounding-box regression. Compact navigation moved to the existing Filters menu; corresponding geometry checks now inspect the visible scope controls and additionally assert the navigation submenu exists. Checked Zoom/Pan menu states retain active-tool feedback. Export tests explicitly verify full long names in the enlarged figure and restoration of compact labels and graph state afterward.

Final frozen fingerprint: `447711b9629de7fac5577b2e1e2724f985c9744bd346948d06c61524865d73f0`. Independently inspected the Greyhaven Advanced dark planned-graph 760×480/16pt image from `build-verification/gui-overhaul/workspaces-final-verified-20260929-071103`: its compact scope, visible graph, selected planned label and full-identity inspector resolve the previous blocking state. The visual-QA agent is independently reviewing the complete ten-image minimum matrix.

The complete frozen-source run executed **248 tests in 156.458s and failed with five errors** (`build-verification/gui-stage3-review-final-tests.log`). Every error was the same new density-layout assumption: provisional node `-1` can remain in the rendered graph after its saved layout position is removed during task cancellation, so `highlight()` raised `KeyError` while positioning its label. Existing cancellation, mode-switch and undo tests caught this.

Foundation corrected the renderer to use the annotation's existing `xy` anchor, which remains valid until the queued redraw removes the artist. Both primary and this reviewer independently checked that normal node dragging updates the same anchor and that no saved model mutation was added. The removed-position regression and affected Simple/undo suites passed **47 tests in 39.154s**. Corrected source fingerprint: `9493bcc22a7223292a1273f159a225bb13fa1e4d233b9252538e3d40e2f4a256`.

Final complete execution of `.build-env/Scripts/python.exe -m unittest discover -s tests -q`: **248 tests passed in 158.598 seconds**, no skips or failures, exit 0. Log: `build-verification/gui-stage3-review-complete-tests.log`. Existing dependency deprecation warnings remain. Single-run graph timings were initial 0.769s, note refresh 0.042s, direct focus 0.046s and Simple 0.303s; repeated performance comparison is tracked separately.

Visual QA independently approved all ten final core minimum captures. The annotation-anchor correction preserves their steady-state rendering. **Recommendation: approve Stage 03 integration after committing the reviewed fixes and evidence.** No unresolved Stage 03 correctness or blocking visual finding remains. Supporting screens, repeated performance comparison, packaged execution and physical per-monitor DPI remain later release gates; none is inferred from this stage approval.
