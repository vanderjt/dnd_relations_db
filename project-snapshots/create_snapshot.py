"""Create and fully verify a project restore archive without changing its sources."""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing
import hashlib
import json
import sqlite3
import tempfile
import time
import zipfile

root = Path(__file__).resolve().parents[1]
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
destination = root / 'project-snapshots' / f'StoryAtlas-0.18.0-before-visual-redesign-{stamp}'
destination.mkdir(exist_ok=False)
(destination / 'INCOMPLETE.txt').write_text('Snapshot is incomplete until verification finishes and manifest.json is written.', encoding='utf-8')
archive = destination / 'project.zip'
folders = ['.vscode', 'story_atlas', 'tests', 'tools', 'docs', 'examples', 'data', 'dist/StoryAtlas']
files = [p for p in root.iterdir() if p.is_file()]
for name in folders:
    files.extend(p for p in (root / name).rglob('*') if p.is_file())
files = sorted(p for p in files if '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo') and not p.name.endswith(('-wal', '-shm', '-journal')))
manifest = {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'source_root': str(root),
    'source_version': '0.18.0',
    'included_folders': folders,
    'included_root_files': True,
    'excluded': ['.build-env', 'build', 'build-verification', 'dist/releases', 'redundant dist ZIP archives', 'project-snapshots', '__pycache__ and compiled Python cache', 'SQLite sidecars (databases captured using SQLite backup)', 'external Documents/asset_packs', 'external AppData/Local/StoryAtlas (not accessible in this session)'],
    'files': [],
}
with tempfile.TemporaryDirectory(prefix='story-atlas-snapshot-') as temporary:
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for index, path in enumerate(files):
            relative = path.relative_to(root).as_posix()
            before = path.stat()
            is_sqlite = path.suffix.lower() in ('.db', '.sqlite', '.sqlite3')
            if is_sqlite:
                copy = Path(temporary) / f'{index}.db'
                start = time.monotonic()
                def progress(status, remaining, total):
                    if time.monotonic() - start > 30:
                        raise TimeoutError(f'Database remained busy: {relative}')
                with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as source:
                    with closing(sqlite3.connect(copy)) as target:
                        source.backup(target, pages=256, progress=progress)
                        result = target.execute('PRAGMA quick_check').fetchall()
                        if result != [('ok',)]:
                            raise RuntimeError(f'Database check failed: {relative}: {result}')
                content = copy.read_bytes()
            else:
                content = path.read_bytes()
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise RuntimeError(f'File changed while reading: {relative}')
            output.writestr('project/' + relative, content)
            manifest['files'].append({'path': relative, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(), 'capture': 'sqlite_backup_verified' if is_sqlite else 'exact_bytes'})
    with zipfile.ZipFile(archive) as check:
        for record in manifest['files']:
            content = check.read('project/' + record['path'])
            if hashlib.sha256(content).hexdigest() != record['sha256']:
                raise RuntimeError(f'Archive verification failed: {record["path"]}')

manifest['verification'] = 'Every archived file read back and SHA-256 verified; all SQLite snapshots passed quick_check.'
with archive.open('rb') as archive_stream:
    manifest['archive_sha256'] = hashlib.file_digest(archive_stream, 'sha256').hexdigest()
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(destination / 'project.zip.sha256').write_text(manifest['archive_sha256'] + '  project.zip\n', encoding='ascii')
(destination / 'RESTORE.md').write_text('''# Story Atlas 0.18.0 restore point

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
''', encoding='utf-8')
(destination / 'INCOMPLETE.txt').unlink()
print(json.dumps({'snapshot': str(destination), 'files': len(files), 'archive_bytes': archive.stat().st_size, 'sha256': manifest['archive_sha256'], 'verification': manifest['verification']}, indent=2))
