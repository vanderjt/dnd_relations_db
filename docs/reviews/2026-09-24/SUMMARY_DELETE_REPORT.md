# Character summary Delete — 0.14.2

The Simple character information panel has a Delete button immediately after
Connect in its bottom action bar. Confirmation names the character and counts all
attached connections. The existing transactional Trash service removes the exact
character and incoming, outgoing, mutual, and ended connections from active views.
The summary and selection clear after success. Cancel and write failure retain
the panel and data. Restoring the character restores its attached connections and
preserves relationship history.

Verification: 202 tests passed in 100.439 seconds, including two new real-Tk
tests for duplicate names, cascading deletion, history restoration, cancellation,
and rollback on an actual SQLite-triggered write failure. The source smoke and
final packaged smoke passed, including deletion/restoration in the Prometheus
example. The smoke's withdrawn graph needs ensure_current before inspecting its
rendered state; this test-harness refresh was added after the first smoke attempt.

Logs: build-verification/summary-delete-build.log,
summary-delete-focused.log, summary-delete-source-smoke.json,
summary-delete-final-package.log, and summary-delete-packaged-smoke.log.

The final package is dist/releases/0.14.2-final/StoryAtlas, selected by the workspace
launcher and used to rebuild dist/StoryAtlas-Windows-x64.zip. Build script DistPath
supports isolated release destinations to avoid Windows locks on running versions.
Source/package fingerprint: 39653c431cda355b81c60c938cff5f217e445c13772e87e0a414e51b82a42068.
Schema 12 and portable format 8 are unchanged.
