# Build and verify a Windows release

End users should follow [Windows installation](../installer/README.txt).
This guide is for maintainers building a new release from source. Building a
candidate and publishing it are separate steps.

## Version and provenance

`VERSION` is the single source of the current source version. The cleanup
source targets **0.1.2**, a release candidate, not a newly published installer.
The build passes that version to Inno Setup; do not maintain a second version
in `preview/package.json` or hardcode one in the Setup definition.

The bundled `installer/release.json`, 0.1.1 EXE, and checksum intentionally
remain the older release from `d6376bc388169bfe636115be5ea2ef444ff875b8`.
See [release history](RELEASE_HISTORY.md). Do not replace or relabel them just
because source changes are ready.

## Prerequisites

Build on Windows x64 with Python 3.13, Node.js/npm, Git, and the source checkout.
Runtime dependencies and packaging dependencies are separate:

```powershell
py -3.13 -m venv .build-env
.\.build-env\Scripts\python.exe -m pip install -r requirements-preview.txt -r requirements-build.lock.txt
cd preview
npm ci
cd ..
```

Prepare these tools locally:

- Inno Setup, using the project's established 6.7.3 toolchain, at
  `build/inno/ISCC.exe` or another path supplied with `-Compiler`.
  Obtain it from [the official site](https://jrsoftware.org/isinfo.php).
- Microsoft's signed x64 Evergreen Standalone WebView2 installer at
  `build/installer-deps/MicrosoftEdgeWebView2RuntimeInstallerX64.exe`.
  Use the [Microsoft download](https://go.microsoft.com/fwlink/?linkid=2124701).

The app and Setup are unsigned; no application signing certificate is
configured. Checking Microsoft's runtime signature does not sign the app.
The build tools and dependencies are not distributed to end users.

## Build a candidate

1. Set `VERSION` for the candidate, finish changes, and run the contributor
   checks. Commit the intended source before building. The script requires a
   clean tracked and untracked source tree so its manifest identifies the
   source actually built. Ignored build artifacts are expected.
2. Run from the repository root:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File build_preview_installer.ps1
   ```

   Optional paths:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File build_preview_installer.ps1 -Compiler "C:\Tools\Inno Setup 6\ISCC.exe" -OutputDirectory "C:\Builds\StoryAtlasCandidate"
   ```

3. Inspect the output in `build/releases/<version>` by default, or the selected
   output directory. It contains the candidate EXE, `.sha256`, and
   `release.json` with the version, source commit, filename, and checksum.
   The build does not automatically overwrite the bundled release in
   `installer/`. Keep custom output outside tracked source (or in an ignored
   build directory), or the final clean-tree check will reject it.
4. Complete and record the verification below before promoting the candidate.

The build installs frontend dependencies from the lockfile, type-checks and
bundles the frontend, checks clean/repeatable generated output, runs the Python
unit suite and saved-example checks, freezes the app with `StoryAtlasPreview.spec`, validates
the Microsoft runtime signature, and compiles Setup. A successful build alone
is not a full native UI, manager, lifecycle, or clean-machine test.

Keep production AppId `B1A827F6-93A7-4365-A494-D793125179DA` stable. Setup installs
per user, retains stories and backups outside the application directory, and
copies examples only when their destination names are absent.

## Verification

### Source and fixture checks

```powershell
.\.build-env\Scripts\python.exe -m unittest discover -s tests -v
.\.build-env\Scripts\python.exe tools/verify_examples.py
cd preview
npm run build
npm run test:build
cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_installation_manager.ps1
```

The manager script uses mocked process/registry behavior. It checks manager
logic and failure handling; it does not prove real Windows Setup behavior.
Frontend checks and Python tests likewise do not prove native rendering.
See [Contributing](../CONTRIBUTING.md#checks) for cross-platform limits.

### Hosted Windows packaging and lifecycle CI

The `Verify Windows installer` workflow builds an offline candidate on a
GitHub-hosted Windows runner and retains the candidate and verification evidence
as seven-day Actions artifacts. It never publishes a release or installs the
production AppId. The hosted-only helper is `tools/verify_windows_ci.ps1`.

The workflow rebuilds the recorded 0.1.1 source with the current pinned build
requirements, then builds the current candidate and runs the isolated lifecycle
checks below. This is not a byte-for-byte reproduction of the shipped 0.1.1 EXE.
Evidence records source commits, dependency/compiler/runtime versions, payload
hashes, and exact results. A frozen `--help` probe checks packaged startup only.
When the runner has an interactive desktop session, a bounded source-native
Greyhaven smoke also runs through real WebView2; otherwise evidence records the
unsupported session explicitly. Attempted smoke failures fail the job, while
artifacts are retained for inspection. None of these checks replaces the
interactive and clean/offline release acceptance gates.

### Native app smoke

`tools/preview_native_smoke.py` drives actual WebView2/bridge flows on Windows.
Use only a disposable `--home`, for example:

```powershell
.\.build-env\Scripts\python.exe tools/preview_native_smoke.py --home .\build-verification\native-sample --stage sample
```

Its `--stage` choices include creation/reopen, layout, story scrolling,
storage-failure and crash recovery, and native X-close/save/reopen cases.
Stages that reopen an existing story need the matching predecessor and data
root; they are not independent checks. This helper selects WebView2 and is not
a Mac acceptance test. Record stages actually executed and inspect failures.

### Installer lifecycle and clean-machine acceptance

`tools/verify_installer_lifecycle.py` requires two frozen app directories with
increasing versions and at least one changed shared payload file. Preserve a
previous build's `dist/StoryAtlasPreview` separately before building the new
one; an installed app directory containing an uninstaller is not a valid input.
Run on Windows with Inno Setup and Windows PowerShell available:

```powershell
.\.build-env\Scripts\python.exe tools/verify_installer_lifecycle.py --run-windows-sandbox --old-payload "C:\Builds\Previous\StoryAtlasPreview" --old-version 0.1.1
```

`--new-payload` defaults to `dist/StoryAtlasPreview`; `--new-version` defaults
to `VERSION`. Use `--compiler` for a non-default Inno Setup path. `--help` lists
the options without installing anything.

The explicit opt-in installs disposable test fixtures into the current Windows
account with a unique AppId and test-only app/data paths. It does not create a
virtual machine or invoke the Windows Sandbox product. It compiles old/new
Setup fixtures and runs the real manager through a silent process wrapper for
check, install, upgrade, custom-path reinstall, uninstall, and installation
after removal. It verifies registration versions, payload hashes, and preserved
synthetic stories, backups, edited examples, and metadata. It records the state
of old-only payload files rather than assuming in-place upgrades remove them;
after manager reinstall it checks that those obsolete tracked files are gone.

The helper retains `evidence.json`, logs, and test data under
`build-verification/`, and removes its test app/registration during cleanup.
Only WebView2 detection is stubbed; the offline runtime is excluded. Interactive
cancellation is covered by mocks, not the silent fixture. A passing run would
not prove native app launch, normal desktop/Start Menu shortcuts, or
clean-machine/offline runtime installation. Fixture shortcuts are redirected
and disabled, so shortcut acceptance must be done separately.
For an actual release, also complete the following acceptance checks:

- Exercise old-to-new upgrade with distinct versions and payloads, retaining a
  synthetic story, backup, and edited example across update/uninstall/reinstall.
- Exercise the real installation manager's cancellation, custom-path, missing
  package, and bad-checksum paths; mocked passes are not native evidence.
- Launch the installed candidate through its shortcuts and verify create,
  edit, save, close, reopen, sample, backup, and restore with disposable data.
- Test installation on a clean Windows machine without WebView2, with network
  access disabled. Confirm the bundled runtime permits startup.
- Confirm uninstall removes test app/registration but preserves test stories.

Store logs and evidence under `build-verification/` (ignored by Git). Record
source commit, package hash, Windows/tool versions, exact commands, observed
results, and checks not run. Native Mac testing is separate and remains pending.

## Promote only a verified release

After verification and release approval, copy the candidate EXE, checksum, and
manifest into `installer/` together, update the end-user release filename and
release-history notes, and review the diff. EXEs use Git LFS. Only remove the
superseded release after the replacement has passed its gates; retain its
provenance in the historical record. Commit release artifacts together and
publish only through the project's approved release workflow.

Check the actual downloaded/published EXE against its manifest before telling
users to install it. `manage_installation.ps1 -Action Check` verifies the
bundled package next to that manager, not an arbitrary staged build. A checksum
match verifies consistency, not publisher identity or runtime behavior.

## Installed-user behavior

`installer/Manage Story Atlas.cmd` offers install/update, uninstall, and
uninstall/reinstall. The PowerShell entry point accepts `-Action Menu`,
`Install`, `Uninstall`, `Reinstall`, or `Check`.

An in-place update replaces current payload files but can retain application
files present only in the older release. **Uninstall/reinstall** removes
installer-tracked obsolete application files before installing the new payload,
while preserving the separate story data. It does not promise to remove
untracked files manually placed in the app directory. No broad wildcard
deletion is used to force upgrade cleanup.

The manager validates the replacement before uninstalling, uses the registered
custom app directory, and carries that path into reinstall. Cancellation,
errors, or incomplete uninstall cleanup stop the reinstall. The manager does
not build source or download an update. Pulling new source is not a packaged
upgrade; installed users need a newly built release.
