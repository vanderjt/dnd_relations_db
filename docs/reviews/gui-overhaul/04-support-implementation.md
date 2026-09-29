# Supporting screens and release preparation

Story Atlas source version **0.19.0**, database schema **13**, portable format **9**. No database migration was introduced.

## Implementation

- Welcome uses a bounded shared library vignette and quieter sample buttons. Start empty and Open story remain in a pinned bottom action group; Start empty is the primary action.
- Story setup uses scrollable fields, an optional opening section and pinned Create/Cancel actions. Title-derived file publication and existing save callbacks are preserved.
- Appearance adds an explicit Illustrated/Minimal choice and explains that imported portraits remain visible. Apply uses the existing live appearance path, retaining unsaved inputs.
- Artwork credits displays attribution and both original HAS license files in selectable, read-only scrolling text with a fixed Close action.
- Recovery reserves action/retention space before expanding its tables, groups browse/import under More, and enables selection actions only when a record is selected. Existing confirmation and restore/import semantics remain unchanged.
- Enabled boundary colors were strengthened in both themes. Primary buttons use the on-accent color for their internal focus cue; the outer focus border still uses the theme focus token.
- Packaging diagnostics explicitly validate all 30 bundled asset paths and hashes, included license content, semantic aliases, representative icon/building Tk images, Illustrated/Minimal persistence and imported-portrait retention. Tk callback errors now fail self-test. Package execution and final fingerprint matching are separate primary-agent release gates.
- README, distribution guidance and roadmap status were updated for current menu routes and 0.19.0. Historical release evidence is labeled historical.

## Focused validation

Six new support tests passed in 2.443s, covering minimum-size setup actions, appearance/draft/portrait preservation, read-only complete credits, Recovery selected-state controls and restoration, Welcome hierarchy and contrast. Four existing Recovery UI tests passed in 5.219s. Eight distribution/startup tests passed in 2.634s. Syntax validation passed for the capture helper and diagnostics. These targeted tests precede independent full-suite review and final screenshots.

The numeric contrast audit checks **66 actual enabled-state palette pairs**. All meet their design targets: lowest text contrast **4.752:1** against a 4.5 target; lowest essential boundary/outer-focus contrast **3.062:1** against a 3 target. Disabled controls, pixel-art colors, and antialiased glyph rendering are outside this palette audit. Selected table rows use normal text rather than muted text. This is not a claim of complete accessibility conformance. Re-run with `python tools/check_ui_contrast.py`.

## Capture and release handoff

`tools/capture_gui_overhaul.py --support-only` adds 36 default/minimum supporting-screen and true-empty cases across both themes. `--support` includes them alongside the core matrix; `--minimum-only` reduces support to 18 cases. Recovery fixtures include a discarded fictional character and an uncommitted draft. Setup captures show the expanded opening section. All files/settings are disposable. Windows captures target each owned window HWND directly. `--text-size 9..16` supports additional text-size spot checks; optional Tk scaling remains explicitly simulated, including Welcome/support dialogs.

Independent review and final visual capture findings are recorded separately. Physical mixed-monitor scaling, a genuinely clean machine, and representative-user testing remain unavailable in this local run. Portrait graph nodes, inventory records, geographic maps, audio and other P2 features remain outside this release.
