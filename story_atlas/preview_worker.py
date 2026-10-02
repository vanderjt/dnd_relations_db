"""One serialized worker owns creation, use, and closure of every SQLite handle."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import logging
import re
import uuid

from .preview_store import PreviewStore, Conflict


class PreviewWorker:
    def __init__(self, home, sample_path):
        self.home = Path(home)
        self.sample_path = Path(sample_path)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='preview-database')
        self._store = None

    def call(self, command, args=None):
        return self._pool.submit(self._dispatch, command, args or {}).result()

    def close(self):
        self._pool.submit(self._close).result()
        self._pool.shutdown(wait=True)

    def _close(self):
        if self._store:
            self._store.close()
            self._store = None

    def _remember(self, path):
        self.home.mkdir(parents=True, exist_ok=True)
        temporary = self.home / ('settings-' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps({'last_story': str(path)}), encoding='utf-8')
        temporary.replace(self.home / 'settings.json')

    def _open(self, path):
        candidate = PreviewStore(path)
        try:
            data = candidate.workspace()
            self._remember(candidate.path)
        except Exception:
            candidate.close()
            raise
        self._close()
        self._store = candidate
        return data

    def _dispatch(self, command, p):
        try:
            if command == 'bootstrap':
                if self._store:
                    data = self._store.workspace()
                elif (self.home / 'settings.json').exists():
                    settings = json.loads((self.home / 'settings.json').read_text(encoding='utf-8'))
                    data = self._open(settings['last_story'])
                else:
                    data = None
            elif command == 'open_story':
                data = self._open(p['path'])
            elif command == 'new_story':
                folder = self.home / 'stories'
                folder.mkdir(parents=True, exist_ok=True)
                sample = json.loads(self.sample_path.read_text(encoding='utf-8')) if p.get('sample') else None
                title = 'Greyhaven' if sample else p.get('title')
                safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '-', title if isinstance(title, str) else '')[:80].strip(' .')
                path = folder / (f'Story-{safe}-{uuid.uuid4().hex[:8]}.atlas-preview')
                created = PreviewStore.create(path, title, sample)
                created.close()
                data = self._open(path)
            elif command == 'restore':
                source = PreviewStore(p['path'])
                try:
                    folder = self.home / 'stories'
                    folder.mkdir(parents=True, exist_ok=True)
                    restored = folder / ('restored-' + uuid.uuid4().hex + '.atlas-preview')
                    source.backup(restored)
                finally:
                    source.close()
                data = self._open(restored)
            else:
                if self._store is None:
                    raise ValueError('Create or open a preview story first.')
                s = self._store
                if command == 'workspace':
                    with s.connection:
                        s.connection.execute('BEGIN')
                        data = s.workspace(p.get('event_id'))
                elif command == 'profile':
                    with s.connection:
                        s.connection.execute('BEGIN')
                        data = dict(**s.profile(p['character_id'], p['event_id']), revision=s.revision())
                elif command == 'write':
                    result = s.write(**p)
                    return {'ok': True, **result}
                elif command == 'save_draft':
                    data = s.save_draft(p['key'], p['payload'])
                elif command == 'get_draft':
                    data = s.get_draft(p['key'])
                elif command == 'discard_draft':
                    data = s.discard_draft(p['key'])
                elif command == 'preference':
                    data = s.save_preference(p['key'], p['payload'])
                elif command == 'backup':
                    folder = self.home / 'backups'
                    folder.mkdir(parents=True, exist_ok=True)
                    data = s.backup(folder / (s.path.stem + '-' + uuid.uuid4().hex[:10] + '.atlas-preview'))
                else:
                    raise ValueError('Unknown preview command.')
            return {'ok': True, 'revision': self._store.revision() if self._store else None, 'data': data}
        except Conflict as error:
            return {'ok': False, 'error': {'code': 'stale_revision', 'message': str(error)}}
        except (ValueError, KeyError, TypeError) as error:
            return {'ok': False, 'error': {'code': 'validation', 'message': str(error)}}
        except Exception as error:
            logging.exception('Preview command failed: %s', command)
            return {'ok': False, 'error': {'code': 'storage', 'message': f'Storage operation failed: {error}. Pending edits are kept; retry or open a backup.'}}
