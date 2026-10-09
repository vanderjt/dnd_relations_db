# Contributing to Story Atlas

The supported application is the React/pywebview source launched by
`preview_main.py`. Start with the [Windows source setup](README.md#run-from-source-on-windows)
or [Mac source setup](installer/README-MAC.md). VS Code can run the Python entry
point directly; it is an editor choice, not a runtime dependency.

## Work safely

Use a separate data root for development and all UI experiments:

```powershell
.\.build-env\Scripts\python.exe preview_main.py --home .\build-verification\manual-dev
```

On Mac, use `.mac-env/bin/python` with the same `preview_main.py --home ...`
arguments. `--home` controls settings, newly created stories, and backup
locations. It does **not** copy or isolate a file passed to `--story` or selected
with **Open story**: those are edited in place. Use copies of examples and
synthetic stories, never real campaign data, for destructive or failure tests.
Do not open the same working file in multiple app instances.

Public source entry points remain:

- `preview_main.py` with `--home`, `--story`, and `--debug`.
- `Launch Story Atlas.cmd` for Windows source/package/installed selection.
- `Launch Story Atlas.command` for Mac source setup and launch.
- `installer/Manage Story Atlas.cmd` for Windows installation management.

## Development loop

1. Make changes in `preview/src`, `preview/assets`, `preview_main.py`, or
   `story_atlas`, as appropriate. Do not edit generated `preview/dist` files.
2. If Python requirements changed, install the relevant platform requirements
   again. On Windows, the runtime pins are `requirements-preview.txt`; Mac uses
   `requirements-preview-macos.txt`.
3. If the frontend lockfile changed, run `npm ci` inside `preview`.
4. Run `npm run build` inside `preview` after frontend changes. This command
   includes TypeScript checking. It does not run browser or native UI tests.
5. Run the Python checks below and launch the changed flow with disposable data.

The Mac launcher refreshes requirements and changed frontend assets itself.
The Windows launcher only selects an already prepared launch target; it does
not build source, install dependencies, or update the installed release.

## Checks

From the repository root on Windows:

```powershell
.\.build-env\Scripts\python.exe -m unittest discover -s tests -v
.\.build-env\Scripts\python.exe tools/verify_examples.py
cd preview
npm run build
npm run test:build
cd ..
```

On Mac or a non-GUI test host, substitute the chosen Python interpreter for
`.\.build-env\Scripts\python.exe`. These unit and example checks do not require
an actual native window. Passing them on Linux or with stubbed `webview` objects
is not proof that the Mac or Windows renderer works.

The unit suite exercises storage transactions, retries, drafts, timeline
semantics, portraits, platform selection, bridge close/picker behavior, and
release metadata/fixture guards. `npm run test:build` checks clean, repeatable
frontend output, including removal of stale generated assets. `npm run typecheck`
can run TypeScript checks separately from bundling.
`verify_examples.py` checks the three checked-in stories for integrity,
expected timeline facts, and matching close/reopen snapshots. It does not
verify artwork rights or exercise the native file picker.

The source CI workflow runs on Ubuntu and Windows with Python 3.13 and Node 22.
It also runs manager mocks on Windows. This workflow is source verification,
not a packaged app or installer acceptance run.

For native WebView2 and installer checks, use the
[Windows verification instructions](docs/OFFLINE_INSTALLER.md#verification).
Record the actual source commit, commands, operating system, and results.
Distinguish passes, failures, and checks not run. A historical release report
must not be reused as evidence for changed source.

## Review checklist

- Preserve the data format and transaction guarantees in
  [Architecture](docs/ARCHITECTURE.md). Never silently convert or overwrite an
  unsupported file.
- Keep the installer AppId and separate story-data paths stable. Installation,
  update, uninstall, and reinstall must retain stories, backups, and edited
  examples.
- Preserve Greyhaven, all three examples, embedded portraits, and credits.
  Test example changes on copies and keep the provenance files intact.
- Keep runtime assets local. Source dependency downloads and release-building
  downloads are separate from the app's offline runtime.
- Update docs when launch commands, data behavior, or release steps change.
- Keep virtual environments, `node_modules`, generated builds, verification
  artifacts, and personal stories out of commits. Review `git diff --stat` and
  `git status --short` before committing.

## Packaging is a separate step

Source changes do not alter the existing Windows EXE. Follow the
[release build guide](docs/OFFLINE_INSTALLER.md) to produce and verify a new
package. Do not relabel or rewrite the provenance of the bundled 0.1.1 release
to describe newer source. Retain the known release until its replacement passes
the appropriate checks. Building locally is not publishing a release.
