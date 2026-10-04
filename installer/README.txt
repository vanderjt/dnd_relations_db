STORY ATLAS PREVIEW 0.1.1 — WINDOWS OFFLINE INSTALLER

Mac users: see README-MAC.md in this folder. Use Launch Story Atlas.command
in the repository's main folder; this Windows Setup EXE does not run on macOS.

Installing from this Git repository
1. Use a Windows 10/11 x64 PC. Install Git and Git LFS if needed:
     Git: https://git-scm.com/downloads/win
     Git LFS: https://git-lfs.com/
2. Open PowerShell in the folder where you want the repository, then run:
     git lfs install
     git clone --branch codex/repo-housekeeping https://github.com/vanderjt/dnd_relations_db.git
     cd dnd_relations_db
     git lfs pull
3. In File Explorer, open the repository's installer folder and double-click:
     StoryAtlasPreview-0.1.1-Windows-x64-Offline-Setup.exe
4. Follow Setup and leave "Create a desktop shortcut" checked.
5. Open Story Atlas Preview from the desktop or Start menu. You can also
   double-click Launch Story Atlas.cmd in the repository's main folder.

If you already cloned the repository, open PowerShell in its main folder:
  git fetch origin
  git switch codex/repo-housekeeping
  git pull --ff-only
  git lfs install
  git lfs pull
Then run the Setup EXE in this installer folder as described above. Save or
commit any local edits before switching branches or pulling updates.

Use the codex/repo-housekeeping branch: that is where this installer is published.
Use a Git LFS clone instead of GitHub's Download ZIP. The installer is about
228 MB; a tiny text file starting with "version https://git-lfs.github.com"
is an LFS pointer. Run git lfs pull to download the real executable.
Internet access is needed to clone and download the installer. After that,
Setup runs offline. Python and Node.js are not needed to install or run the app.

For friends installing from a flash drive
1. Copy StoryAtlasPreview-0.1.1-Windows-x64-Offline-Setup.exe to the drive.
2. On the destination Windows 10/11 x64 PC, double-click that file.
3. Follow Setup and leave "Create a desktop shortcut" checked.
4. Open Story Atlas Preview from the desktop or Start menu.
5. Create a story, try Greyhaven, or use Open story for the included Frankenstein,
   Dracula, and Cyberpunk: Edgerunners Season 1 examples in the Stories folder.

The flash drive can be removed after installation. Python, Node.js, and an
internet download are not required: Setup includes the app and Microsoft's
offline WebView2 runtime, which it installs if missing.

This preview installer is not code-signed. Windows may identify its publisher
as unknown. The embedded Microsoft runtime is signed by Microsoft.

Updates, uninstall, and reinstall
1. Save your edits and close Story Atlas.
2. In PowerShell in the repository folder, run:
     git pull --ff-only
     git lfs pull
3. Double-click Manage Story Atlas.cmd in this installer folder.
4. Choose 1 (Install/update) and follow Setup. This replaces the installed
   app without needing to uninstall it first. Your stories and backups remain.
5. Reopen the installed app using its desktop or Start Menu shortcut.

The menu also provides option 2 (Uninstall) and option 3 (Uninstall/reinstall).
Option 3 checks the new installer before removing the old app. Cancelling
uninstall stops the reinstall. Each operation uses the normal Setup dialogs.
You can also uninstall using Windows Settings > Apps > Story Atlas Preview,
or the Start Menu's Uninstall Story Atlas Preview shortcut.

The menu checks the installer's SHA-256 against release.json before installing.
Keep Manage Story Atlas.cmd, manage_installation.ps1, release.json, and the
Setup EXE together if copying the manager to a flash drive. The Setup EXE
alone still works when double-clicked.

New source code does not automatically update the installed app. A new Setup
build must be published for each release. The manager displays the bundled
version and source commit so you can identify which release you are installing.
Use installed desktop/Start Menu shortcuts for that release: the repository's
root launcher can prefer source mode or a local developer package instead.

Your files
The app installs for your Windows account in:
  %LOCALAPPDATA%\Programs\Story Atlas Preview
Default story data and backups live separately in:
  %LOCALAPPDATA%\StoryAtlasPreview
Uninstalling the app preserves those story files. Use the app's backup command
to transfer a story; copying the installer does not copy your personal stories.
Setup includes the three authored example stories. Existing files with the same
names are never overwritten, and uninstalling preserves the examples too.
Frankenstein and Edgerunners include embedded offline portraits. Image credits
are recorded in portrait-sources.json and inside each illustrated story.
Legacy Tkinter stories and browser-prototype edits are not imported by this
preview. Existing preview limitations remain; this package adds installation,
not new editing features.

Verification, October 3, 2026 (0.1.1)
Production frontend build and 34 focused Python tests passed. All three saved
examples passed integrity and close/reopen checks. An isolated installation
test passed install, update, uninstall, and reinstall using the frozen app
payload. A test story, backup, and user-edited example remained byte-for-byte
unchanged. Test registration and app files were removed afterward. The manager
validated the published installer checksum. The isolated lifecycle test omits
the WebView2 bootstrapper; clean-machine runtime testing remains outstanding.
This release includes the story scrolling and notification dismissal fixes.

Earlier verification, October 2, 2026 (0.1.0)
Production frontend build and 31 focused Python tests passed. Saved examples
passed database integrity, timeline, and close/reopen checks. Setup installed
successfully on the development PC. Desktop/Start Menu shortcuts were created,
the packaged Greyhaven sample opened, X closed the app, and the installed copy
reopened that saved sample. Tests used disposable story data.
A clean PC without WebView2 and an installation with networking disabled have
not yet been tested. Treat this as a friends-and-family preview release.

The adjacent .sha256 file records the setup file's SHA-256 checksum.
