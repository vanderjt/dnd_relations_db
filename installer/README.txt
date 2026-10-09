STORY ATLAS PREVIEW — WINDOWS OFFLINE INSTALLER

BUNDLED RELEASE: 0.1.1
Source commit: d6376bc388169bfe636115be5ea2ef444ff875b8

This EXE predates the current source. Pulling source changes does not rebuild
or update an installed app. The release.json beside this file describes the
bundled EXE, not the latest source. See ../docs/RELEASE_HISTORY.md for historical
verification and remaining platform limits.

Mac users: see README-MAC.md. There is no standalone Mac installer.
Source developers: see ../README.md and ../CONTRIBUTING.md. VS Code and direct
preview_main.py launch remain supported independently of this installer.

INSTALL FROM A DOWNLOADED FILE OR FLASH DRIVE
1. Use a Windows 10/11 x64 PC.
2. Run StoryAtlasPreview-0.1.1-Windows-x64-Offline-Setup.exe.
3. Follow Setup and select a desktop shortcut if wanted.
4. Open Story Atlas Preview from the desktop or Start Menu.

The flash drive can be removed afterward. Python and Node.js are not needed.
Setup includes the app and Microsoft's offline WebView2 runtime, installing
the runtime if missing. Installation is designed to work without a download;
a clean Windows machine without WebView2 and with networking disabled still
requires validation. Treat this as a friends-and-family preview.

The app and Setup are not code-signed. The embedded runtime is signed by
Microsoft. Obtain the package from a trusted source; a matching checksum
checks file consistency but does not establish a publisher's identity.

GET THE INSTALLER THROUGH GIT
Install Git and Git LFS if needed:
  https://git-scm.com/downloads/win
  https://git-lfs.com/

In PowerShell:
  git lfs install
  git clone --branch codex/repo-housekeeping https://github.com/vanderjt/dnd_relations_db.git
  cd dnd_relations_db
  git lfs pull

Then run the Setup EXE in installer. GitHub's Download ZIP may contain only
an LFS pointer. A tiny file starting with "version https://git-lfs.github.com"
is not an executable; git lfs pull retrieves the actual package (about 228 MB).
Internet access is needed for the clone/download, not normal app use.

If already on the release branch, save or commit local source edits first:
  git pull --ff-only
  git lfs pull

Do not discard local work or switch branches blindly to update an installer.
A friend can instead give you the complete replacement Setup EXE directly.

UPDATE, UNINSTALL, OR REINSTALL
1. Back up important work and close Story Atlas.
2. Obtain the replacement release files, if a newer release has been published.
3. Double-click Manage Story Atlas.cmd in this folder.
4. Choose Install/update to replace the app without uninstalling it first.
5. Reopen using the installed desktop or Start Menu shortcut.

In-place updates can leave application files removed from a later release.
Choose Uninstall/reinstall for a clean replacement of installer-tracked app
files; separate stories and backups remain. Files you manually placed in the
app folder may remain because they are not tracked by the uninstaller.

The menu also offers Uninstall and Uninstall/reinstall. Reinstall validates
the replacement before removing a working installation. If uninstall is
cancelled or incomplete, reinstall must stop. The manager uses the registered
installation so custom app locations can be found.

You can also uninstall through Windows Settings > Apps > Story Atlas Preview,
or the Start Menu's Uninstall Story Atlas Preview shortcut.

The manager verifies the EXE's SHA-256 against release.json before installing.
Keep the installation-manager files in this folder together when copying them;
the Setup EXE alone can still be run directly. The adjacent .sha256 records
the same package checksum. The manager does not build source or download
updates. Its displayed version and source commit identify the selected release.

Use installed shortcuts for the packaged release. Launch Story Atlas.cmd at
the repository root prefers prepared source, then a local developer package,
then the registered installed copy, and reports its selection.

YOUR STORIES AND BACKUPS
The default per-user app installation directory is:
  %LOCALAPPDATA%\Programs\Story Atlas Preview
Default story data and backups are separate:
  %LOCALAPPDATA%\StoryAtlasPreview

Uninstall preserves this separate data, including edited examples. Use the
app's Back up story command to transfer work; copying the installer does not
copy personal stories. Restore backup as a copy creates a separate working
story rather than replacing the current one.

Source and installed copies share the default data root. Developers should
use a disposable --home directory and copied story files for testing.

GREYHAVEN AND EXAMPLES
Choose Try Greyhaven sample to create a fresh sample. Setup also places
Frankenstein, Dracula, and Cyberpunk: Edgerunners Season 1 examples in the
default Stories folder. Existing files with the same names are not overwritten.
Open story edits the chosen file directly; copy an example before experimenting
if you want to retain its original. Frankenstein and Edgerunners have embedded
offline portraits. Credits are in portrait-sources.json and inside the stories.

Legacy Tkinter .db stories and browser-prototype edits are not imported.
For editing, drafts, backups, and scope rules, read ../docs/USER_GUIDE.md.
