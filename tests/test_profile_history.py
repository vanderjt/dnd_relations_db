"""Web-profile foundation acceptance on disposable SQLite files only."""
import tempfile
import unittest
from pathlib import Path
import sqlite3

from story_atlas.database import Database
from story_atlas.profile_history import ProfileHistory, ProfileConflict


class ProfileHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'disposable.db'
        self.db = Database(self.path)
        self.character = self.db.save_character({'name': 'Mira', 'location': 'Harbor'})
        self.events = [self.db.events.save(f'Event {i}', '', i) for i in range(1, 5)]
        self.service = ProfileHistory(self.db)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def read(self, index):
        return self.service.get_profile(self.character, self.events[index])

    def save(self, index, field, value, scope='carry_forward'):
        return self.service.save_profile(self.character, self.events[index],
            [{'field': field, 'value': value, 'scope': scope}], self.read(index)['revision'])

    def test_create_edit_close_reopen(self):
        self.save(1, 'language', 'Old Harbor')
        self.save(1, 'age', '22')
        self.db.close()
        self.db = Database(self.path)
        self.service = ProfileHistory(self.db)
        self.assertEqual(self.read(2)['values']['language'], 'Old Harbor')
        self.assertEqual(self.read(2)['values']['age'], '22')
        self.assertEqual(self.read(0)['values']['age'], '')
        self.assertEqual(self.db.characters()[0]['location'], 'Harbor')
        self.assertEqual(self.read(2)['sources']['age'],
                         {'event_id': self.events[1], 'scope': 'carry_forward'})

    def test_event_only_resumes_continuing_state_and_later_decisions_win(self):
        self.save(0, 'location', 'Quay')
        self.save(1, 'location', 'Inn', 'event_only')
        self.save(3, 'location', 'Castle')
        self.save(0, 'location', 'Docks')
        self.assertEqual([self.read(i)['values']['location'] for i in range(4)],
                         ['Docks', 'Inn', 'Docks', 'Castle'])
        self.save(1, 'location', '', 'event_only')
        self.assertEqual(self.read(1)['values']['location'], '')
        self.assertEqual(self.read(2)['values']['location'], 'Docks')

    def test_atomic_save_clears_only_its_draft_and_logs_once(self):
        key = f'web-profile:{self.character}:{self.events[1]}'
        other = f'web-profile:{self.character}:{self.events[2]}'
        self.db.drafts.save_task(key, {'age': '22'})
        self.db.drafts.save_task(other, {'notes': 'Keep'})
        before = len(self.db.activity())
        result = self.service.save_profile(self.character, self.events[1], [
            {'field': 'age', 'value': '22', 'scope': 'carry_forward'},
            {'field': 'belief', 'value': 'The tide', 'scope': 'event_only'},
        ], self.read(1)['revision'])
        self.assertEqual(result['values']['belief'], 'The tide')
        self.assertEqual(len(self.db.activity()), before + 1)
        self.assertEqual([r['key'] for r in self.db.drafts.list()], [other])

    def test_logging_failure_rolls_back_edits_and_draft_cleanup(self):
        key = f'web-profile:{self.character}:{self.events[0]}'
        self.db.drafts.save_task(key, {'age': '22'})
        self.db.connection.execute("""CREATE TEMP TRIGGER reject_profile_log BEFORE INSERT ON activity
            WHEN NEW.action='Event profile saved' BEGIN SELECT RAISE(ABORT,'simulated failure'); END""")
        before = self.read(0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.save(0, 'age', '22')
        self.assertEqual(self.read(0), before)
        self.assertEqual(self.db.drafts.list()[0]['key'], key)

    def test_stale_writer_is_rejected_including_legacy_edits(self):
        revision = self.read(0)['revision']
        second = Database(self.path)
        try:
            other = ProfileHistory(second)
            other.save_profile(self.character, self.events[0],
                [{'field': 'title', 'value': 'Warden', 'scope': 'carry_forward'}], revision)
            with self.assertRaises(ProfileConflict):
                self.service.save_profile(self.character, self.events[0],
                    [{'field': 'title', 'value': 'Captain', 'scope': 'carry_forward'}], revision)
            fresh = self.read(0)['revision']
            second.save_character({'name': 'Mira renamed'}, self.character)
            with self.assertRaises(ProfileConflict):
                self.service.save_profile(self.character, self.events[0], [], fresh)
        finally:
            second.close()

    def test_invalid_batch_writes_nothing(self):
        before = self.read(0)
        bad = [
            {'field': 'age', 'value': '22', 'scope': 'carry_forward'},
            {'field': 'name', 'value': ' ', 'scope': 'event_only'},
        ]
        with self.assertRaises(ValueError):
            self.service.save_profile(self.character, self.events[0], bad, before['revision'])
        self.assertEqual(self.read(0), before)
        for field, value, scope in [('unknown', '', 'event_only'), ('age', 22, 'event_only'),
                                    ('age', '22', 'forever')]:
            with self.assertRaises(ValueError):
                self.save(0, field, value, scope)
        with self.assertRaises(ValueError):
            self.service.get_profile(self.character, 9999)
        with self.assertRaises(ValueError):
            self.service.get_profile(9999, self.events[0])

    def test_reordering_uses_ids_not_position(self):
        self.save(1, 'age', '22', 'event_only')
        before = self.read(1)['revision']
        with self.db.connection:
            self.db.connection.execute('UPDATE story_events SET sequence=99 WHERE id=?', (self.events[0],))
            self.db.connection.execute('UPDATE story_events SET sequence=1 WHERE id=?', (self.events[1],))
            self.db.connection.execute('UPDATE story_events SET sequence=2 WHERE id=?', (self.events[0],))
        self.assertEqual(self.read(1)['values']['age'], '22')
        self.assertEqual(self.read(0)['values']['age'], '')
        self.assertNotEqual(before, self.read(1)['revision'])

    def test_schema_is_opt_in_and_does_not_change_migration_version(self):
        from story_atlas.migrations import CURRENT_VERSION
        self.assertEqual(self.db.connection.execute('PRAGMA user_version').fetchone()[0], CURRENT_VERSION)
        self.assertEqual(self.db.connection.execute('PRAGMA foreign_key_check').fetchall(), [])
        other = Database(Path(self.temp.name) / 'legacy.db')
        try:
            self.assertIsNone(other.connection.execute(
                "SELECT name FROM sqlite_master WHERE name='web_profile_history'").fetchone())
        finally:
            other.close()


if __name__ == '__main__':
    unittest.main()
