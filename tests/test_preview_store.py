"""Preview persistence boundaries on disposable files; no real story edits."""
import concurrent.futures
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid

from story_atlas.preview_store import PreviewStore, Conflict
from story_atlas.preview_worker import PreviewWorker


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.path = self.home / 'story.atlas-preview'
        self.store = PreviewStore.create(self.path, 'Test story')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def write(self, command, payload, **kwargs):
        return self.store.write(command, payload, kwargs.pop('expected_revision', self.store.revision()),
                                kwargs.pop('request_id', str(uuid.uuid4())), **kwargs)['data']

    def character(self):
        return self.write('create_character', {'name': 'Mira', 'summary': 'A witness', 'event_id': 1})['character_id']

    def event(self, title='Later', chapter_id=1):
        return self.write('save_event', {'title': title, 'chapter_id': chapter_id})['id']

    def change(self, char, event, value, scope='carry_forward', **kwargs):
        return self.write('save_profile', {'character_id': char, 'event_id': event,
            'changes': [{'field': 'location', 'value': value, 'scope': scope}]}, **kwargs)

    def test_temporal_values_provenance_and_reopen(self):
        char = self.character()
        events = [1, self.event(), self.event(), self.event()]
        self.change(char, events[0], 'Harbor')
        self.change(char, events[1], 'Inn', 'event_only')
        self.change(char, events[3], 'Castle')
        self.change(char, events[0], 'Quay')
        self.store.close()
        self.store = PreviewStore(self.path)
        self.assertEqual([self.store.profile(char, e)['values']['location'] for e in events], ['Quay', 'Inn', 'Quay', 'Castle'])
        self.assertEqual(self.store.profile(char, events[2])['sources']['location'], {'event_id': 1, 'scope': 'carry_forward'})
        self.change(char, events[1], '', 'event_only')
        self.assertEqual(self.store.profile(char, events[1])['values']['location'], '')
        self.assertEqual(self.store.profile(char, events[2])['values']['location'], 'Quay')

    def test_retry_receipts_and_reuse_rejected(self):
        p = {'name': 'Mira', 'event_id': 1}
        request = str(uuid.uuid4())
        first = self.write('create_character', p, request_id=request, expected_revision=0)
        repeated = self.write('create_character', p, request_id=request, expected_revision=0)
        self.assertEqual(first, repeated)
        self.assertEqual(len(self.store.workspace()['characters']), 1)
        with self.assertRaises(ValueError):
            self.write('create_character', dict(p, name='Changed'), request_id=request, expected_revision=0)

    def test_failed_write_rolls_back_facts_receipt_revision_audit_and_draft(self):
        char = self.character()
        key = f'profile:{char}:1'
        self.store.save_draft(key, {'version': 1, 'pending': 'Keep me'})
        before = self.store.revision()
        self.store.connection.execute("CREATE TEMP TRIGGER reject_audit BEFORE INSERT ON activity BEGIN SELECT RAISE(ABORT,'injected disk failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.change(char, 1, 'Inn', draft_key=key)
        self.assertEqual(self.store.revision(), before)
        self.assertEqual(self.store.profile(char, 1)['values']['location'], '')
        self.assertEqual(self.store.get_draft(key)['pending'], 'Keep me')
        self.assertEqual(self.store.connection.execute('SELECT COUNT(*) FROM receipts').fetchone()[0], 1)

    def test_stale_writer_preserves_draft(self):
        char = self.character()
        old = self.store.revision()
        other = PreviewStore(self.path)
        try:
            other.write('save_title', {'title': 'Another editor'}, old, str(uuid.uuid4()))
            self.store.save_draft(f'profile:{char}:1', {'version': 1, 'pending': 'Mine'})
            with self.assertRaises(Conflict):
                self.change(char, 1, 'Harbor', expected_revision=old)
            self.assertIsNotNone(self.store.get_draft(f'profile:{char}:1'))
        finally:
            other.close()

    def test_invalid_field_endpoint_scope_and_atomic_batch(self):
        char = self.character()
        for row in [{'field': 'bogus', 'value': '', 'scope': 'event_only'},
                    {'field': 'name', 'value': ' ', 'scope': 'carry_forward'},
                    {'field': 'age', 'value': 22, 'scope': 'event_only'},
                    {'field': 'age', 'value': '22', 'scope': 'forever'}]:
            with self.assertRaises(ValueError):
                self.write('save_profile', {'character_id': char, 'event_id': 1, 'changes': [
                    {'field': 'location', 'value': 'Rollback', 'scope': 'event_only'}, row]})
            self.assertEqual(self.store.profile(char, 1)['values']['location'], '')
        with self.assertRaises(ValueError):
            self.change(char, 999, 'Unknown')
        with self.assertRaises(ValueError):
            self.write('save_event', {'title': 'Invalid', 'chapter_id': 1, 'participants': [999]})

    def test_only_matching_draft_clears(self):
        char = self.character()
        later = self.event()
        for event in [1, later]:
            self.store.save_draft(f'profile:{char}:{event}', {'version': 1})
        self.change(char, 1, 'Quay', draft_key=f'profile:{char}:1')
        self.assertIsNone(self.store.get_draft(f'profile:{char}:1'))
        self.assertIsNotNone(self.store.get_draft(f'profile:{char}:{later}'))
        with self.assertRaises(ValueError):
            self.change(char, 1, 'Castle', draft_key=f'profile:{char}:{later}')
        self.assertEqual(self.store.profile(char, 1)['values']['location'], 'Quay')

    def test_chapters_participants_details_and_stable_event_ids(self):
        char = self.character()
        ch = self.write('save_chapter', {'title': 'Second chapter', 'summary': 'New land'})['id']
        second = self.event('Arrival', ch)
        self.change(char, second, 'New land')
        middle = self.event('Departure', 1)
        self.assertEqual([e['id'] for e in self.store.events()], [1, middle, second])
        self.write('save_event', {'id': second, 'title': 'Arrival renamed', 'chapter_id': ch,
            'status': 'Happened', 'purpose': 'Reveal a secret', 'summary': 'Reunion', 'notes': 'Author note', 'participants': [char]})
        self.store.close()
        self.store = PreviewStore(self.path)
        w = self.store.workspace(second)
        self.assertEqual(w['events'][-1]['purpose'], 'Reveal a secret')
        self.assertEqual(w['participants'], [{'event_id': second, 'character_id': char}])
        self.assertEqual(w['characters'][0]['location'], 'New land')
        self.assertEqual(w['events'][0]['status'], 'Planned')

    def test_backup_restores_all_tables_from_wal(self):
        char = self.character()
        self.change(char, 1, 'Harbor')
        target = self.character()
        self.write('save_connection', dict(source_id=char, target_id=target, kind='Friend', semantics='mutual', scope='event_only', event_id=1))
        self.write('save_event', {'id': 1, 'title': 'Beginning', 'chapter_id': 1, 'participants': [char, target]})
        self.store.save_draft('new', {'version': 1, 'text': 'pending'})
        self.store.save_preference('context', {'event_id': 1, 'character_id': char})
        self.store.connection.execute('PRAGMA journal_mode=WAL')
        copy = self.home / 'backup.atlas-preview'
        self.store.backup(copy)
        restored = PreviewStore(copy)
        try:
            names = [r[0] for r in self.store.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for name in names:
                self.assertEqual(self.store.rows(f'SELECT * FROM {name}'), restored.rows(f'SELECT * FROM {name}'))
            with self.assertRaises(FileExistsError):
                self.store.backup(copy)
        finally:
            restored.close()

    def test_replaced_draft_is_not_cleared_by_another_editor(self):
        char = self.character()
        key = f'profile:{char}:1'
        self.store.save_draft(key, {'version': 1, 'editor': {'draft_id': 'other-editor', 'pending': 'Keep'}})
        with self.assertRaises(Conflict):
            self.store.write('save_profile', {'character_id': char, 'event_id': 1, 'changes': [
                {'field': 'age', 'value': '22', 'scope': 'carry_forward'}]}, self.store.revision(), str(uuid.uuid4()), key, 'old-editor')
        self.assertEqual(self.store.get_draft(key)['editor']['pending'], 'Keep')
        self.assertEqual(self.store.profile(char, 1)['values']['age'], '')

    def test_missing_unsupported_and_legacy_are_unchanged(self):
        missing = self.home / 'missing.atlas-preview'
        with self.assertRaises(sqlite3.OperationalError):
            PreviewStore(missing)
        self.assertFalse(missing.exists())
        legacy_path = self.home / 'legacy.db'
        with sqlite3.connect(legacy_path) as legacy:
            legacy.execute('CREATE TABLE characters (id INTEGER PRIMARY KEY, name TEXT)')
        legacy.close()
        before = legacy_path.read_bytes()
        with self.assertRaises(ValueError):
            PreviewStore(legacy_path)
        self.assertEqual(before, legacy_path.read_bytes())
        with self.assertRaises(FileExistsError):
            PreviewStore.create(self.path, 'Overwrite')

    def test_worker_serializes_concurrent_requests_and_reopens(self):
        sample = Path(__file__).resolve().parents[1] / 'story_atlas/resources/greyhaven.json'
        worker = PreviewWorker(self.home / 'worker', sample)
        try:
            self.assertTrue(worker.call('open_story', {'path': str(self.path)})['ok'])
            request = {'command': 'create_character', 'payload': {'name': 'Only once', 'event_id': 1}, 'expected_revision': 0, 'request_id': str(uuid.uuid4())}
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(lambda _: worker.call('write', request), range(12)))
            self.assertTrue(all(r['ok'] for r in results))
            self.assertEqual(len(worker.call('workspace')['data']['characters']), 1)
        finally:
            worker.close()

        worker = PreviewWorker(self.home / 'worker', sample)
        try:
            self.assertEqual(len(worker.call('bootstrap')['data']['characters']), 1)
        finally:
            worker.close()

    def test_connection_scope_direction_duplicates_and_restart(self):
        a = self.character()
        b = self.write('create_character', {'name': 'Bryn', 'event_id': 1})['character_id']
        second, third, fourth = self.event(), self.event(), self.event()
        payload = dict(source_id=a, target_id=b, event_id=1, kind='Mentor', inverse_label='Student',
                       semantics='directional', notes='Teaching', scope='carry_forward')
        saved = self.write('save_connection', payload)
        ident = saved['id']
        with self.assertRaises(ValueError):
            self.write('save_connection', dict(payload, kind='Friend', inverse_label='', semantics='mutual'))
        with self.assertRaises(ValueError):
            self.write('save_connection', dict(payload, target_id=999))
        self.write('save_connection', dict(payload, id=ident, event_id=second, kind='Distrusts',
                   inverse_label='Distrusted by', scope='event_only'))
        self.write('save_connection', dict(payload, id=ident, event_id=fourth, kind='Employer', inverse_label='Employee'))
        self.store.close()
        self.store = PreviewStore(self.path)
        self.assertEqual([self.store.connections(e)[0]['kind'] for e in [1, second, third, fourth]],
                         ['Mentor', 'Distrusts', 'Mentor', 'Employer'])
        self.assertEqual(self.store.connections(third)[0]['inverse_label'], 'Student')
        self.write('save_connection', dict(payload, id=ident, event_id=second, kind='Friend', inverse_label='', semantics='mutual', scope='event_only'))
        self.assertEqual(self.store.connections(second)[0]['semantics'], 'mutual')
        self.assertEqual(self.store.connections(third)[0]['semantics'], 'directional')

    def test_world_identity_rename_scopes_drafts_event_and_backup(self):
        char = self.character()
        second, third = self.event(), self.event()
        first = self.write('save_world', {'category': 'location', 'name': 'Harbor', 'description': 'Old town'})['id']
        other = self.write('save_world', {'category': 'location', 'name': 'Inn'})['id']
        self.change(char, 1, f'@world:{first}')
        self.change(char, second, f'@world:{other}', 'event_only')
        self.write('save_event', {'id': second, 'title': 'Arrival', 'chapter_id': 1, 'location_id': first})
        self.store.save_draft(f'profile:{char}:{third}', {'version': 1, 'assignment': f'@world:{first}'})
        self.write('save_world', {'id': first, 'category': 'location', 'name': 'Old Harbor', 'description': 'Renamed'})
        self.assertEqual([self.store.profile(char, e)['values']['location'] for e in [1, second, third]], ['Old Harbor', 'Inn', 'Old Harbor'])
        self.assertEqual(self.store.events()[1]['location_id'], first)
        self.assertEqual(self.store.get_draft(f'profile:{char}:{third}')['assignment'], f'@world:{first}')
        with self.assertRaises(ValueError):
            self.change(char, third, '@world:99999')
        species = self.write('save_world', {'category': 'species', 'name': 'Human'})['id']
        with self.assertRaises(ValueError):
            self.change(char, third, f'@world:{species}')
        self.change(char, third, 'old harbor')
        self.assertEqual(len(self.store.rows("SELECT * FROM world_entries WHERE category='location'")), 3)
        copy = self.home / 'world-backup.atlas-preview'
        self.store.backup(copy)
        restored = PreviewStore(copy)
        try:
            self.assertEqual(restored.profile(char, 1)['raw_values']['location'], f'@world:{first}')
            self.assertEqual(restored.profile(char, 1)['values']['location'], 'Old Harbor')
        finally:
            restored.close()

    def test_sample_preserves_every_connection_snapshot_and_multiple_pairs(self):
        sample = json.loads((Path(__file__).resolve().parents[1] / 'story_atlas/resources/greyhaven.json').read_text(encoding='utf-8'))
        store = PreviewStore.create(self.home / 'sample.atlas-preview', 'Greyhaven', sample)
        try:
            keys = ('id', 'source_id', 'target_id', 'kind', 'semantics', 'inverse_label', 'notes', 'category')
            for event in sample['events']:
                expected = [{k: r.get(k, '') for k in keys} for r in sample['relationships'][str(event['id'])]]
                actual = [{k: r[k] for k in keys} for r in store.connections(event['id'])]
                self.assertEqual(sorted(expected, key=lambda r: r['id']), actual)
            pairs = [tuple(sorted((r['source_id'], r['target_id']))) for r in store.connections(1)]
            self.assertLess(len(set(pairs)), len(pairs))
        finally:
            store.close()

    def test_connection_failure_keeps_draft_and_world_failure_rolls_back(self):
        a, b = self.character(), self.character()
        key = 'connection:new:1'
        self.store.save_draft(key, {'version': 1})
        self.store.connection.execute("CREATE TEMP TRIGGER reject_new_activity BEFORE INSERT ON activity BEGIN SELECT RAISE(ABORT,'storage failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.write('save_connection', dict(source_id=a, target_id=b, kind='Friend', semantics='mutual', scope='carry_forward', event_id=1), draft_key=key)
        self.assertEqual(self.store.connections(1), [])
        self.assertIsNotNone(self.store.get_draft(key))
        with self.assertRaises(sqlite3.IntegrityError):
            self.write('save_world', {'category': 'species', 'name': 'Elf'})
        self.assertEqual(self.store.rows('SELECT * FROM world_entries'), [])

    def test_worker_backup_restore_missing_open_and_safe_filenames(self):
        sample = Path(__file__).resolve().parents[1] / 'story_atlas/resources/greyhaven.json'
        worker = PreviewWorker(self.home / 'worker', sample)
        try:
            opened = worker.call('new_story', {'title': 'CON: A / story?'})
            self.assertTrue(opened['ok'])
            original = Path(opened['data']['path'])
            self.assertTrue(original.name.startswith('Story-CON- A - story-'))
            backup = worker.call('backup')['data']['path']
            with self.assertLogs(level='ERROR'):
                self.assertFalse(worker.call('open_story', {'path': str(self.home / 'missing')})['ok'])
            self.assertEqual(worker.call('workspace')['data']['path'], str(original))
            restored = worker.call('restore', {'path': backup})
            self.assertTrue(restored['ok'])
            self.assertNotEqual(restored['data']['path'], str(original))
            self.assertNotEqual(restored['data']['path'], backup)
            self.assertEqual(restored['data']['events'], opened['data']['events'])
            self.assertTrue(original.exists())
        finally:
            worker.close()

    def test_bridge_picker_cancellation_and_command_allowlist(self):
        from preview_main import PreviewBridge
        sample = Path(__file__).resolve().parents[1] / 'story_atlas/resources/greyhaven.json'
        worker = PreviewWorker(self.home / 'cancel', sample)
        class Window:
            def create_file_dialog(self, *args, **kwargs):
                return None
        bridge = PreviewBridge(worker)
        bridge._window = Window()
        try:
            self.assertEqual(bridge.command('open_story')['data'], None)
            self.assertEqual(bridge.command('restore')['data'], None)
            self.assertFalse((self.home / 'cancel').exists())
            self.assertFalse(bridge.command('execute_sql', {'sql': 'DROP TABLE characters'})['ok'])
        finally:
            worker.close()

    def test_restore_without_an_open_story(self):
        sample = Path(__file__).resolve().parents[1] / 'story_atlas/resources/greyhaven.json'
        worker = PreviewWorker(self.home / 'fresh', sample)
        try:
            result = worker.call('restore', {'path': str(self.path)})
            self.assertTrue(result['ok'])
            self.assertNotEqual(result['data']['path'], str(self.path))
        finally:
            worker.close()


if __name__ == '__main__':
    unittest.main()
