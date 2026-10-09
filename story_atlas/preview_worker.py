"""One serialized worker owns creation, use, and closure of every SQLite handle."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import logging
import re
import uuid

from .preview_store import PreviewStore, Conflict


class PreviewWorker:
    """Route bridge requests through one thread and one active story store.

    SQLite connections are opened, used, and closed inside the executor. The
    caller waits for a result, but never takes ownership of a connection.
    """

    def __init__(self, home, sample_path):
        self.home = Path(home)
        self.sample_path = Path(sample_path)
        self._pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='preview-database'
        )
        self._store = None

    def call(self, command, args=None):
        """Queue a command behind earlier work and return its bridge response."""
        return self._pool.submit(self._dispatch, command, args or {}).result()

    def close(self):
        """Finish queued work and close SQLite on its owning thread."""
        self._pool.submit(self._close).result()
        self._pool.shutdown(wait=True)

    def _close(self):
        if self._store:
            self._store.close()
            self._store = None

    def _remember(self, path):
        """Replace the last-story setting only after its new file is complete."""
        self.home.mkdir(parents=True, exist_ok=True)
        temporary_settings = self.home / ('settings-' + uuid.uuid4().hex + '.tmp')
        temporary_settings.write_text(
            json.dumps({'last_story': str(path)}), encoding='utf-8'
        )
        temporary_settings.replace(self.home / 'settings.json')

    def _open(self, path):
        """Validate a candidate before replacing the currently open story."""
        candidate_store = PreviewStore(path)
        try:
            workspace = candidate_store.workspace()
            self._remember(candidate_store.path)
        except Exception:
            candidate_store.close()
            raise
        self._close()
        self._store = candidate_store
        return workspace

    def _dispatch(self, command, payload):
        """Execute an allowed operation and translate failures for the frontend."""
        try:
            if command == 'bootstrap':
                if self._store:
                    data = self._store.workspace()
                elif (self.home / 'settings.json').exists():
                    settings = json.loads(
                        (self.home / 'settings.json').read_text(encoding='utf-8')
                    )
                    data = self._open(settings['last_story'])
                else:
                    data = None
            elif command == 'open_story':
                data = self._open(payload['path'])
            elif command == 'new_story':
                destination_folder = self.home / 'stories'
                destination_folder.mkdir(parents=True, exist_ok=True)
                sample = (
                    json.loads(self.sample_path.read_text(encoding='utf-8'))
                    if payload.get('sample')
                    else None
                )
                title = 'Greyhaven' if sample else payload.get('title')
                safe_title = re.sub(
                    r'[<>:"/\\|?*\x00-\x1f]',
                    '-',
                    title if isinstance(title, str) else '',
                )[:80].strip(' .')
                path = destination_folder / (
                    f'Story-{safe_title}-{uuid.uuid4().hex[:8]}.atlas-preview'
                )
                created_store = PreviewStore.create(path, title, sample)
                created_store.close()
                data = self._open(path)
            elif command == 'restore':
                # Restore into a new story; leave the source backup untouched.
                backup_source = PreviewStore(payload['path'])
                try:
                    destination_folder = self.home / 'stories'
                    destination_folder.mkdir(parents=True, exist_ok=True)
                    restored_path = destination_folder / (
                        'restored-' + uuid.uuid4().hex + '.atlas-preview'
                    )
                    backup_source.backup(restored_path)
                finally:
                    backup_source.close()
                data = self._open(restored_path)
            else:
                if self._store is None:
                    raise ValueError('Create or open a preview story first.')
                store = self._store
                if command == 'workspace':
                    with store.connection:
                        store.connection.execute('BEGIN')
                        data = store.workspace(payload.get('event_id'))
                elif command == 'profile':
                    # Profile data and its revision must share one read snapshot.
                    with store.connection:
                        store.connection.execute('BEGIN')
                        data = dict(
                            **store.profile(
                                payload['character_id'], payload['event_id']
                            ),
                            revision=store.revision(),
                        )
                elif command == 'write':
                    result = store.write(**payload)
                    return {'ok': True, **result}
                elif command == 'save_draft':
                    data = store.save_draft(payload['key'], payload['payload'])
                elif command == 'get_draft':
                    data = store.get_draft(payload['key'])
                elif command == 'discard_draft':
                    data = store.discard_draft(payload['key'])
                elif command == 'preference':
                    data = store.save_preference(payload['key'], payload['payload'])
                elif command == 'backup':
                    destination_folder = self.home / 'backups'
                    destination_folder.mkdir(parents=True, exist_ok=True)
                    data = store.backup(
                        destination_folder
                        / (
                            store.path.stem
                            + '-'
                            + uuid.uuid4().hex[:10]
                            + '.atlas-preview'
                        )
                    )
                else:
                    raise ValueError('Unknown preview command.')
            return {
                'ok': True,
                'revision': self._store.revision() if self._store else None,
                'data': data,
            }
        except Conflict as error:
            return {
                'ok': False,
                'error': {'code': 'stale_revision', 'message': str(error)},
            }
        except (ValueError, KeyError, TypeError) as error:
            return {'ok': False, 'error': {'code': 'validation', 'message': str(error)}}
        except Exception as error:
            logging.exception('Preview command failed: %s', command)
            return {
                'ok': False,
                'error': {
                    'code': 'storage',
                    'message': f'Storage operation failed: {error}. Pending edits are kept; retry or open a backup.',
                },
            }
