# Foundation pilot visual review

28 September 2026, source 0.18.0. Disposable fictional story and settings only. Real Tk client captures, current desktop scaling only; no per-monitor DPI or clean-machine verification.

Local evidence folders:

- `build-verification/gui-overhaul/pilot-illustrated-20260928-204049`
- `build-verification/gui-overhaul/pilot-minimal-20260928-204115`

Each run completed 16 cases with zero recorded callback errors: both themes/modes at default and minimum-size baseline configurations, plus default-size imported synthetic portrait overview/editor cases. Report metadata records the requested and effective illustration setting. Captures are supplementary visual evidence, not functional preservation tests.

## Inspection findings

- Inspected Simple dark and Advanced light overview captures show the imported portrait in both Illustrated and Minimal. Minimal removes decorative section art while retaining the user-content portrait and section text.
- Illustrated section artwork reads crisply beside text at default size. Its authored colors remain distinct from the palette. The small goals emblem is visually subdued on dark; its explicit label keeps its meaning clear.
- Default-size Advanced editor fields and bottom Save/Done actions remain legible. Minimal Simple editor also retains readable sections and stable Save/Close actions. Portraits in editor forms are below the initial viewport or in collapsed optional details; these captures do not alone establish editor portrait visibility or unsaved-value preservation. Independent functional review must establish those contracts.
- The initial Illustrated Advanced metadata block used the amber context treatment, competing with chronology context. The reviewer independently flagged this and the foundation agent changed the metadata to neutral. The subsequent Minimal images show neutral metadata. Source edits occurred between these runs, so they are not a perfectly identical-source A/B comparison; the start fingerprints are in each report.
- The minimum-window/maximum-text problems described in `00-baseline.md` remain unresolved at this foundation milestone. They are preexisting navigation/layout issues and remain release blockers against the roadmap's minimum-size acceptance criterion.

## Capture reliability and exclusions

The first pilot attempts (`pilot-illustrated-20260928-203823` and `pilot-minimal-20260928-203959`) captured an occluding Codex window and are **invalid visual evidence**. The tool now sets its disposable window topmost before capturing. A Windows task-switcher still occluded `simple-dark-1180x720-10pt-editor-portrait.png` in the valid Illustrated rerun; exclude that individual image. The corresponding inspected Minimal editor image is unobscured. Desktop screenshots always require manual inspection; a zero exit status does not establish that an image is unobscured.

The GUI slot was released to the independent reviewer for regression and preservation tests. Further release captures should include actual bundled Greyhaven content, relationships, chronology, graph, Welcome, and functional error/empty/historical states. Minimum-size layout must be reinspected after the navigation and core-screen phases.
