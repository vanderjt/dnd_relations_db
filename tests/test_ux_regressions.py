"""Exercise the user interaction paths missed by the initial UX rollout."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tkinter import ttk

from story_atlas.app import StoryAtlas
from story_atlas.database import Database
from story_atlas.history_dialog import StateDialog, StoryChangeReviewDialog


def button(parent, label):
    for child in parent.winfo_children():
        if isinstance(child, ttk.Button) and child.cget('text') == label:
            return child
        found = button(child, label)
        if found:
            return found


class UXRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.app = StoryAtlas(self.folder / 'a.db')
        self.addCleanup(self.cleanup)
        self.errors = []
        self.app.report_callback_exception = lambda *error: self.errors.append(error)
        self.db = self.app.database
        self.a = self.db.save_character({'name': 'Mira'})
        self.b = self.db.save_character({'name': 'Pip'})
        self.rel = self.db.save_relationship(self.a, self.b, 'Ally')
        self.event = self.db.events.save('Chapter 5', '', 5, [self.a, self.b])
        self.app.refresh()
        self.view = self.app.characters
        self.view.open_character(self.a)
        self.app.update()

    def cleanup(self):
        self.app.update()
        self.app.database.close()
        self.app.destroy()

    def test_story_switch_invalidates_both_undo_actions(self):
        with patch('story_atlas.relationships.messagebox.askyesno', return_value=True):
            self.app.relationships.tree.selection_set(str(self.rel))
            self.app.relationships.delete()
            self.view.delete()
        other = Database(self.folder / 'b.db')
        a = other.save_character({'name': 'Different Mira'})
        b = other.save_character({'name': 'Different Pip'})
        rel = other.save_relationship(a, b, 'Enemy')
        other.delete_relationship(rel)
        other.delete_character(a)
        before = other.trash.items()
        other.close()
        self.assertTrue(self.app.projects.switch(self.folder / 'b.db'))
        for page in (self.view, self.app.relationships):
            self.assertIsNone(page.undo_target)
            self.assertIn('disabled', page.undo_button.state())
            page.undo_delete()
        self.assertEqual(self.app.database.trash.items(), before)

    def test_done_discard_resets_existing_and_new_profiles(self):
        for ident in (self.a, None):
            row = next((r for r in self.db.characters() if r['id'] == ident), None)
            self.view.load(row)
            self.view.edit_profile()
            self.app.update()
            self.view.fields['name'].set('Discard me')
            with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=False) as prompt:
                button(self.view.buttons, 'Done').invoke()
            self.assertEqual(prompt.call_count, 1)
            self.assertEqual(self.view.values(), self.view.original)
            self.assertEqual(self.view.values()['name'], 'Mira' if ident else '')
        self.assertEqual(len(self.db.characters()), 2)

    def test_done_cancel_save_and_failed_save(self):
        self.view.edit_profile()
        self.view.fields['name'].set('New name')
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(self.view.done())
        self.assertEqual(self.view.profile_tabs.select(), str(self.view.editor))
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=True):
            self.assertTrue(self.view.done())
        self.assertEqual(self.view.original['name'], 'New name')
        self.view.edit_profile()
        self.view.fields['name'].set('')
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=True), patch('story_atlas.characters.messagebox.showerror'):
            self.assertFalse(self.view.done())
        self.assertEqual(self.view.profile_tabs.select(), str(self.view.editor))
        self.assertEqual(self.view.fields['name'].get(), '')

    def test_navigation_prompts_once_and_cancellation_preserves_back(self):
        nav = self.app.navigation
        self.view.fields['name'].set('Discard')
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=False) as prompt:
            self.assertTrue(nav.open_profile_link(self.b))
        self.assertEqual(prompt.call_count, 1)
        self.view.fields['name'].set('Keep pending')
        stack = list(nav.stack)
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=None) as prompt:
            self.assertFalse(nav.back())
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(nav.stack, stack)
        self.assertEqual(self.view.character_id, self.b)
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=False) as prompt:
            self.assertTrue(nav.back())
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(self.view.character_id, self.a)
        self.view.fields['name'].set('Save once')
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=True) as prompt:
            self.assertTrue(nav.open_from_graph(self.b))
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(next(r for r in self.db.characters() if r['id'] == self.a)['name'], 'Save once')

    def test_section_buttons_focus_widgets_and_reopening_preserves_order(self):
        self.app.focus_force()
        for label, field in [('Edit identity', 'name'), ('Add more details', 'summary'), ('Edit notes', 'notes')]:
            self.view.profile_tabs.select(self.view.overview)
            button(self.view.overview, label).invoke()
            self.app.update()
            self.assertEqual(self.app.focus_get(), self.view.editor.field_widgets[field])
        for name, (header, body, _) in self.view.editor.collapsible_sections.items():
            for _ in range(2):
                header.invoke()
                header.invoke()
                siblings = list(body.master.pack_slaves())
                self.assertEqual(siblings.index(body), siblings.index(header) + 1, name)
        self.assertEqual(self.errors, [])

    def change_editor(self):
        self.app.events.tree.selection_set(str(self.event))
        flow = self.app.events.add_relationship_change()
        flow.choice.set(next(label for label, row in flow.choices.items() if row['id'] == self.rel))
        flow.continue_button.invoke()
        editor = flow.editor
        editor.variables['kind'].set('Enemy')
        self.app.update()
        return flow, editor

    def test_keyboard_review_then_graph_completion_button(self):
        flow, editor = self.change_editor()
        editor.focus_force()
        editor.event_generate('<Control-Return>')
        self.app.update()
        self.assertEqual(self.db.history.rows(self.rel), [])
        review = editor
        button(review, 'Back to edit').invoke()
        self.assertEqual(self.app.grab_current(), flow)
        button(editor, 'Review change').invoke()
        review = editor
        button(review, 'Record story change').invoke()
        self.app.update()
        self.assertEqual(len(self.db.history.rows(self.rel)), 1)
        flow.graph_button.invoke()
        self.app.update()
        self.assertEqual(self.app.tabs.select(), str(self.app.graph))
        self.assertEqual(self.app.graph.as_of_id, self.event)
        self.assertIsNone(self.app.grab_current())
        self.assertEqual(self.errors, [])

    def test_close_save_requires_review_and_failure_retains_input(self):
        flow, editor = self.change_editor()
        with patch('story_atlas.history_dialog.messagebox.askyesnocancel', return_value=True):
            editor.close()
        self.assertEqual(self.db.history.rows(self.rel), [])
        review = editor
        with patch.object(self.db.history, 'write', side_effect=ValueError('Conflict')), patch('story_atlas.history_dialog.messagebox.showerror'):
            button(review, 'Record story change').invoke()
        self.assertTrue(editor.winfo_exists())
        self.assertTrue(review.winfo_exists())
        self.assertEqual(editor.variables['kind'].get(), 'Enemy')
        self.assertEqual(self.db.history.rows(self.rel), [])
        button(review, 'Back to edit').invoke()
        with patch('story_atlas.history_dialog.messagebox.askyesnocancel', return_value=False):
            editor.close()
        flow.destroy()
        self.assertEqual(self.errors, [])
