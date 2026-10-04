# Build and distribute the Windows installer

End users can install the ready-made EXE in `installer/` without Python or Node.
See [Windows instructions](../installer/README.txt) for install, update,
uninstall, and reinstall, and the [user guide](USER_GUIDE.md) for using the app.

## Build prerequisites

Use Windows x64 with Python 3.13, Node.js LTS, and the repository's source files.
Create `.build-env` and install both runtime and packaging dependencies:

```powershell
py -3.13 -m venv .build-env
.\.build-env\Scripts\python.exe -m pip install -r requirements-preview.txt -r requirements-build.lock.txt
cd preview
npm ci
cd ..
```

Prepare these build dependencies once:

- Inno Setup 6.7.3 at `build/inno/ISCC.exe`, or pass its path with `-Compiler`.
  Obtain it from https://jrsoftware.org/isinfo.php and observe its license.
- Microsoft's signed x64 Evergreen Standalone WebView2 installer at
  `build/installer-deps/MicrosoftEdgeWebView2RuntimeInstallerX64.exe`.
  Official download: https://go.microsoft.com/fwlink/?linkid=2124701.

## Build and publish

1. Update `AppVersion` in `installer/StoryAtlasPreview.iss` and the release
   filenames in the READMEs. Commit the source changes to identify the build.
2. Run `build_preview_installer.ps1`. It builds the frontend from `preview/assets`,
   runs current app and example checks, freezes Python with `StoryAtlasPreview.spec`,
   verifies the Microsoft runtime signature, and compiles the offline Setup.
3. Verify the generated release. The script creates the EXE, `.sha256`, and
   `release.json` in `installer/`. The manifest records the version, source
   commit, filename, and checksum.
4. Remove the superseded EXE and checksum from the current checkout after the
   new release passes checks. Commit and push the new release files together.
   EXEs use Git LFS; the manifests and documentation use ordinary Git.

Keep the installer AppId stable across releases so Setup updates the same app.
The app installs per user and includes the frozen host, frontend, sample,
examples, and offline WebView2 runtime. The runtime is installed only if missing.
Setup and the app are unsigned; no signing certificate is configured.

## Verify a release

```powershell
.\.build-env\Scripts\python.exe -m unittest discover -s tests -q
.\.build-env\Scripts\python.exe tools/verify_examples.py
powershell -NoProfile -ExecutionPolicy Bypass -File installer/manage_installation.ps1 -Action Check
.\.build-env\Scripts\python.exe tools/verify_installer_lifecycle.py
```

The lifecycle check requires a current frozen package in `dist/StoryAtlasPreview`.
It compiles a separate test installer with a unique AppId and disposable app/data
folders. It checks install, update, uninstall, reinstall, and story/backup/example
preservation, then uninstalls the test app. It omits the WebView2 bootstrapper.
Use `tools/preview_native_smoke.py` only with a disposable `--home`; its script
contains the available workflow and layout stages. Verification artifacts are
ignored under `build-verification/`.

Native Mac testing and clean-machine Windows testing without preinstalled
WebView2 or with networking disabled are still pending.

## Updating installed users

Publish a rebuilt installer for packaged feature changes. Users close the app,
pull the repository and LFS files, and open **installer/Manage Story Atlas.cmd**.
**Install/update** replaces the app without uninstalling first. **Uninstall** and
**Uninstall/reinstall** preserve the separate story directory. The manager
verifies the replacement before uninstalling and uses the registered uninstaller
for custom paths. Cancelling uninstall stops the reinstall.

The manager does not build source or silently download updates. Mac source
users can pull and run `Launch Story Atlas.command` to refresh dependencies
and assets; see [Mac instructions](../installer/README-MAC.md).
