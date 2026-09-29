# Sol review follow-up fixes

This earlier corrective pass is followed by [the latest event-layout review](EVENT_LAYOUT_REVIEW.md),
which records the current package verification. Package hashes below are historical.

24 September 2026. All four findings from SOL_REVIEW.md are addressed.

- Search routes that leave the profile editor mounted explicitly reset its
  discarded buffer. Story switching retains its separate failed-open recovery
  behavior. New/existing profiles cannot later commit the discarded input.
- A dedicated chronology preview displays grouped Before/After lists, empty
  chapters, and Unassigned events in scrollable panes. Confirm/Cancel remain
  visible. Preview confirmation still uses the existing stale-check and atomic
  chapter transaction; stale changes require another review.
- Event-context history inspection selects the most recent state effective at
  or before the event, falling back to baseline. The view explicitly labels
  Present, Ended, or Not yet begun and recalculates its selection after corrections.
- Chapter/event IDs now join the existing per-story session state. All and
  Unassigned are retained; missing IDs fall back safely without navigating to
  a same-numbered record in a different story. This is session memory, not a
  newly promised across-restart selection setting.

## Validation

`tests/test_senior_fixes.py` adds actual-widget coverage for search Discard routes,
new/existing profiles and draft flushes, five historical timing cases, same-ID
story switches, and a 300-event preview in both themes with large text and visible
controls. Existing preview cancel/confirm/stale tests use the new confirmation
boundary. Existing failed-open recovery and batch-entry checks continue to pass.

The full build command ran **141 tests in 43.764 seconds: OK**:

```powershell
.\build_windows.ps1 -Python 'C:\ProgramData\anaconda3\python.exe'
```

Build output: `build-verification/senior-fixes-build.log`.
No database migration or user-story changes were needed. Native visual inspection,
physical DPI testing, and clean-machine checks remain outstanding.

## Rebuilt release

`tools/smoke_windows.ps1` exited successfully with `ok=true`, `frozen=true`,
version 0.9.0, schema 8, and Tcl/Tk 8.6.15. It used isolated test data and checked
startup/reopen, sample isolation, relationship batch reset, rendering/resources,
historical exports, portraits, backup/restore, settings, and version-7 migration.
Log: `build-verification/senior-fixes-smoke.log`.

Build fingerprint: `3b3ab5dc4abfdf948d715567bf1df6b18ff92505ba4add212ac3a0398738c2bc`.

| Artifact | SHA-256 |
|---|---|
| `dist/StoryAtlas/StoryAtlas.exe` | `C2C4421E0FEEE06E7F032B5A5524E44A49B047F85888A91B6FF2AF0E48BF8896` |
| `dist/StoryAtlas-Windows-x64.zip` | `21F421926046BB13E7F30F2FE57B61AA24FEBC16E34FBF4F56E71FF0516BBA6E` |

These artifacts supersede the hashes in the original implementation report.
This is a locally package-verified build, not clean-machine certification.
