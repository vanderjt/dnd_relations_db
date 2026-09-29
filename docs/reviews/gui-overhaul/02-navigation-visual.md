# Navigation visual review — 29 September 2026

Final-source confirmation: independently reinspected Simple dark default and Advanced light minimum/16pt from `build-verification/gui-overhaul/navigation-final-20260929-060721`, fingerprint `71447fa842b1540e0dd094f7a25db033b80004078ab67ae78c60e535a5199310`. The final `lift()` correction retains visibly restored first controls and story title. Stage2 rendering approval stands. The coordinating agent reports 237 full-suite tests passing in 136.815 seconds and independent source-review approval. Minimum-size content limitations below remain stage3 work.

**Stage2 navigation visual gate: passed after correction.** The first-child occlusion described below was fixed and independently reinspected in all eight images in `build-verification/gui-overhaul/navigation-fixed-20260929-060001`, source fingerprint `95b8cd769cdf2484d3f304ccba850394f0781cfaa85fd2aab0053b031d873669`. Story title, New character, Edit character, previous timeline arrow and Advanced Edit profile are now visibly rendered. Both themes and both window/text configurations were inspected without OS overlay occlusion. This approves the navigation rendering correction, not the final minimum-size content-layout gate.

**Initial visual gate was blocked.** Independent inspection of all eight images in `build-verification/gui-overhaul/navigation-20260929-055519` found an ActionBar rendering regression invisible to the geometry-only checks. Source fingerprint: `6f7e2b62c922c55a044757fce045fcf212ce6e2583d35c32fddf1b8c661a675d`.

## Resolved blocking finding

The first item in multiple ActionBars is visually absent, leaving blank space while later items render. This occurs in both themes and at default and minimum sizes:

- Main header: story title is missing.
- Simple toolbar: New character is missing.
- Character summary actions: Edit character is missing.
- Simple timeline: previous-event arrow is missing.
- Advanced profile actions: Edit profile is missing.

The corresponding baseline captures show these actions. The initial pattern was consistent with row-container stacking obscuring early children. The implementation owner corrected the stacking, and the unobscured recapture confirmed every listed control before visual approval. Zero callback errors and empty outside-client candidates alone do not prove that a control is visible or receives pointer input.

## Other observations

The rendered menus use the proposed Story, Search, Help and Settings organization; View and More appear in the Simple toolbar. Advanced labeled tab emblems are crisp. Dark borders are subdued and distinct from text. At 760×480/16pt the Back button fits on the second header row, improving the specific preexisting right-edge clipping. The story title was missing in the initial capture and is visible in the corrected capture.

Minimum-size content remains severely crowded: Simple graph legend overlaps scope text, inspector summary has no useful vertical space, and Advanced roster/profile content is pushed below the viewport. These baseline content problems remain assigned to the core layout phase; the final release minimum-size gate remains unmet.

All eight screenshots appear to depict the application without external-window or OS-overlay occlusion. The fixture contains two synthetic characters, one connection and one event, with a short story filename (`review`). This matrix does not establish long-title rendering, menu keyboard behavior, physical Windows scaling, or package behavior.

The primary and implementation/review agents were notified immediately. No application source was changed by the visual reviewer.

## Remaining stage3 work

Corrected minimum-size captures still show no useful overview height, a crowded/clipped Simple inspector action area, and graph legend/title overlap. Advanced headers now fit, including Back and short story title, but guidance and nested navigation leave almost no roster/profile reading area. These issues remain visible and must be corrected before final release approval. The default-size core screens are readable; removing unset metadata and compacting the identity layout should recover useful reading space.
