"""Transaction undo/redo, branch safety, and actual keyboard dispatch."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from story_atlas.database import Database
import test_simple_mode as baseline


class UndoStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Database(Path(self.temp.name) / 'story.db')
        self.addCleanup(self.db.close)
        self.undo = self.db.enable_undo()

    def test_create_edit_delete_redo_keeps_ids_and_relationship_history(self):
        a = self.db.save_character(dict(name='A'))
        b = self.db.save_character(dict(name='B'))
        rel = self.db.save_relationship(a, b, 'Friend')
        event = self.db.events.save('Change', '', 1, [a, b])
        self.db.history.write(rel, event, dict(source_id=a, target_id=b, kind='Enemy'))
        before = self.undo.capture()
        self.db.delete_character(a)
        self.assertTrue(self.undo.apply())
        self.assertEqual(self.undo.capture(), before)
        self.assertEqual(self.db.relationships()[0]['kind'], 'Enemy')
        self.assertTrue(self.undo.apply(True))
        self.assertNotIn(a, {r['id'] for r in self.db.characters()})
        self.assertFalse(self.db.relationships())
        self.undo.apply()
        self.undo.apply()
        self.assertEqual(self.db.relationships()[0]['kind'], 'Friend')
        self.undo.apply(True)
        self.assertEqual(self.db.relationships()[0]['kind'], 'Enemy')

    def test_atomic_batch_branch_and_drafts_are_independent(self):
        a, b, c = [self.db.save_character(dict(name=n)) for n in ('A', 'B', 'C')]
        self.db.relationship_store.batch([(a,b),(a,c)], 'Friend', '', 'mutual', '', None)
        self.db.drafts.save(a, {'name': 'Uncommitted'})
        self.undo.apply()
        self.assertEqual(self.db.relationship_records(), [])
        self.assertEqual(self.db.drafts.list()[0]['values']['name'], 'Uncommitted')
        self.undo.apply(True)
        self.assertEqual(len(self.db.relationship_records()), 2)
        self.undo.apply()
        self.db.save_character(dict(name='A revised'), a)
        self.assertFalse(self.undo.apply(True))

    def test_chapter_event_introduction_and_reorder_roundtrip(self):
        chapter = self.db.chapters.save('Chapter', '')
        first = self.db.events.save('First', '', 1)
        second = self.db.events.save('Second', '', 2)
        a = self.db.save_character(dict(name='Later', introduction_event_id=second))
        before = self.undo.capture()
        with self.db.connection:
            self.db.connection.execute('UPDATE story_events SET chapter_id=?', (chapter,))
        self.undo.apply()
        self.assertEqual(self.undo.capture(), before)
        self.undo.apply(True)
        self.assertTrue(all(row['chapter_id'] == chapter for row in self.db.events.list()))
        self.assertEqual(self.db.characters()[0]['introduction_event_id'], second)

    def test_failure_rolls_back_and_external_changes_reset_history(self):
        self.db.save_character(dict(name='A'))
        self.db.connection.execute("CREATE TRIGGER reject_undo BEFORE DELETE ON characters BEGIN SELECT RAISE(ABORT,'write failed'); END")
        with self.assertRaises(sqlite3.Error):
            self.undo.apply()
        self.assertEqual(self.db.characters()[0]['name'], 'A')
        self.assertEqual(len(self.undo.past), 1)
        self.db.connection.execute('DROP TRIGGER reject_undo')
        other = sqlite3.connect(self.db.path)
        with other:
            other.execute("UPDATE characters SET name='External'")
        other.close()
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.undo.apply()
        self.assertEqual(self.db.characters()[0]['name'], 'External')
        self.assertFalse(self.undo.past)


class UndoUITests(unittest.TestCase):
    setUp = baseline.SimpleUITests.setUp
    cleanup = baseline.SimpleUITests.cleanup

    def test_unsaved_form_and_modal_do_not_change_saved_history(self):
        import tkinter as tk
        from story_atlas.widgets import text_area
        self.db.save_character(dict(name='Saved'))
        self.app.refresh()
        self.ws.new_character()
        self.ws.task.fields['name'].set('Unsaved')
        self.assertFalse(self.app.undo_controls.change())
        self.assertEqual(len(self.db.characters()), 1)
        self.ws.task.draft.discard()
        self.ws.remove_task()
        dialog = tk.Toplevel(self.app)
        text = text_area(dialog)
        text.pack()
        dialog.grab_set()
        text.focus_force()
        self.app.update()
        text.insert('1.0', 'Draft in dialog')
        text.edit_separator()
        text.event_generate('<Control-z>')
        self.assertEqual(text.get('1.0','end-1c'), '')
        self.assertFalse(self.app.undo_controls.change())
        dialog.destroy()
        self.assertEqual(len(self.db.characters()), 1)
        self.assertEqual(self.errors, [])

    def test_story_switch_starts_separate_history(self):
        self.db.save_character(dict(name='Keep in first story'))
        self.app.refresh()
        self.assertTrue(self.app.projects.try_sample('prometheus'))
        self.db = self.app.database
        self.assertFalse(self.app.undo_controls.change())
        self.assertEqual(len(self.db.characters()), 17)

    def test_shortcuts_undo_and_redo_summary_delete(self):
        a, b = [self.db.save_character(dict(name=n)) for n in ('A', 'B')]
        self.db.save_relationship(a, b, 'Friend')
        self.app.refresh()
        self.ws.graph.select_node(a)
        with patch('story_atlas.simple_workspace.messagebox.askyesno', return_value=True):
            self.ws.task.delete_button.invoke()
        canvas = self.ws.graph.canvas.get_tk_widget()
        canvas.focus_force()
        self.app.update()
        canvas.event_generate('<Control-z>')
        self.app.update()
        self.assertIn(a, self.ws.graph.graph)
        self.assertEqual(len(self.db.relationships()), 1)
        canvas.event_generate('<Control-y>')
        self.app.update()
        self.assertNotIn(a, self.ws.graph.graph)
        self.assertEqual(self.errors, [])

    def test_typing_undo_redo_is_local_and_does_not_undo_saved_character(self):
        a = self.db.save_character(dict(name='Saved'))
        self.app.refresh()
        self.ws.edit_character(a)
        editor = self.ws.task.editor
        name = editor.field_widgets['name']
        name.focus_force()
        self.app.update()
        name.insert('end', ' edit')
        name.event_generate('<KeyRelease>', keysym='t')
        name.event_generate('<Control-z>')
        self.assertEqual(name.get(), 'Saved')
        name.event_generate('<Control-y>')
        self.assertEqual(name.get(), 'Saved edit')
        self.assertEqual(self.db.characters()[0]['name'], 'Saved')
        editor.focus_section('goals')
        self.app.update()
        text = editor.fields['goals']
        text.insert('end', 'A goal')
        text.edit_separator()
        text.event_generate('<Control-z>')
        self.assertEqual(text.get('1.0','end-1c'), '')
        text.event_generate('<Control-y>')
        self.assertEqual(text.get('1.0','end-1c'), 'A goal')
        self.assertEqual(len(self.db.characters()), 1)
        self.assertEqual(self.errors, [])

    def test_graph_move_and_saved_change_share_order(self):
        a = self.db.save_character(dict(name='A'))
        self.app.refresh()
        self.ws.graph.select_node(a)
        old = list(self.ws.graph.positions[a])
        self.ws.graph.keyboard_move(.2, .1)
        new = list(self.ws.graph.positions[a])
        self.assertTrue(self.app.undo_controls.change())
        self.assertEqual(self.ws.graph.positions[a], old)
        self.assertTrue(self.app.undo_controls.change(True))
        self.assertEqual(self.ws.graph.positions[a], new)
        self.app.undo_controls.change()
        self.app.undo_controls.change()
        self.assertFalse(self.db.characters())
        self.assertEqual(self.errors, [])

    def test_layout_undo_restores_layout_choice_and_profile_reload_clears_text_history(self):
        a, b = [self.db.save_character(dict(name=n, goals='Original')) for n in ('A', 'B')]
        self.app.refresh()
        graph = self.ws.graph
        graph.layout.set('Spring')
        graph.reset_layout()
        self.assertTrue(self.app.undo_controls.change())
        self.assertEqual(graph.layout.get(), 'Circle')
        self.assertTrue(self.app.undo_controls.change(True))
        self.assertEqual(graph.layout.get(), 'Spring')
        view = self.app.characters
        view.load(next(r for r in self.db.characters() if r['id'] == a))
        text = view.fields['goals']
        text.insert('end', ' first character edit')
        text.edit_separator()
        view.load(next(r for r in self.db.characters() if r['id'] == b))
        with self.assertRaises(Exception):
            text.edit_undo()
        self.assertEqual(text.get('1.0','end-1c'), 'Original')
