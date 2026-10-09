# Release history and verification provenance

## Bundled Windows release: 0.1.1

The repository retains these original release artifacts:

- `installer/StoryAtlasPreview-0.1.1-Windows-x64-Offline-Setup.exe`
- The adjacent `.sha256` file
- `installer/release.json`

The [published release manifest](https://github.com/vanderjt/dnd_relations_db/blob/87c030a5bca898dc8406428d358d70b23656613b/installer/release.json)
identifies source commit
`d6376bc388169bfe636115be5ea2ef444ff875b8` and SHA-256
`35179351CDAE30EF00D438C3F94567170C21EAFFE2FC475FAB0370EF21C40AD1`.
The EXE uses Git LFS. A matching LFS pointer/manifest is metadata evidence;
checking the downloaded EXE's bytes is a separate step.

**This release predates the current source and repository cleanup.** Its version
and provenance must not be rewritten to claim it contains later changes.
Source fixes require a newly built, separately verified Windows release.

### Historical report: October 3, 2026

The release documentation recorded a production frontend build, 34 focused
Python tests, integrity and close/reopen checks for all three saved examples,
and an isolated installer lifecycle test using the frozen payload. It recorded
byte-for-byte preservation of a synthetic story, backup, and edited example,
cleanup of the test app/registration, and manager checksum validation.
The release included story scrolling and notification-dismissal fixes.
Source: [the published 0.1.1 verification record](https://github.com/vanderjt/dnd_relations_db/blob/87c030a5bca898dc8406428d358d70b23656613b/installer/README.txt#L94-L102).

Inspection of [the historical lifecycle helper](https://github.com/vanderjt/dnd_relations_db/blob/87c030a5bca898dc8406428d358d70b23656613b/tools/verify_installer_lifecycle.py)
shows that it reinstalled the same version/payload. It omitted WebView2
bootstrap and did not exercise the installation manager's full workflow or
prove an old-to-new payload upgrade. These are historical reported results,
not a new run against the current checkout.

## Earlier release: 0.1.0

The October 2, 2026 documentation recorded a production frontend build,
31 focused Python tests, saved-example integrity/timeline/reopen checks, and
installation on the development PC. Desktop and Start Menu shortcuts, packaged
Greyhaven, native window close, and reopening the saved sample were exercised
with disposable data. This is also historical evidence.
Source: [the October 2 example-enabled package record](https://github.com/vanderjt/dnd_relations_db/blob/295925befc415e91a82e95791e125d1ab2b653a2/installer/README.txt#L33-L40).

## Still requires platform evidence

Native Mac operation and clean-machine Windows installation with WebView2
absent and networking disabled are not established by the above reports.
Current unit, fixture, or non-Windows checks cannot fill those gaps. Treat the
bundled binary as a friends-and-family preview.

For a new release, record its own exact source commit, platform, test commands,
results, and remaining limits following the [build guide](OFFLINE_INSTALLER.md).
Do not carry historical pass counts forward as current test results.
