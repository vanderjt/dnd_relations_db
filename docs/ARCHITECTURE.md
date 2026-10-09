# Architecture and data safety

## Runtime boundaries

Story Atlas is one local desktop app with a web-rendered interface. The React
frontend is bundled into `preview/dist`; `preview_main.py` opens those assets
with pywebview. Windows selects WebView2 (`edgechromium`). Mac source launches
use pywebview's platform renderer. There is no supported standalone browser
storage mode or Tkinter runtime in this tree.

| Component | Responsibility |
| --- | --- |
| `preview/src/main.tsx` | Workspace navigation, editors, review/save, durable draft requests, close flow |
| `preview/src/Graph.tsx` | Relationship graph and labels |
| `preview/src/World.tsx` | Shared world-reference editor |
| `preview_main.py` / `PreviewBridge` | Native window, file dialogs, explicit command allowlist, asynchronous close handshake |
| `story_atlas/preview_worker.py` / `PreviewWorker` | One serialized worker that owns SQLite handles and active-story switching |
| `story_atlas/preview_store.py` / `PreviewStore` | Format validation, queries, mutations, revision checks, drafts, backups |
| `story_atlas/profile_history.py` | Resolve baseline and event-specific character fields |
| `story_atlas/relationship_semantics.py` | Normalize relationship direction and detect duplicates |

The UI calls `window.pywebview.api.command(name, args)`. The bridge permits only
known commands. Native file-dialog choices are passed to the worker; arbitrary
SQL and arbitrary filesystem operations are not exposed as UI commands.

## Story format

A `.atlas-preview` file is a SQLite database with these required identifiers:

- `PRAGMA application_id`: `0x53415056` (`SAPV`)
- `PRAGMA user_version`: `10002`

Opening requires an existing file (`mode=rw`), matching identifiers, and a
successful quick integrity check. The filename extension alone does not prove
that a file is supported. Unsupported versions and old `.db` files are rejected;
there is no legacy import or automatic format migration in this version.

The database stores chapters, sequenced story events, characters and profile
history, event participants, world entries, connections and connection history,
plus drafts, preferences, activity, and retry receipts. Portrait images and
example attribution travel inside the story rather than depending on remote
image URLs. Settings outside the story remember the last opened path.

Event IDs are stable identities; event sequence determines temporal ordering.
Character fields resolve from baseline values and dated decisions:

- `carry_forward` applies from its event until superseded.
- `event_only` applies at its event; afterward the continuing value resumes.
- An empty value is an explicit authored decision, not a missing update.

World references use stable entry IDs, allowing renames without rewriting
historical assignments. Relationship history follows the same event-scope
model; direction, inverse labels, and mutual semantics are validated.

## Write and recovery guarantees to preserve

1. **One owner per app instance.** The worker serializes database operations
   through a single-worker executor. UI callbacks do not share its connection.
2. **Atomic domain saves.** A write commits facts, revision, activity, retry
   receipt, and matching draft cleanup together, or rolls them all back.
3. **Stale-write protection.** A domain write supplies its expected revision.
   A conflicting revision is rejected while the draft remains available.
4. **Idempotent retry.** A request ID and content fingerprint identify a saved
   operation. Retrying the same request returns its receipt; reusing the ID for
   different content is rejected.
5. **Draft ownership.** A save may clear only the draft belonging to that editor.
   A replaced draft is not silently removed by an older editor.
6. **Safe new/open/restore.** New files are reserved exclusively. A candidate
   story is validated before replacing the active store. Restore copies the
   backup to a new story path rather than overwriting the original.
7. **SQLite-aware backup.** Backups use SQLite's backup API, including committed
   content that may still be in a WAL journal. Copying a live database file is
   not a substitute.
8. **Native-close handshake.** The native close callback returns promptly and
   requests frontend review asynchronously. Pending edits can be saved or kept
   as a draft before closing; renderer errors must not silently discard them.

Drafts are separate from committed story facts. A successful draft write means
pending work is on disk; it does not mean the user has approved its timeline
scope or saved those facts. UI errors and failed draft writes must remain visible.

## Data locations and development isolation

The default Windows data root is `%LOCALAPPDATA%\StoryAtlasPreview`; Mac uses
`~/Library/Application Support/StoryAtlasPreview`. Each contains `stories`,
`backups`, and `settings.json` as needed. The installed application lives in a
separate directory, normally `%LOCALAPPDATA%\Programs\Story Atlas Preview`.

`--home` overrides the data root. `--story` selects an existing file in place,
including one outside that root. Source, local frozen, and installed Windows
copies share the same default root, so development checks must opt into a
disposable root and copied fixtures.

Installation copies the authored examples only when the destination filename
is absent and marks them to survive uninstall. The installer must not remove
user stories or backups. Keep AppId `B1A827F6-93A7-4365-A494-D793125179DA` stable
for production upgrades; verification uses a different disposable identity.

## Build and verification boundaries

`preview/build.mjs` bundles frontend source and copies current assets.
`StoryAtlasPreview.spec` freezes the Python host plus built frontend, Greyhaven,
and user documentation. Inno Setup packages that output, examples, and the
signed Microsoft offline WebView2 installer.

A frontend build or unit-suite pass does not verify native rendering, Windows
registration, uninstall handoff, or a clean-machine runtime install. See the
[contributor checks](../CONTRIBUTING.md#checks),
[Windows verification layers](OFFLINE_INSTALLER.md#verification), and
[historical release record](RELEASE_HISTORY.md).
