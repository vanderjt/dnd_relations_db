# Combined legend and worked examples

Story Atlas 0.14.0 — schema 12, portable format 8. 24 September 2026.

## Delivered

- A shared plotted key includes all five character dot colors and all four link
  categories. It occupies reserved space above the graph rather than covering
  nodes. Simple's **Legend · dots & links** adds category explanations, arrow
  direction, planned/unsaved dots, and the ended-link style. Dot entries retain
  their filtering actions.
- Greyhaven now explicitly uses all five types, populated goals, and Support,
  Conflict, Personal and Other link categories. It retains 18 characters,
  3 chapters, 10 events and 50 recorded connections, with four guided scene views.
- **the modern prometheus** is a second example available from Story and Welcome.
  It contains 17 characters, 6 editorial chapters, 20 events, 33 connections,
  and six guided scene views plus an overview. It models Shelley's
  [1831 Frankenstein](https://www.gutenberg.org/files/42324/42324-h/42324-h.htm),
  using original paraphrases and explicit interpretation notes.
- Examples create separate files through the normal publish/database services.
  Their stored Example overview supplies opening layout, positions, label
  visibility and link categories. Scene views use separate round layouts to
  avoid clustering a small focus group into its original whole-cast arc.
- Ready-made story files, exports, graph previews, a local launcher, and a
  walkthrough are in `examples/`. `examples/StoryAtlas-Examples.zip` includes
  both databases, the guide and previews. It contains no temporary test records.

## Verification

- Focused example tests passed: creation isolation, full-story import/export,
  introduction boundaries, all five types, explicit categories, uncertain ending,
  history transitions, and legend/renderer color correspondence.
- Real-Tk workflow test opened the example through the app's story-switch action,
  loaded bargain and broken-promise views, created a new node in free space, and
  reviewed/committed a connection in a disposable copy.
- Final build: **200 tests passed in 100.925 seconds**.
  Evidence: `build-verification/examples-build.log`.
- Packaged smoke: **passed**, version 0.14.0, schema 12, frozen=true. Includes
  opening the second example, loading both relationship-transition scenes, and
  checking the combined legend. Evidence: `build-verification/packaged-smoke.json`
  and `build-verification/examples-packaged-smoke.log`.
- Generated graph previews were visually inspected at normal and small sizes.
  The key remains outside the node area. Small canvases can still overlap long
  relationship labels; overview labels are hidden and scene views support zoom
  and inspection. These previews are not full-window screenshots. No additional
  native-window, DPI, or clean-machine manual review was performed.

## Modeling limits

The walkthrough records chronology versus flashbacks, current-only profile
fields, the meaning of Player/NPC adaptation labels, and persistent fact-links
versus living interaction states. It does not invent a living second creature or
claim to witness the creature's announced death. Saved views are included in the
database files; ordinary JSON story export does not carry those presentation presets.

## Local package identities

- Executable SHA-256: `901cb0a0cbc181fdbdc02451dec53f69cc55b7084ac32c9476e3e7f3782b1d34`
- Windows ZIP SHA-256: `e44ce8b877db2d015f5938c368035db84382c397882b391ee87551dbb620c92e`
- Prometheus database SHA-256: `17a3654a6f5a94fcbe28b3dbd25a567515e522ce3a7fff94335de5f341a2cabd`
- Greyhaven database SHA-256: `9854c1a1c273221aa6b168acd16b1794e1c3b2775f9d19f865e24a9e4bd0833e`

Source and packaged fingerprints were verified equal. Artifacts were built locally;
no publication was performed.
