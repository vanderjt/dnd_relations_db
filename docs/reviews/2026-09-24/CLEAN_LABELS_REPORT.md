# Graph label cleanup — 0.14.1

Removed numeric IDs from plotted character and relationship labels, including
selection/highlight redraws. The plotted legend uses category names alone; marker
and line swatches provide the distinction. Internal identifiers and picking remain
unchanged. Example previews and the example archive were regenerated and inspected.

All 200 tests passed in 102.692 seconds (`build-verification/clean-labels-build.log`).
The default packaging destination contained a Windows-locked native module, so
PyInstaller was rerun with the same frozen metadata into a separate directory.
The complete replacement is **dist/releases/0.14.1/StoryAtlas**. The workspace's
packaged launcher prefers that directory. Do not use the partially replaced older
dist/StoryAtlas folder; use the launcher, new directory, or rebuilt ZIP.

The Windows ZIP was rebuilt from the separate directory. Packaged smoke passed
against its executable (`build-verification/clean-labels-packaged-smoke.log`), and
source/package fingerprints match. Schema remains 12 and portable format remains 8.
