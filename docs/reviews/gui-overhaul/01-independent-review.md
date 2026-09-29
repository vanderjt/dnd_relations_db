# Stage 01 — independent review

Reviewer: the independent review agent, separate from the foundation implementation agent. Reviewed feature commit `9248c3e` against `gui_overhaul`, then reviewed the fixes below in the working tree. The primary agent owns integration and GitHub actions; this report is agent review evidence, not a separate human GitHub approval.

## Scope and findings

Reviewed all changed Python files, asset manifest/build ingestion, copied license text, integration workflow record, baseline report and capture utility. The integration record correctly preserves `main`, requires feature branches and sequential reviewed PR integration, and excludes later map/inventory/audio features.

Two findings were sent to the foundation agent and corrected:

1. Optional artwork decoding could raise Pillow's oversized-image exceptions instead of falling back to text. The loader now catches both decompression-bomb exception types and rejects dimensions over 2048 before converting pixels. Independent tests exercise both exception paths and the predecode dimension limit without allocating large images.
2. The shared identity header applied the amber Context treatment to ordinary Advanced character metadata. It now uses neutral Muted text, keeping chronology/unsaved context visually distinct.

The loader otherwise has bounded per-root caches, path containment checks and widget-owned image references surviving eviction. Missing/malformed catalogs and image files preserve text controls. Built-in assets remain separate from managed portrait storage, and the source fingerprint includes resource bytes and license files. The initial 30-image subset has semantic aliases and source provenance; no runtime source-pack path is needed.

Added `tests/test_ui_asset_review.py` to verify real Advanced and Simple editing sessions retain their original editor instances, unsaved field values, original saved baselines and stored data across theme/text/Illustrated changes. It also verifies an imported Simple portrait remains visible in Minimal mode. These checks exercise application behavior beyond the original isolated Entry-widget test.

## Capture review and visual limits

The capture utility uses disposable stories/settings, reports requested and actual geometry/preferences, distinguishes simulated Tk scaling from physical DPI, records callbacks and fails for callback errors. It now captures portrait overview/editor states and destroys its temporary app even if database cleanup raises. Its temporary topmost flag affects only the disposable capture window. OS overlays can still obscure screenshots; invalid captures must be excluded explicitly.

Independently inspected the post-fix Advanced dark Minimal imported-portrait screenshot at `build-verification/gui-overhaul/pilot-minimal-20260928-204115/advanced-dark-1180x720-10pt-overview-portrait.png`: portrait and profile text are visible, metadata is neutral, historical context remains distinct. The visual-QA agent separately reviewed both themes/modes and excluded one task-switcher-occluded image. Existing 760×480/16pt crowding is documented as baseline behavior, not a passing release gate. Stage 02 must improve header geometry and subsequent work must address remaining minimum-size workspace crowding.

## Validation and recommendation

Executed `.build-env/Scripts/python.exe -m unittest discover -s tests -q` serially after visual-QA released the desktop: **233 tests passed in 128.022 seconds**, with no skips or failures. Log: `build-verification/gui-stage1-review-tests.log`. This includes both independent regression tests and all existing profile, appearance, relationship, recovery, graph and chronology coverage. Only existing Matplotlib dependency deprecation warnings were emitted. The graph benchmark reported initial 0.846s, note refresh 0.037s, direct focus 0.057s and Simple 0.293s; these single-run timings are not a controlled performance comparison.

**Recommendation: integrate Stage 01 after committing the reviewed fixes and evidence.** No unresolved Stage 01 findings remain. This is a foundation-stage acceptance, not release acceptance: physical DPI, packaged-resource execution, final navigation completeness and documented minimum-window crowding remain later gates.
