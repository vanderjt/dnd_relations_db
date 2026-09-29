# Core workspaces visual review

## Final stage3 visual decision: pass

Independently inspected all ten images in `build-verification/gui-overhaul/workspaces-final-verified-20260929-071103`, source fingerprint `447711b9629de7fac5577b2e1e2724f985c9744bd346948d06c61524865d73f0`. All are valid, unobscured direct-window captures. Simple node labels are separated again in both themes, while the long full identity remains readable in its inspector. Advanced Graph retains the readable selected planned-node label, visible network and matching inspector. Characters, Relationships and Events retain their corrected minimum-size access. No unresolved blocking visual regression remains in this reviewed core matrix.

This passes the **stage3 core-workspace visual gate**, with cramped minimum-size lists intentionally relying on scrolling and menus. It does not establish the remaining supporting-screen, contrast, packaged-build, physical DPI or representative-user gates. The implementation agent reports 23 focused tests passing in 20.695 seconds; independent full-suite execution is coordinated separately. Prior defects and intermediate results below are retained as review history, not current blockers.

## Fourth review: selected planned-node candidate

All ten images in `build-verification/gui-overhaul/workspaces-approved-candidate-20260929-070706` were inspected (fingerprint `f0ac634528af861b65174b1555a5b3b20ed059b2014b0e154eebc2d58393f1b4`). Advanced Graph now displays the full compact network, a readable selected planned-node label and the corresponding inspector identity in both themes. Characters, Relationships and Events retain the improvements below.

One regression prevents approval of the entire matrix: the Simple two-node minimum-size graph labels now overlap in both themes. Bryn's label moved inward toward Alden's, while Alden's wrapped label moved inward from the right. This collision was absent in the preceding `065029` captures. The primary and implementation agent have been notified. All ten images are valid direct-window captures.

## Third review: focused minimum-size corrections

All ten direct-window captures in `build-verification/gui-overhaul/workspaces-minimum-fixed-20260929-065029` were independently inspected. Characters retains readable identity and actions. Simple long names are now bounded and separated from adjacent node labels; the full name remains available in the inspector. Relationships now shows All relationships fully and a partial following row with a scrollbar, plus readable connection rows and More actions; the prior complete loss of the cast-list body is resolved. Events remains usable with scrolling and Expand details.

The remaining visual blocker is Advanced Graph label density: although the compressed one-line scope restores approximately 114 pixels of canvas, all 19 node labels overlap heavily and lower labels are cropped. A density-aware rendering correction is in progress. Its recapture should include a selected node to establish useful selected labeling and inspector content, alongside the initial no-selection view. No other new blocker was found in these ten images.

## Second review: direct-window captures

All 40 images in `build-verification/gui-overhaul/workspaces-final-20260929-063530` were independently inspected, with native-size checks of the remaining minimum-size defects. Source fingerprint: `c6e88f50b120fb0bbbcc557295850b0a08b5608e9980c00d97503ba1aa7c7168`. All depict Story Atlas without the previous OS overlays; Windows direct-window capture is producing useful evidence.

**Gate remains blocked:**

- Advanced Graph at 760×480/16pt still has only approximately 60 pixels of canvas below a three-line planned/historical scope banner. Nodes and labels are cropped and inspector content is effectively unavailable. Merely restoring a thin strip of canvas does not resolve the usability defect.
- Advanced Relationships at 760×480/16pt restores two readable connection rows, and source inspection confirms More now includes selected connection commands. However, the cast roster shows its heading and only clipped row pixels below the Filter cast label/entry. Cast records cannot be read normally. Its filter/header region needs further compression or an alternate cast chooser.
- Simple minimum-size graph labels collide: the long Alden name runs into Bryn's label and underneath the inspector boundary. The inspector name itself wraps and its Edit/Actions controls are visible. Graph labeling needs wrapping, abbreviation, or an equivalent readable treatment.

Advanced Characters minimum-size now displays the selected identity and character type in a scrolling overview, with New character and Edit profile accessible; its earlier banner-only defect is resolved. Default/900px overview, fallback, validation, chronology, relationships and portrait/editor states retain the improvements described below. Events minimum-size remains cramped but operable.

The primary was notified of these remaining defects. Earlier invalid-capture exclusions below apply only to the previous `workspaces-review` folder, not this direct-window rerun.

## Initial review history

**Release visual gate remains blocked pending minimum-size fixes and new captures.** Independent offline inspection covered all 40 images in `build-verification/gui-overhaul/workspaces-review-20260929-062511`, using ten four-image contact sheets. No application source was changed by this reviewer. The primary independently confirmed the principal minimum-size findings.

Recorded source fingerprint: `e9353efcbb9aa9dddffd82152181abeca443af7f64c9fdf166c2c20e1bc6b004` (Story Atlas 0.18.0).

## Valid-image findings

- Default-size Advanced profile identity is more compact: portrait sits beside identity text, empty metadata no longer fills the header, and Summary/Goals receive consistent emblems. Imported portraits remain visible in inspected Advanced overview captures.
- At 900×600/10pt, Greyhaven overview, missing-portrait fallback, directional relationship ledger, chronology, historical graph, planned graph, filtered-empty graph and validation states are readable. Missing portraits leave a clear message and accessible profile content. Blank-name validation displays an adjacent correction. Historical Simple timeline and graph show the same event context.
- At 760×480/16pt, **Advanced Characters is blocked**: the overview's initial visible region contains only its chronology banner; selected identity and prose lie below it. The roster offers about one visible row. Removing metadata alone has not recovered enough reading space.
- At 760×480/16pt, **Advanced Relationships is blocked**: cast/list controls and selected action controls disappear below the available body. The initial visible body contains the cast filter and selected-connection description but not a usable connection list/action region. Both themes show this failure.
- At 760×480/16pt, **Advanced Graph is blocked**: navigation and scope text consume the body, leaving no visible graph. Both themes show the failure.
- At 760×480/16pt, **Advanced Events remains cramped but operable**: roughly three event rows and a narrow scrolling description are visible; Expand details provides a route to more reading space. Final captures should verify that action route and selected chronology remain coherent.
- Dense Greyhaven graph labels still overlap in 900×600 captures; graph selection/label-density behavior needs continued review. This is separate from the complete loss of graph canvas at minimum size.

## Invalid captures: exclude from visual evidence

These six images show Windows task switching/other applications rather than an unobscured Story Atlas window:

1. `simple-dark-760x480-16pt.png`
2. `simple-dark-1180x720-10pt-editor-portrait.png`
3. `simple-dark-1180x720-10pt-overview-portrait.png`
4. `simple-light-1180x720-10pt.png`
5. `simple-light-760x480-16pt.png`
6. `simple-light-1180x720-10pt-overview-portrait.png`

The other 34 images show the application. Exclusion is based on inspecting the images, regardless of process exit or callback status. This run cannot establish Simple minimum-size or Simple portrait-overview acceptance.

## Corrective work and next gate

The independent reviewer is correcting minimum-size Characters layout; the foundation implementation agent is correcting Graph and Relationships. The capture helper now uses the installed Pillow `ImageGrab.grab(window=app.winfo_id())` API on Windows, with desktop bounding-box capture only on other platforms. It records capture method and resulting pixel dimensions. Primary will verify the new capture method on a short matrix before capturing final evidence from frozen source.

Per-case source fingerprints, selected IDs, graph/timeline state and explicit filtered-empty/planned assertions remain in the capture report. A source fingerprint change causes a nonzero result. Physical Windows scaling combinations, mixed-monitor movement, representative-user studies and clean-machine package behavior are not established by this source review.
