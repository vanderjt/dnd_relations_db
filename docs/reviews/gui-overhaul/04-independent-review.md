# Stage 04 independent review

Reviewed by the foundation/workspace implementation agent, independently of the stage 04 owner, on 2026-09-29.

## Result

Approved supporting source changes and final visual results. No blocking correctness issue remains. The empty-graph clipping observation was corrected and independently verified in final captures. Packaged verification remains a separate release gate.

## Source review

Reviewed onboarding, story setup, Appearance, artwork credits, Recovery, theme, diagnostics, version, capture and benchmark helpers, the new support tests, and current usage documentation. Existing data operations retain their callbacks and confirmation flows. Schema remains unchanged. Recovery selection controls now accurately disable without a selection; primary actions remain outside scrolling content. Appearance applies preferences without rebuilding dirty editors and retains managed portraits in Minimal mode.

Credits include both packaged license texts in a selectable read-only viewer. Diagnostic checks validate all 30 packaged asset hashes, confined image paths, license availability, aliases, Tk images, preference persistence, and retained portraits. Recorded Tk callback failures now fail smoke verification rather than silently passing.

Requested review corrections were applied: support captures actually apply requested simulated Tk scaling and identify it separately from physical display testing; accent-button internal focus uses the contrasting on-accent color; contrast coverage includes dangerous-action hover/selection and success states; active menu routes and first-launch sample names in documentation match the application. The numeric audit covers 66 enabled color pairs, with exclusions explained rather than represented as complete accessibility certification.

Benchmark memory counters measure whole-process Windows working set and private bytes. They are explicitly not artwork allocation attribution; warm-cache counts and bounds are separate measurements. Source launch no longer preferentially starts the obsolete hard-coded 0.17.0 release.

## Independent visual review

Inspected all 36 original support captures through nine four-image contact sheets, then inspected native-resolution minimum setup, credits, and Recovery drafts images. Evidence directory:

`build-verification/gui-overhaul/release-support-review-20260929-073701`

The report identifies source fingerprint `de31b721afa7a8eab99c4b8e14de113c8ea482af4a1a47bf81f92be744542d8f` consistently before and after every capture, with zero callback errors and zero outside-client control candidates. These are owned-window captures, avoiding desktop occlusion. The automated geometry check explicitly does not detect text clipping, so visual inspection remains necessary.

Both dark and light themes were inspected for Welcome, expanded story setup, Appearance, credits, all three Recovery tabs, and empty Simple/Advanced workspaces, at default and minimum sizes/text settings. Dialog primary and closing actions remain painted and readable. Narrow dialog bodies scroll while their action footers remain available. Recovery minimum tables retain readable selected rows, scrollbars, and their actions. Default empty workspaces have clear creation routes.

Initial minor observation: empty Simple at 760×480/16pt clipped the second graph instruction line horizontally. The owner shortened its two lines to retain the focus/filter guidance. Independently reviewed the text-only patch and the new Agg 300×180/16pt regression, which checks all four rendered text bounds against the actual axes. Empty Advanced at that size initially shows editor guidance rather than the name field, but the field remains in the visible scrollable editor and primary actions remain available. Neither issue affects saved data.

Final verification: independently inspected all 36 support images again in `build-verification/gui-overhaul/release-final-20260929-074212`, including native-resolution minimum empty Simple. Its corrected instruction fits fully in both themes. Dialog actions, tables, scrolling content, and typography show no new regression. The completed 76-case report contains 36 supporting cases, zero support callback errors, zero support outside-client candidates, and consistent final fingerprint `98bb3cce5bcbfee253c0ebcc7ea91b2a68e345a64057115cebdbb0376f138573`. The other 40 core images are independently reviewed by the visual QA agent.

## Validation boundaries

The owner reported 18 focused tests passing (6 support, 4 Recovery, 8 distribution), followed by 7 support tests passing in 2.427 seconds after the empty-text regression was added. Primary reported the preceding full 254-test suite passed. This reviewer inspected test intent and source without running GUI concurrently with capture/full-suite owners. Final suite and packaged results should be read from the release verification report. Current-desktop screenshots and simulated Tk scaling do not establish physical Windows DPI or per-monitor transition coverage.

## Independent performance assessment

Reviewed `performance-comparison.json`, `content-main.txt`, and `content-overhaul.txt` in `build-verification/gui-overhaul`. The corrected comparison requires the same 100-node/300-edge graph to be ready. The earlier initial-window measurement was not comparable because the baseline still displayed an empty graph.

Comparable median first-content paint increased from 650 to 994 ms without portraits and 658 to 1,072 ms with portraits (53% and 63%; absolute increases 344 and 414 ms). Theme round trips increased from 688 to 850 ms and 709 to 820 ms. Mode round trips changed by −4.1%/+5.1%, and graph refresh by −5.8%/+4.6%. These results must not be described as uniformly unchanged performance.

Both content profiles show three renderer builds (two empty constructors and one populated graph) and 300 patch additions. Raster path drawing increased from 612 to 2,416 calls, with cumulative path-drawing time increasing from 0.153 to 0.609 seconds. This supports repeated initial geometry-settle painting as the dominant measured cause, rather than repeated graph construction or uncached artwork loading. Profiling overhead means those profile times are explanatory, not a replacement for the repeated unprofiled medians.

Recommendation: release with the explicit startup/theme limitation recorded. The roadmap's provisional 10% threshold requires investigation; it is not an absolute rejection threshold. The investigation establishes a roughly one-second populated startup on this test machine, while steady graph operations remain close to baseline. A future isolated optimization should measure/debounce initial rasterization with dedicated startup, hidden-tab, resize, provisional-editor and shutdown tests. A late event-scheduling change would risk the validated minimum-layout and lifecycle behavior without evidence of a data or functional defect.
