# Preview offline installer

Run `build_preview_installer.ps1` from Windows PowerShell to build the React
preview, run focused tests, freeze its Python host, compile Setup, and generate
a SHA-256 checksum. Output is in `installer/`, alongside the tracked Setup
definition and instructions. Setup EXEs are stored with Git LFS. After cloning,
run `git lfs install` and `git lfs pull` if the EXE has not been downloaded.
The installer creates desktop
and Start Menu shortcuts and installs per user. It never deletes user stories
or backups on uninstall.

## Build prerequisites

- CPython 3.13 x64 in `.build-env`, with `requirements-preview.txt` and
  PyInstaller 6.22.0 installed; Node.js and `npm ci` in `preview`.
- Inno Setup 6.7.3 compiler at `build/inno/ISCC.exe`, or supply `-Compiler`.
  Obtain it from https://jrsoftware.org/isinfo.php and observe its license.
- Microsoft's x64 Evergreen Standalone WebView2 installer at
  `build/installer-deps/MicrosoftEdgeWebView2RuntimeInstallerX64.exe`.
  Official download: https://go.microsoft.com/fwlink/?linkid=2124701.
  The build verifies a valid Microsoft Authenticode signature.

Build dependencies need downloading once. End users receive a single Setup
EXE containing the frozen host, frontend assets, Greyhaven sample, and full
WebView2 runtime. Setup checks the documented EdgeUpdate runtime registry key
and invokes the included installer only when the runtime is missing.

Version lives in `installer/StoryAtlasPreview.iss`; the output filename and
build script derive it from that definition. Increase the version for each
release and update user-facing filenames in the READMEs. The build writes
`installer/release.json` with the version, source commit, filename, and SHA-256.
Commit and publish the new EXE, checksum, and manifest together through Git LFS.
Remove the superseded EXE and checksum from the current checkout after the
new release passes verification.
This uses `StoryAtlasPreview.spec`, not the legacy Tkinter `StoryAtlas.spec`.
No signing certificate is configured; Setup and the application are unsigned.

## Updating installed copies

Users close the app, run `git pull --ff-only` and `git lfs pull`, then open
`installer/Manage Story Atlas.cmd`. Install/update runs the verified bundled
Setup over the installed copy. Its stable AppId keeps it registered as the same
app. Uninstall/reinstall validates the new Setup first, invokes the registered
uninstaller, and installs again only after uninstall completes. The menu never
deletes the story data directory. Ordinary Setup and uninstall dialogs remain
visible, and cancellation stops the operation. A Start Menu uninstall shortcut
is included in new installations.

Publish rebuilt installers when changing packaged features. The manager does
not build source or silently download updates. Mac source users can pull and
run `Launch Story Atlas.command` to refresh dependencies and built assets; see
`installer/README-MAC.md`.

## Acceptance evidence

On October 2, 2026 the frontend build and 28 focused Python tests passed.
The frozen app loaded its bundled sample. The generated installer returned
exit code 0, and both shortcut files were verified. The installed executable
reopened the disposable saved sample after the frozen app closed through X.
Installer log: `build-verification/installer.log` (ignored local evidence).

Clean-machine testing without preinstalled WebView2/Python/Node and with
networking disabled remains outstanding. The missing-runtime installation path
and uninstall/upgrade behavior have not been exercised on a clean machine.
Target friends' Windows 10/11 x64 PCs for this preview; do not claim broader
platform certification. See `installer/README.txt` for distribution instructions
and `docs/MVP_DELIVERY.md` for existing feature limitations.
