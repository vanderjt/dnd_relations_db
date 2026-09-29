"""Regression coverage for progressive tasks, classification and crash drafts."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_simple_mode as baseline
from story_atlas.database import Database
from story_atlas.story_setup import StorySetup, story_filename, available_path
from story_atlas.classification import CLASSIFICATIONS, COLORS
from story_atlas.imports import read_export, import_payload
from story_atlas.migrations import MIGRATIONS
from story_atlas.suggestions import choices
from story_atlas.simple_batch import BatchPane
from story_atlas.simple_event import EventPane
from story_atlas.simple_summary import CharacterSummary
from story_atlas.recent_undo import RecentCreation


class StorageTests(unittest.TestCase):
    def test_windows_filenames_and_collisions(self):
        for title in ('CON', 'nul.txt', 'COM1', 'LPT9'):
            self.assertTrue(story_filename(title).startswith('_'))
        self.assertEqual(story_filename('The: Broken/Crown?'), 'The_ Broken_Crown_.db')
        self.assertEqual(story_filename('  ... '), 'Untitled story.db')
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / 'Crown.db'
            first.touch()
            self.assertEqual(available_path(directory, 'Crown.db').name, 'Crown (2).db')
            (Path(directory) / 'Crown (2).db').touch()
            self.assertEqual(available_path(directory, 'Crown.db').name, 'Crown (3).db')

    def test_v9_migration_and_classification_roundtrips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'legacy.db'
            connection = sqlite3.connect(path)
            for migration in MIGRATIONS[:9]:
                migration(connection)
            connection.execute("INSERT INTO characters(name,narrative_role,role) VALUES ('Old','antagonist','Healer')")
            connection.execute('PRAGMA user_version=9')
            connection.commit()
            connection.close()
            db = Database(path)
            try:
                row = db.characters()[0]
                self.assertEqual((row['classification'], row['narrative_role'], row['role']), ('Neutral', 'antagonist', 'Healer'))
                self.assertTrue(list(path.parent.rglob('*pre-migration-v9*.db')))
                for label in CLASSIFICATIONS:
                    db.save_character(dict(name=label, classification=label))
                duplicate = db.duplicate_character(db.characters()[0]['id'])
                db.delete_character(duplicate)
                db.trash.restore('character', duplicate)
                output = path.with_suffix('.json')
                db.export_json(output)
                self.assertEqual(json.loads(output.read_text())['format_version'], 9)
                imported = Database(import_payload(read_export(output), path.parent / 'copy.db'))
                self.assertEqual(db.characters(), imported.characters())
                imported.close()
                self.assertEqual(len(set(COLORS.values())), 5)
                with self.assertRaises(ValueError):
                    db.save_character(dict(name='Bad', classification='Enemy'))
            finally:
                db.close()


class UITests(unittest.TestCase):
    setUp = baseline.SimpleUITests.setUp
    cleanup = baseline.SimpleUITests.cleanup
    cast = baseline.SimpleUITests.cast

    def test_story_default_no_picker_custom_and_cancel(self):
        folder = Path(self.temp.name)
        results = []
        setup = StorySetup(self.app, folder, results.append)
        setup.fields[0].set('Broken: Crown')
        with patch('story_atlas.story_setup.filedialog.asksaveasfilename') as picker:
            setup.save()
            picker.assert_not_called()
        self.assertEqual(results[0].name, 'Broken_ Crown.db')
        setup = StorySetup(self.app, folder, results.append)
        setup.fields[0].set('Broken: Crown')
        self.assertEqual(setup.path.name, 'Broken_ Crown (2).db')
        original = setup.path
        with patch('story_atlas.story_setup.filedialog.asksaveasfilename', return_value=''):
            setup.change_location()
        self.assertEqual(setup.path, original)
        with patch('story_atlas.story_setup.filedialog.asksaveasfilename', return_value=str(folder / 'Elsewhere.db')) as picker:
            setup.change_location()
            self.assertEqual(picker.call_args.kwargs['initialfile'], 'Broken_ Crown.db')
        setup.destroy()
        self.assertFalse((folder / 'Elsewhere.db').exists())

    def test_collapsed_input_suggestions_tags_and_save_state(self):
        self.db.save_character(dict(name='Existing', role='sCHolar', tags='My tag'))
        self.ws.new_character()
        task = self.ws.task
        self.assertTrue(all(not section[2] for section in task.editor.collapsible_sections.values()))
        self.assertEqual(task.fields['role'].get(), '')
        self.assertIn('Scholar', choices(self.db, 'role'))
        self.assertIn('sCHolar', choices(self.db, 'role'))
        task.editor.toggle_section('goals')
        task.fields['goals'].insert('1.0', 'Protect the city')
        task.editor.toggle_section('goals')
        self.assertEqual(task.fields['goals'].get('1.0', 'end-1c'), 'Protect the city')
        tags = task.editor.field_widgets['tags']
        for label in ('My tag', 'Witness'):
            tags.pending.set(label)
            tags.add()
        self.assertEqual(task.fields['tags'].get(), 'My tag, Witness')
        tags.remove('Witness')
        self.assertEqual(task.fields['tags'].get(), 'My tag')
        task.fields['name'].set('Hero')
        task.fields['character_type'].set('Player Ally')
        self.assertTrue(task.save())
        self.assertIn('disabled', task.save_button.state())
        task.fields['name'].set('Edited')
        self.assertNotIn('disabled', task.save_button.state())
        state = task.editor.collapsible_sections.copy()
        self.app.refresh()
        self.assertEqual(task.editor.collapsible_sections, state)
        self.assertEqual(self.errors, [])

    def test_summary_connect_guided_reset_and_nested_creation(self):
        a, b, c = self.cast()
        before = self.db.activity()
        self.ws.inspect_character(a)
        self.assertIsInstance(self.ws.task, CharacterSummary)
        self.assertTrue(self.ws.can_leave())
        self.assertEqual(self.db.activity(), before)
        self.ws.connect(a)
        task = self.ws.task
        for ident in (b, c):
            self.ws.choose_node(ident)
        self.assertEqual(task.targets, [b, c])
        self.ws.set_source(c)
        self.assertEqual(task.names[task.variables['source'].get()], c)
        self.assertEqual(task.targets, [a, b])
        task.variables['kind'].set('Employer')
        task.variables['semantics'].set('Directional')
        task.variables['inverse_label'].set('Employee')
        task.notes.insert('1.0', 'Keep this')
        nested = task.create_character('target')
        nested.name.set('New witness')
        self.assertTrue(nested.save())
        self.assertEqual(task.notes.get('1.0', 'end-1c'), 'Keep this')
        self.assertFalse(task.save())
        self.assertTrue(task.save())
        self.app.update()
        self.assertEqual(len(self.db.relationship_records()), 3)
        self.assertEqual(task.targets, [])
        self.assertTrue(all(not task.variables[key].get() for key in ('source', 'target', 'kind', 'inverse_label')))
        self.assertEqual(task.variables['semantics'].get(), 'Mutual')
        self.assertEqual(task.notes.get('1.0', 'end-1c'), '')
        self.assertEqual(self.ws.ordered.ids, [])
        self.assertIs(self.app.focus_get(), task.boxes['source'].search)
        self.assertEqual(self.db.drafts.list(), [])
        self.assertEqual(self.errors, [])

    def test_relationship_draft_restart_missing_reference_and_isolation(self):
        a, b, _ = self.cast()
        self.ws.connect(a)
        task = self.ws.task
        self.ws.choose_node(b)
        task.variables['kind'].set('Friend')
        task.notes.insert('1.0', 'Uncommitted notes')
        task.draft.flush()
        path = self.db.path
        reopened = Database(path)
        payload = reopened.drafts.list()[0]['values']
        reopened.close()
        other = Database(path.parent / 'other.db')
        self.assertEqual(other.drafts.list(), [])
        other.close()
        self.ws.remove_task()
        self.db.delete_character(b)
        task = self.ws.mount(lambda: BatchPane(self.ws.host, self.ws, payload))
        self.assertEqual(task.notes.get('1.0', 'end-1c'), 'Uncommitted notes')
        self.assertFalse(task.save())
        self.assertIn('missing', task.error.get().lower())
        self.assertEqual(task.targets, [b])
        self.assertEqual(self.db.relationship_records(), [])

    def test_event_draft_missing_participant_and_atomic_clear(self):
        a, _, _ = self.cast()
        self.ws.continue_event()
        task = self.ws.task
        self.assertIsInstance(task, EventPane)
        self.assertEqual(task.chapters[task.chapter.get()], self.db.events.list()[0]['chapter_id'])
        self.assertTrue(task.title.get())
        task.summary.insert('1.0', 'Draft scene')
        task.participants.selected.add(a)
        task.draft.flush()
        payload = self.db.drafts.list()[0]['values']
        self.ws.remove_task()
        self.db.delete_character(a)
        task = self.ws.mount(lambda: EventPane(self.ws.host, self.ws, recovered=payload))
        self.assertFalse(task.save())
        self.assertEqual(task.missing_participants, {a})
        task.exclude_missing()
        self.assertTrue(task.save())
        self.assertEqual(self.db.drafts.list(), [])
        self.assertEqual(self.db.events.list()[-1]['summary'], 'Draft scene')

    def test_undo_refuses_subsequent_edits_and_trash_restore(self):
        ident = self.db.save_character(dict(name='New', classification='NPC Ally'))
        undo = RecentCreation(self.db, ident)
        undo.undo()
        self.db.trash.restore('character', ident)
        self.assertEqual(self.db.characters()[0]['classification'], 'NPC Ally')
        undo = RecentCreation(self.db, ident)
        self.db.save_character(dict(name='Changed'), ident)
        with self.assertRaisesRegex(ValueError, 'Later changes'):
            undo.undo()
        self.assertEqual(self.db.characters()[0]['name'], 'Changed')

    def test_state_draft_recovers_exact_ended_correction(self):
        from story_atlas.simple_state import recover_state
        a, b, _ = self.cast()
        rel = self.db.save_relationship(a, b, 'Friend')
        self.db.history.write(rel, self.first, dict(source_id=a, target_id=b, kind='Enemy', semantics='directional', inverse_label='Opponent'), False)
        self.ws.state_task(rel, True)
        task = self.ws.task
        task.notes.insert('1.0', 'Recovered correction')
        task.draft.flush()
        payload = self.db.drafts.list()[0]['values']
        self.ws.remove_task()
        task = recover_state(self.ws, payload)
        self.assertEqual(task.variables['kind'].get(), 'Enemy')
        self.assertEqual(task.variables['presence'].get(), 'Ended')
        self.assertFalse(task.save())
        self.assertTrue(task.save())
        row = self.db.history.rows(rel)[0]
        self.assertEqual((row['kind'], row['active'], row['notes']), ('Enemy', 0, 'Recovered correction'))
        self.assertEqual(self.db.drafts.list(), [])

    def test_starting_character_cannot_be_its_own_target(self):
        a, _, _ = self.cast()
        self.ws.connect(a)
        task = self.ws.task
        self.assertEqual(task.names[task.variables['source'].get()], a)
        self.ws.choose_node(a)
        self.assertEqual(self.ws.ordered.ids, [a])
        self.assertEqual(task.variables['source'].get(), task.label(a))
        self.assertEqual(task.targets, [])

    def test_recovery_center_opens_simple_draft_from_advanced(self):
        from story_atlas.recovery import RecoveryDialog
        self.ws.new_event()
        self.ws.task.title.set('Recover from Advanced')
        self.ws.task.draft.flush()
        self.ws.remove_task()
        self.app.mode.set('Advanced')
        self.assertTrue(self.app.switch_mode())
        dialog = RecoveryDialog(self.app)
        index = next(i for i, row in enumerate(dialog.draft_items) if row['key'] == 'task:event:new')
        dialog.drafts.selection_set(str(index))
        dialog.recover_draft()
        self.assertEqual(self.app.mode.get(), 'Simple')
        self.assertEqual(self.ws.task.title.get(), 'Recover from Advanced')
        self.assertEqual(len(self.db.events.list()), 1)

    def test_event_nested_creation_retains_parent_and_pending_tag_save(self):
        self.ws.new_event()
        task = self.ws.task
        task.title.set('Witness meeting')
        task.summary.insert('1.0', 'Keep this summary')
        nested = task.create_character()
        nested.name.set('Witness')
        self.assertTrue(nested.save())
        self.assertEqual(task.title.get(), 'Witness meeting')
        self.assertEqual(task.summary.get('1.0', 'end-1c'), 'Keep this summary')
        self.assertEqual(len(task.participants.selected), 1)
        self.assertTrue(task.save())
        self.ws.new_character()
        task = self.ws.task
        task.fields['name'].set('Another')
        task.editor.field_widgets['tags'].pending.set('Typed custom tag')
        task.draft.flush()
        self.assertEqual(self.db.drafts.list()[0]['values']['tags'], 'Typed custom tag')
        self.assertTrue(task.save())
        self.assertEqual(next(r for r in self.db.characters() if r['name'] == 'Another')['tags'], 'Typed custom tag')

    def test_classification_filter_and_primary_geometry_both_themes(self):
        a, b, c = self.cast()
        self.db.save_character(dict(name='Alden', classification='NPC Enemy'), a)
        self.ws.graph.classification_filter = 'Enemy NPC'
        self.ws.graph.refresh(force=True)
        self.assertEqual(set(self.ws.graph.graph), {a})
        self.assertIn('Enemy NPC (current)', self.ws.graph.displayed_scope())
        self.assertIn('Enemy NPC', self.ws.graph.renderer.node_labels[a].get_text())
        self.ws.graph.classification_filter = None
        for theme in ('dark', 'light'):
            for geometry, size, scaling in (('1280x720', 12, 96 / 72), ('900x600', 16, 144 / 72)):
                self.app.geometry(geometry)
                self.app.tk.call('tk', 'scaling', scaling)
                self.app.set_appearance(theme, size)
                self.ws.new_character()
                self.app.update()
                button = self.ws.task.save_button
                self.assertTrue(button.winfo_viewable(), (theme, geometry, size, scaling))
                self.assertLessEqual(button.winfo_rooty() + button.winfo_height(), self.app.winfo_rooty() + self.app.winfo_height())
                self.ws.close_task()
                for factory in (self.ws.new_relationship, self.ws.new_event):
                    self.ws.clear_selection()
                    factory()
                    self.app.update()
                    task = self.ws.task
                    from story_atlas.simple_batch import BatchPane
                    if isinstance(task, BatchPane):
                        self.assertFalse(task.save_button.winfo_viewable())
                        task.boxes['source'].buttons[a].invoke()
                        self.app.update()
                    self.assertTrue(task.save_button.winfo_viewable(), (theme, geometry, type(task).__name__))
                    self.assertLessEqual(task.save_button.winfo_rooty() + task.save_button.winfo_height(), self.app.winfo_rooty() + self.app.winfo_height())
                    task.draft.discard()
                    self.ws.remove_task()
        self.assertEqual(self.errors, [])
