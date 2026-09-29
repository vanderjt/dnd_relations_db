# Story Atlas 0.18.0 restore point

This snapshot preserves the source, current packaged Windows app, project-local
data and SQLite backups, examples, tests, tools, documentation (including the
asset visual roadmap), build specifications, dependency locks, and launchers.

## Restore safely

1. Close Story Atlas before switching versions or restoring a database.
2. Keep the current working folder as a separate backup.
3. Verify project.zip with Get-FileHash -Algorithm SHA256 and compare it with
   project.zip.sha256.
4. Extract project.zip into a NEW empty directory. Its project subfolder is the
   restored project. Do not overlay it onto newer source or database files.
5. Launch dist/StoryAtlas/StoryAtlas.exe for the preserved packaged app. For
   project-local data, pass --database with the absolute path to the extracted
   data/story_atlas.db. To isolate user settings and automatic story reopening,
   also pass --data-dir with an absolute path to a new writable data directory.
6. For source development, recreate the environment using environment.yml and
   the project README. The local .build-env environment is not archived.

The snapshot does not contain external Documents/asset_packs or the separate
AppData/Local/StoryAtlas story/settings directory. Those are not restored by
extracting this archive. The packaged app normally uses external AppData unless
you supply an isolated --data-dir, so launching it without those arguments may
open an existing external story.

Generated build intermediates, verification scratch files, old release folders,
redundant distribution ZIPs, and Python caches were excluded. manifest.json
records every included file, capture method, SHA-256 hash, and all exclusions.
SQLite databases were captured using the online backup API and checked for
integrity; they are consistent individual snapshots rather than raw file copies.

Verification: every archive entry was read back and compared with its recorded
SHA-256 checksum. This verifies preservation, not a new application test run.
