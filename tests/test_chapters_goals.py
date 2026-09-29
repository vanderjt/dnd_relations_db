"""Chapter chronology and profile goals preserve story data through recovery."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_atlas.database import Database
from story_atlas.migrations import MIGRATIONS
from story_atlas.backup import snapshot, restore_backup, backup_directory
from story_atlas.imports import validate_payload, import_payload
from story_atlas.retrieval import search
from story_atlas.app import StoryAtlas
from story_atlas.event_view import EventDialog
from story_atlas.goals_view import CastGoalsDialog, ParticipantGoalsDialog


class ChapterStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = Database(self.folder / 'story.db')
        self.addCleanup(self.db.close)
        self.a = self.db.save_character(dict(name='Mira', goals='Find the lost ledger.\nLong term: heal the city.'))
        self.b = self.db.save_character(dict(name='Pip'))

    def chapter_story(self):
        c1 = self.db.chapters.save('The pact', 'Hope')
        c2 = self.db.chapters.save('Betrayal', 'Conflict')
        e1 = self.db.chapters.save_event('Meet', '', 1, [self.a], chapter_id=c1)
        e2 = self.db.chapters.save_event('Agree', '', 2, [self.a, self.b], chapter_id=c1)
        e3 = self.db.chapters.save_event('Break trust', '', 1, chapter_id=c2)
        rel = self.db.save_relationship(self.a, self.b, 'Ally', semantics='mutual', start_event=e2)
        self.db.history.write(rel, e3, dict(self.db.relationships()[0], kind='Enemy'))
        return c1, c2, e1, e2, e3, rel

    def test_chapters_order_events_and_history_stays_attached(self):
        c1, c2, e1, e2, e3, rel = self.chapter_story()
        self.assertEqual(self.db.relationships(e2)[0]['kind'], 'Ally')
        self.assertEqual(self.db.relationships()[0]['kind'], 'Enemy')
        self.db.chapters.move(c2, -1)
        self.assertEqual([row['id'] for row in self.db.events.list()], [e3, e1, e2])
        self.assertEqual(self.db.relationships()[0]['kind'], 'Ally')
        self.assertEqual({row['event_id'] for row in self.db.history.rows(rel)}, {e2, e3})
        self.db.events.move(e2, -1)
        self.assertEqual([row['id'] for row in self.db.events.list()], [e3, e2, e1])

    def test_chapter_preview_is_read_only_and_rejects_stale_confirmation(self):
        c1, c2, e1, e2, e3, rel = self.chapter_story()
        before = (self.db.chapters.list(), self.db.events.list(), self.db.activity())
        preview = self.db.chapters.preview_move(c2, -1)
        self.assertEqual([row[0] for row in preview['old_events']], [e1, e2, e3])
        self.assertEqual([row[0] for row in preview['new_events']], [e3, e1, e2])
        self.assertEqual(before, (self.db.chapters.list(), self.db.events.list(), self.db.activity()))
        self.db.chapters.save('Changed summary', ident=c1)
        fresh = (self.db.chapters.list(), self.db.events.list(), self.db.activity())
        with self.assertRaisesRegex(ValueError, 'since the preview'):
            self.db.chapters.move(c2, -1, expected=preview)
        self.assertEqual(fresh, (self.db.chapters.list(), self.db.events.list(), self.db.activity()))
        with self.assertRaisesRegex(ValueError, 'no neighbor'):
            self.db.chapters.preview_move(c1, -1)
        self.db.chapters.move(c2, -1, expected=self.db.chapters.preview_move(c2, -1))
        self.assertEqual(self.db.chapters.list()[0]['id'], c2)

    def test_real_timeline_conflict_rolls_back_chapter_move(self):
        c1 = self.db.chapters.save('Closure')
        c2 = self.db.chapters.save('Restart')
        e1 = self.db.chapters.save_event('Ends', '', 1, chapter_id=c1)
        e2 = self.db.chapters.save_event('Begins again', '', 1, chapter_id=c2)
        first = self.db.save_relationship(self.a, self.b, 'Friend', semantics='mutual')
        self.db.history.write(first, e1, self.db.relationship_records()[0], active=False)
        self.db.save_relationship(self.a, self.b, 'Friend', semantics='mutual', start_event=e2)
        before = (self.db.chapters.list(), self.db.events.list(), self.db.activity())
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.db.chapters.move(c2, -1, expected=self.db.chapters.preview_move(c2, -1))
        self.assertEqual(before, (self.db.chapters.list(), self.db.events.list(), self.db.activity()))

    def test_failed_reorder_or_move_rolls_back_every_write(self):
        c1, c2, e1, e2, e3, rel = self.chapter_story()
        before = self.db.events.list(), self.db.chapters.list(), self.db.events.participants(), self.db.activity()
        with patch.object(self.db.history, 'validate', side_effect=ValueError('Timeline conflict')):
            with self.assertRaises(ValueError):
                self.db.chapters.move(c2, -1)
            with self.assertRaises(ValueError):
                self.db.chapters.save_event('Changed', 'Changed', 1, [self.b], e1, c2)
        self.assertEqual(before, (self.db.events.list(), self.db.chapters.list(), self.db.events.participants(), self.db.activity()))

    def test_moving_event_to_other_chapter_inserts_at_position(self):
        c1, c2, e1, e2, e3, rel = self.chapter_story()
        self.db.chapters.save_event('Meet', '', 1, [self.a], e1, c2)
        self.assertEqual([row['id'] for row in self.db.events.list()], [e2, e1, e3])
        self.assertEqual(self.db.events.list()[1]['chapter_id'], c2)
        self.assertEqual(self.db.relationships()[0]['kind'], 'Enemy')

    def test_export_import_backup_and_goals_recovery(self):
        self.chapter_story()
        self.assertEqual(search(self.db, 'lost ledger')[0]['id'], self.a)
        duplicate = self.db.duplicate_character(self.a)
        self.assertEqual(next(r for r in self.db.characters() if r['id'] == duplicate)['goals'], self.db.characters()[0]['goals'])
        self.db.delete_character(self.a)
        self.db.trash.restore('character', self.a)
        self.db.drafts.save(self.a, dict(self.db.characters()[0], goals='Uncommitted ambition'))
        export = self.folder / 'story.json'
        self.db.export_json(export)
        payload = json.loads(export.read_text(encoding='utf-8'))
        imported = Database(import_payload(payload, self.folder / 'import.db'))
        self.addCleanup(imported.close)
        self.assertEqual(imported.chapters.list(), self.db.chapters.list())
        self.assertEqual(imported.events.list(), self.db.events.list())
        self.assertEqual(imported.characters(), self.db.characters())
        restored = Database(restore_backup(snapshot(self.db.connection, self.db.path), self.folder / 'restored.db'))
        self.addCleanup(restored.close)
        self.assertEqual(restored.chapters.list(), self.db.chapters.list())
        self.assertEqual(restored.events.list(), self.db.events.list())
        self.assertEqual(restored.characters(), self.db.characters())
        self.assertEqual(restored.drafts.list()[0]['values']['goals'], 'Uncommitted ambition')
        for mutation in ('missing', 'duplicate', 'chronology'):
            bad = copy.deepcopy(payload)
            if mutation == 'missing':
                bad['story_events'][0]['chapter_id'] = 999
            elif mutation == 'duplicate':
                bad['chapters'].append(bad['chapters'][0])
            else:
                bad['story_events'][0]['chapter_id'] = bad['chapters'][1]['id']
            with self.assertRaises(ValueError):
                import_payload(bad, self.folder / f'{mutation}.db')
            self.assertFalse((self.folder / f'{mutation}.db').exists())

    def test_v7_migration_keeps_existing_events_unassigned_and_backed_up(self):
        path = self.folder / 'legacy.db'
        con = sqlite3.connect(path)
        for migration in MIGRATIONS[:7]:
            migration(con)
        con.execute("INSERT INTO characters(id,name,notes) VALUES(1,'Old','Preserved')")
        con.execute("INSERT INTO story_events(id,title,sequence) VALUES(9,'Old scene',20)")
        con.execute('PRAGMA user_version=7')
        con.commit()
        con.close()
        upgraded = Database(path)
        self.addCleanup(upgraded.close)
        self.assertEqual(upgraded.chapters.list(), [])
        self.assertEqual(upgraded.events.list()[0], dict(id=9, title='Old scene', summary='', sequence=20, chapter_id=None))
        self.assertEqual(upgraded.characters()[0]['notes'], 'Preserved')
        self.assertEqual(upgraded.characters()[0]['goals'], '')
        self.assertEqual(len(list(backup_directory(path).glob('pre-migration-v7*.db'))), 1)


class ChapterUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = StoryAtlas(Path(self.temp.name) / 'story.db')
        self.addCleanup(self.cleanup)
        self.db = self.app.database

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_chapter_creation_event_filter_edit_and_goal_save(self):
        view = self.app.events
        dialog = view.new_chapter()
        dialog.name.set('First chapter')
        self.assertTrue(dialog.save())
        chapter = view.chapter_id
        dialog = view.edit()
        self.assertEqual(dialog.chapter.get(), chapter)
        dialog.title_value.set('First scene')
        self.assertTrue(dialog.save())
        self.assertEqual(len(view.rows), 1)
        row = next(iter(view.rows.values()))
        self.assertEqual(row['chapter_id'], chapter)
        dialog = EventDialog(view, self.db, self.app.refresh, row)
        dialog.title_value.set('Keep pending')
        dialog.sequence.set('0')
        with patch('story_atlas.event_view.messagebox.showerror'):
            self.assertFalse(dialog.save())
        self.assertEqual(dialog.title_value.get(), 'Keep pending')
        with patch('story_atlas.event_view.messagebox.askyesnocancel', return_value=False):
            dialog.close()
        char = self.app.characters
        char.fields['name'].set('Goal seeker')
        char.fields['goals'].insert('1.0', 'Recover the crown')
        self.assertTrue(char.save())
        char.overview.refresh(char.character_id)
        self.assertIn('Recover the crown', char.overview.goals.cget('text'))
        self.assertEqual(search(self.db, 'crown')[0]['id'], char.character_id)
        self.app.tabs.select(self.app.graph)
        self.app.update()
        self.assertTrue(any('First chapter / First scene' in label for label in self.app.graph.event_choices))

    def test_outline_empty_chapters_destination_and_exact_navigation(self):
        view = self.app.events
        self.assertEqual(view.workspace.panes(), (str(view.outline_frame), str(view.event_frame), str(view.detail)))
        self.assertEqual(view.tree['columns'], ('title',))
        first = self.db.chapters.save('Same', 'First summary')
        second = self.db.chapters.save('Same', 'Second summary')
        unassigned = self.db.chapters.save_event('Loose', '', 1)
        event = self.db.chapters.save_event('Scene', '', 1, chapter_id=first)
        self.app.refresh()
        self.assertFalse(view.outline.item(f'chapter:{first}', 'values')[0].startswith('1.'))
        self.assertEqual(view.outline.item(f'chapter:{second}', 'values')[0], f'Same (#{second})')
        self.assertEqual(view.outline.item('unassigned', 'values')[0], 'Unassigned')
        view.outline.selection_set(f'chapter:{second}')
        self.app.update()
        self.assertEqual(view.chapter_id, second)
        self.assertIn('Second summary', view.detail_text.get())
        self.assertTrue(view.reveal_event(event, self.db.path))
        self.assertEqual(view.chapter_id, first)
        self.assertEqual(view.tree.selection(), (str(event),))
        self.assertFalse(view.reveal_event(event, self.db.path.with_name('other.db')))
        self.assertFalse(view.reveal_event(99999, self.db.path))
        editor = view.edit_selected()
        editor.chapter.value.set(next(label for label, ident in editor.chapter.choices.items() if ident == second))
        editor.chapter_changed()
        self.assertTrue(editor.save())
        self.assertEqual(view.destination_target, (self.db.path, second, event))
        self.assertIn('destination', view.destination_button.cget('text'))
        view.open_destination()
        self.assertEqual(view.chapter_id, second)
        self.assertEqual(view.tree.selection(), (str(event),))
        self.assertEqual(self.db.events.list()[0]['id'], event)
        self.assertEqual(self.db.events.list()[-1]['id'], unassigned)

    def test_chapter_move_preview_cancel_and_confirm(self):
        view = self.app.events
        first = self.db.chapters.save('First')
        second = self.db.chapters.save('Second')
        self.db.chapters.save_event('One', '', 1, chapter_id=first)
        self.db.chapters.save_event('Two', '', 1, chapter_id=second)
        self.app.refresh()
        view.reveal_chapter(second, self.db.path)
        with patch('story_atlas.event_view.confirm_preview', return_value=False) as confirm:
            view.move_chapter(-1)
        self.assertIn('old_events', confirm.call_args.args[1])
        self.assertEqual(self.db.chapters.list()[0]['id'], first)
        with patch('story_atlas.event_view.confirm_preview', return_value=True):
            view.move_chapter(-1)
        self.assertEqual(self.db.chapters.list()[0]['id'], second)
        self.assertEqual(view.chapter_id, second)

    def test_stale_chapter_preview_requires_a_second_confirmation(self):
        view = self.app.events
        first = self.db.chapters.save('First')
        second = self.db.chapters.save('Second')
        self.app.refresh()
        view.reveal_chapter(second, self.db.path)
        calls = []
        def confirm(*args, **kwargs):
            calls.append(args[1])
            if len(calls) == 1:
                self.db.chapters.save('Updated', ident=first)
                return True
            return False
        with patch('story_atlas.event_view.confirm_preview', side_effect=confirm), patch(
                'story_atlas.event_view.messagebox.showinfo'):
            view.move_chapter(-1)
        self.assertEqual(len(calls), 2)
        self.assertIn((first, 'Updated'), calls[1]['old_chapters'])
        self.assertEqual(self.db.chapters.list()[0]['id'], first)

    def test_cast_goals_and_event_participant_inspection_preserve_drafts(self):
        goals = 'Find Ω\nHelp the city without erasing this line.'
        first = self.db.save_character(dict(name='Same', goals=goals, summary='A saved profile'))
        second = self.db.save_character(dict(name='Same', goals=''))
        self.app.refresh()
        cast = CastGoalsDialog(self.app.characters, self.db)
        contents = cast.content.get('1.0', 'end-1c')
        self.assertIn(f'Same (#{first})\n{goals}', contents)
        self.assertIn(f'Same (#{second})\nNo saved goals.', contents)
        cast.close()
        for existing in (False, True):
            event_id = self.db.chapters.save_event('Saved', '', 1, [first]) if existing else None
            self.app.refresh()
            row = next((item for item in self.db.events.list() if item['id'] == event_id), None)
            editor = EventDialog(self.app.events, self.db, self.app.refresh, row)
            editor.title_value.set('Uncommitted event Ω')
            editor.summary.insert('1.0', 'Uncommitted summary')
            if first not in editor.participants.selected:
                editor.participants.buttons[first].invoke()
            before = editor.values()
            editor.participants.inspect(first)
            self.assertIn(goals, editor.participants.preview.get('1.0', 'end-1c'))
            self.app.update()
            self.assertEqual(editor.values(), before)
            self.assertEqual(editor.grab_current(), editor)
            self.assertEqual(next(row for row in self.db.characters() if row['id'] == first)['goals'], goals)
            with patch('story_atlas.event_view.messagebox.askyesnocancel', return_value=False):
                editor.close()
            if existing:
                break
        self.db.delete_character(second)
        editor = EventDialog(self.app.events, self.db, self.app.refresh)
        self.assertNotIn(second, editor.participants.rows)
        with patch('story_atlas.event_view.messagebox.askyesnocancel', return_value=False):
            editor.close()
