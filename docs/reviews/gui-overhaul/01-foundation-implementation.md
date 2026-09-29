# Stage 01 — artwork foundation and character pilot

Implemented a 30-image HAS subset: 21 book/equipment/object motifs and nine buildings. Exact original paths, SHA-256 digests, native sizes, author, copied license texts, descriptions and semantic aliases are recorded in `story_atlas/resources/ui/manifest.json`. The contact sheet at `build-verification/gui-assets-contact.png` was visually inspected. Original bytes are preserved; scaling happens through nearest-neighbor rendering at runtime. Artwork is incorporated into Story Atlas, not published as a separate asset pack.

Regenerate with `.build-env/Scripts/python.exe tools/build_ui_assets.py C:/Users/Jonathan/Documents/asset_packs --contact-sheet build-verification/gui-assets-contact.png`. The source root and output are configurable. Runtime only reads packaged resources. Build fingerprints now include UI artwork, manifest and licenses.

## Shared contracts for subsequent stages

- `ui_assets.decorate(widget, semantic_key, size=32)` decorates an existing labeled ttk control. The widget retains its PhotoImage independently of LRU eviction.
- `ui_assets.cache_for(widget).get(key, size=32, theme='dark', state='normal')` resolves the bounded, interpreter-owned cache. Missing resources, corrupt images/catalogs and path escapes fall back to no image. Call from the Tk thread.
- `ui_assets.refresh_illustrations(root)` updates existing controls without rebuilding forms or changing values.
- `illustrated_widgets.IllustratedLabel(parent, key, size=32, **kwargs)` is a wrapping section label.
- `illustrated_widgets.IdentityHeader(parent)` exposes `name`, `details`, `portrait`, `photo`; `show_portrait(assets, filename)` uses the managed user-portrait pipeline. It never invents a person's appearance.
- `settings.values['illustrations']` is `Illustrated` (default) or `Minimal`, independent of theme. `StoryAtlas.set_appearance(theme, size, illustrations=None)` persists and refreshes it; the existing two-argument call remains supported. A visible preference control belongs to the supporting-screens stage.
- `ui_assets.artwork_credits()` provides attribution text for later Help/About integration.

Advanced overview and Simple summary share the identity component. Overview's public name/details/portrait/photo access and missing-portrait wording remain intact. ProfileEditor supplies section emblems to both Advanced and Simple editors; collapsed/filled indicators retain their behavior. Save character has the shared primary treatment. User portraits stay visible in Minimal mode.

## Validation

`.build-env/Scripts/python.exe -m unittest tests.test_ui_assets tests.test_profiles tests.test_appearance -q`: **25 tests passed in 9.998 seconds**, no skips. This covers provenance and license completeness, resource-sensitive build identity, settings validation, root cache isolation, live image retention after eviction, malformed/missing/corrupt resources, Minimal refresh preservation of entry content and portrait images, plus existing profile and appearance workflows.

Full regression, independent review and application screenshot matrix are separate integration gates. Physical multi-monitor DPI and frozen-package verification have not been performed in this stage. The package spec already includes the resources directory; release validation must verify the nested UI files in the built distribution. No story schema change, inferred inventory parsing, animated artwork, or graph portrait nodes were introduced.
