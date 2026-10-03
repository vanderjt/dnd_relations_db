STORY ATLAS PREVIEW 0.1.0 — WINDOWS OFFLINE INSTALLER

For friends installing from a flash drive
1. Copy StoryAtlasPreview-0.1.0-Windows-x64-Offline-Setup.exe to the drive.
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

Verification, October 2, 2026
Production frontend build and 31 focused Python tests passed. Saved examples
passed database integrity, timeline, and close/reopen checks. Setup installed
successfully on the development PC. Desktop/Start Menu shortcuts were created,
the packaged Greyhaven sample opened, X closed the app, and the installed copy
reopened that saved sample. Tests used disposable story data.
A clean PC without WebView2 and an installation with networking disabled have
not yet been tested. Treat this as a friends-and-family preview release.

The adjacent .sha256 file records the setup file's SHA-256 checksum.
