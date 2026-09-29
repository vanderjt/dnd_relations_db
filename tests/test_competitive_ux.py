"""Task-level regressions for the September competitive UX recommendations."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from matplotlib.backend_bases import MouseEvent
from story_atlas.app import StoryAtlas
from story_atlas.database import Database
from story_atlas.event_editor import EventDialog
from story_atlas.graph_state import SavedViews, validate_view
from story_atlas.graph_render import category
from story_atlas.goals_view import CastGoalsDialog
from story_atlas.relationship_dialog import RelationshipDialog


class CompetitiveUXTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.app = StoryAtlas(self.folder / 'story.db')
        self.addCleanup(self.cleanup)
        self.errors = []
        self.app.report_callback_exception = lambda *error: self.errors.append(error)
        self.db = self.app.database
        self.a = self.db.save_character(dict(name='Same', role='Witness', goals='Intent\n  Keep Ω\n' + 'A long goal. ' * 70))
        self.b = self.db.save_character(dict(name='Same', faction='Council'))
        self.chapter = self.db.chapters.save('First')
        self.event = self.db.chapters.save_event('Pact', 'Summary ' * 80, 1, [self.a, self.b], chapter_id=self.chapter)
        self.later = self.db.chapters.save_event('Later', '', 2, chapter_id=self.chapter)
        self.rel = self.db.save_relationship(self.a, self.b, 'Pact', semantics='mutual')
        self.app.refresh()
        self.app.events.reveal_event(self.event)
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def flow(self, correction=False):
        flow = self.app.events.add_relationship_change()
        flow.choice.set(next(key for key, row in flow.choices.items() if row['id'] == self.rel))
        editor = flow.review() if correction else flow.describe()
        self.app.update()
        return flow, editor

    def test_new_event_revealed_in_destination_and_failed_save_keeps_fields(self):
        chapter = self.db.chapters.save('Destination')
        dialog = self.app.events.edit()
        dialog.title_value.set('New scene')
        dialog.chapter.value.set(next(key for key, value in dialog.chapter.choices.items() if value == chapter))
        dialog.chapter_changed()
        with patch.object(self.db.chapters, 'save_event', side_effect=sqlite3.OperationalError('locked')):
            self.assertFalse(dialog.save())
        self.assertIn('Not saved', dialog.error.get())
        self.assertEqual(dialog.title_value.get(), 'New scene')
        self.assertTrue(dialog.save())
        self.app.update()
        view = self.app.events
        self.assertEqual(view.chapter_id, chapter)
        self.assertEqual(view.rows[view.tree.selection()[0]]['title'], 'New scene')
        self.assertNotIn('disabled', view.add_change_button.state())
        self.assertEqual(view.detail_heading.get(), 'New scene')

    def test_native_participant_checkboxes_search_keyboard_and_deleted_references(self):
        cast = [self.db.save_character(dict(name=f'Person {i:03}')) for i in range(100)]
        deleted = cast.pop()
        self.db.delete_character(deleted)
        self.db.delete_character(self.b)
        row = next(row for row in self.db.events.list() if row['id'] == self.event)
        dialog = EventDialog(self.app.events, self.db, self.app.refresh, row)
        picker = dialog.participants
        self.assertNotIn(deleted, picker.rows)
        self.assertIn(self.b, picker.selected)
        self.assertIn('disabled', picker.buttons[self.b].state())
        self.assertIn('Witness', picker.buttons[self.a].cget('text'))
        self.assertIn('Council', picker.buttons[self.b].cget('text'))
        for ident in cast[::20]:
            picker.query.set(str(ident))
            self.app.update()
            picker.buttons[ident].focus_force()
            picker.buttons[ident].event_generate('<KeyPress-space>')
            picker.buttons[ident].event_generate('<KeyRelease-space>')
            self.app.update()
        self.assertEqual(picker.selected, {self.a, self.b, *cast[::20]})
        picker.query.set('no matches')
        self.assertEqual(picker.selected, {self.a, self.b, *cast[::20]})
        self.assertIn('(7)', picker.summary.get())
        picker.inspect(self.a)
        self.assertIn('  Keep Ω', picker.preview.get('1.0', 'end'))
        self.assertTrue(dialog.save())
        saved = {row['character_id'] for row in self.db.events.participants() if row['event_id'] == self.event}
        self.assertEqual(saved, {self.a, self.b, *cast[::20]})
        self.assertEqual(self.errors, [])

    def test_single_task_record_correct_mutual_failure_review_and_later_independence(self):
        base = self.db.relationship_records()[0]
        self.db.history.write(self.rel, self.later, dict(base, kind='Later state'))
        flow, editor = self.flow()
        editor.variables['kind'].set('Enemy')
        editor.notes.insert('1.0', 'Kept notes Ω')
        pending = editor.values()
        with patch('story_atlas.state_editor.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(editor.close())
        self.assertEqual(editor.values(), pending)
        flow.focus_force()
        flow.event_generate('<Control-Return>')
        self.app.update()
        self.assertEqual(editor.step, 'review')
        self.assertFalse(any(isinstance(child, tk.Toplevel) for child in flow.winfo_children()))
        editor.back_to_edit()
        self.assertEqual(editor.values(), pending)
        editor.review_change()
        with patch.object(self.db.history, 'write', side_effect=ValueError('Duplicate connection')):
            self.assertFalse(editor.commit())
        self.assertEqual(editor.values(), pending)
        self.assertIn('Not saved', editor.error.get())
        self.assertEqual(len(self.db.history.rows(self.rel)), 1)
        self.assertTrue(editor.commit())
        state = self.db.history.rows(self.rel)[0]
        self.assertEqual(state['kind'], 'Enemy')
        self.assertEqual(state['semantics'], 'mutual')
        self.assertEqual(self.db.relationships()[0]['kind'], 'Later state')
        self.assertIn(f"change:{state['id']}", self.app.events.change_tree.selection()[0])
        flow.choice.set(next(key for key, row in flow.choices.items() if row['id'] == self.rel))
        self.assertIsNone(flow.describe())
        correction = flow.review()
        correction.variables['kind'].set('Corrected spelling')
        correction.review_change()
        self.assertIn('no new story change', correction.review_content.get('1.0', 'end'))
        self.assertTrue(correction.commit())
        self.assertEqual(len(self.db.history.rows(self.rel)), 2)
        self.assertEqual(self.db.history.rows(self.rel)[0]['id'], state['id'])
        self.assertEqual(self.db.relationships()[0]['kind'], 'Later state')
        flow.destroy()

    def test_inline_state_validation_and_real_duplicate_rollback(self):
        other = self.db.save_relationship(self.a, self.b, 'Other', semantics='mutual')
        flow, editor = self.flow()
        editor.variables['kind'].set('')
        self.assertIsNone(editor.review_change())
        self.assertTrue(editor.errors['kind'].get())
        editor.variables['kind'].set('Other')
        editor.variables['inverse_label'].set('Keep this')
        self.assertIsNone(editor.review_change())
        self.assertTrue(editor.errors['inverse_label'].get())
        editor.variables['inverse_label'].set('')
        before = self.db.history.rows(), self.db.activity()
        editor.review_change()
        self.assertFalse(editor.commit())
        self.assertEqual((self.db.history.rows(), self.db.activity()), before)
        self.assertEqual(editor.variables['kind'].get(), 'Other')
        flow.destroy()

    def test_event_graph_profile_back_back_restores_context_and_goal_edit(self):
        events = self.app.events
        key = f'character:{self.a}'
        events.goals_tree.selection_set(key)
        events.goals_tree.item(key, open=False)
        events.goals_tree.focus(key)
        events.detail_scroller.canvas.yview_moveto(.35)
        self.app.update()
        state = events.capture_context()
        events.show_graph()
        self.app.update()
        graph = self.app.graph
        graph.kind.set('Pact')
        graph.focus_node(self.a)
        graph.select_node(self.a)
        graph.renderer.axes.set_xlim(-.4, .6)
        graph.renderer.axes.set_ylim(-.3, .7)
        graph_state = graph.capture_state()
        graph.open_profile(self.a)
        self.app.update()
        self.assertEqual(self.app.characters.profile_tabs.select(), str(self.app.characters.overview))
        self.assertTrue(self.app.navigation.back())
        self.app.update()
        self.assertEqual(graph.capture_state(), graph_state)
        self.assertTrue(self.app.navigation.back())
        self.app.update()
        restored = events.capture_context()
        self.assertEqual(restored['chapter'], state['chapter'])
        self.assertEqual(restored['selection'], state['selection'])
        self.assertEqual(restored['trees'], state['trees'])
        self.assertAlmostEqual(restored['scroll'], state['scroll'], places=2)
        self.assertTrue(events.edit_current_goals())
        self.app.characters.fields['goals'].insert('end', '\nNew free text')
        self.assertTrue(self.app.characters.save())
        self.assertTrue(self.app.navigation.back())
        self.app.update()
        self.assertEqual(events.tree.selection(), (str(self.event),))
        self.assertIn('New free text', events.goal_detail.get('1.0', 'end'))
        self.assertEqual(self.errors, [])

    def test_story_isolation_and_unfinished_change_blocks_switch(self):
        other = Database(self.folder / 'other.db')
        other.close()
        flow, editor = self.flow()
        with patch('story_atlas.projects.messagebox.showinfo'):
            self.assertFalse(self.app.projects.switch(self.folder / 'other.db'))
        flow.destroy()
        self.app.events.show_graph()
        self.app.graph.visual_categories['Pact'] = 'Conflict'
        self.app.graph.highlight_changes.set(True)
        self.assertTrue(self.app.projects.switch(self.folder / 'other.db'))
        self.app.graph.ensure_current()
        self.assertEqual(self.app.navigation.stack, [])
        self.assertIsNone(self.app.graph.as_of_id)
        self.assertEqual(self.app.graph.visual_categories, {})
        self.assertFalse(self.app.graph.highlight_changes.get())

    def test_graph_scope_time_filters_exports_and_explicit_categories(self):
        row = self.db.relationship_records()[0]
        self.db.history.write(self.rel, self.event, dict(row, notes='Ends here'), active=False)
        graph = self.app.graph
        self.app.events.show_graph()
        self.app.update()
        self.assertEqual(graph.graph.number_of_edges(), 0)
        positions = copy.deepcopy(graph.positions)
        limits = (graph.renderer.axes.get_xlim(), graph.renderer.axes.get_ylim())
        graph.highlight_changes.set(True)
        graph.changes_only.set(True)
        graph.refresh(force=True)
        self.assertIn(self.rel, graph.renderer.edge_artists)
        self.assertIn('ENDED HERE', graph.renderer.edge_labels[self.rel].get_text())
        graph.select_edge(self.rel)
        graph.kind.set('Pact')
        output = self.folder / 'changes.png'
        with patch('story_atlas.graph_actions.filedialog.asksaveasfilename', return_value=str(output)):
            graph.export()
        exported = json.loads(output.with_suffix('.json').read_text(encoding='utf-8'))
        self.assertIn('Changes only', exported['display_scope'])
        self.assertIn('not historically versioned', exported['profile_scope'])
        self.assertEqual(exported['relationships'][0]['baseline_active'], 0)
        graph.clear_filters()
        self.assertEqual(graph.as_of_id, self.event)
        graph.step_event(1)
        self.assertEqual(graph.as_of_id, self.later)
        graph.step_event(-1)
        self.assertEqual(graph.positions, positions)
        self.assertEqual((graph.renderer.axes.get_xlim(), graph.renderer.axes.get_ylim()), limits)
        self.assertEqual(graph.selection, ('edge', self.rel))
        self.assertEqual(category('Mentor'), 'Other')
        graph.set_visual_category('Mentor', 'Conflict')
        state = graph.capture_state()
        SavedViews(self.db).save('Visual choices', state)
        self.assertEqual(SavedViews(self.db).load('Visual choices'), state)
        self.assertEqual(self.db.relationship_records()[0]['kind'], 'Pact')
        with self.assertRaises(ValueError):
            validate_view(dict(state, visual_categories={'Pact': 'Invented'}))

    def test_cast_goal_search_direct_navigation_and_optional_content_retention(self):
        cast = CastGoalsDialog(self.app.characters, self.db)
        cast.query.set('Ω')
        self.assertEqual(list(cast.choices.values()), [self.a])
        cast.open_character()
        self.assertEqual(self.app.characters.character_id, self.a)
        entry = RelationshipDialog(self.app, self.db, self.app.refresh)
        self.assertEqual(entry.values()["category"], "Other")
        self.assertEqual({key: value for key, value in entry.values().items() if key != "category"}, {key: "" for key in entry.values() if key != "category"})
        entry.toggle_optional()
        entry.notes.insert('1.0', 'Keep hidden notes')
        entry.variables['inverse_label'].set('Retain inverse')
        before = entry.values()
        entry.toggle_optional()
        self.assertEqual(entry.values(), before)
        self.assertTrue(entry.inverse_frame.winfo_manager())
        entry.destroy()

    def test_long_text_narrow_panes_themes_and_large_text(self):
        view = self.app.events
        view.goals_tree.selection_set(f'character:{self.a}')
        view.read_goal()
        for theme in ('dark', 'light'):
            self.app.set_appearance(theme, 16)
            self.app.geometry('900x600')
            self.app.update()
            view.toggle_navigation()
            self.app.update()
            self.assertEqual(view.workspace.panes(), (str(view.detail),))
            self.assertEqual(view.goal_detail.cget('wrap'), 'word')
            self.assertIn('  Keep Ω', view.goal_detail.get('1.0', 'end'))
            self.assertGreater(view.detail.winfo_width(), 700)
            view.toggle_navigation()
            self.app.update()
            self.assertEqual(len(view.workspace.panes()), 3)
        self.assertEqual(self.errors, [])

    def test_dense_graph_interaction_100_characters_300_parallel_reverse_links(self):
        dense = Database(self.folder / 'dense.db')
        nodes = [dense.save_character(dict(name=f'Character {i:03}')) for i in range(100)]
        links = []
        for i, source in enumerate(nodes):
            target = nodes[(i + 1) % len(nodes)]
            for a, b, kind in ((source, target, 'First'), (source, target, 'Parallel'), (target, source, 'Reverse')):
                links.append(dense.save_relationship(a, b, kind, 'Complete inspector notes ' * 20))
        event = dense.events.save('One change', '', 1)
        row = dense.relationship_records()[0]
        dense.history.write(row['id'], event, dict(row, kind='Changed type'))
        dense.close()
        self.assertTrue(self.app.projects.switch(self.folder / 'dense.db'))
        graph = self.app.graph
        self.app.tabs.select(graph)
        self.app.update()
        graph.canvas.draw()
        self.assertEqual((len(graph.graph), graph.graph.number_of_edges()), (100, 300))
        self.assertEqual(len(graph.renderer.edge_artists), 300)
        self.assertLess(sum(label.get_visible() for label in graph.renderer.edge_labels.values()), 60)
        # The inspector exposes every exact ID even when dense labels are hidden.
        for ident in links[:3]:
            graph.inspector.tree.selection_set(str(ident))
            self.app.update()
            self.assertEqual(graph.selection, ('edge', ident))
            self.assertTrue(graph.renderer.edge_labels[ident].get_visible())
            self.assertIn('Complete inspector notes', graph.inspector.details.get('1.0', 'end'))
        x, y = graph.renderer.axes.transData.transform(graph.positions[nodes[0]])
        graph.on_click(MouseEvent('button_press_event', graph.canvas, x, y, button=1))
        self.assertEqual(graph.selection, ('node', nodes[0]))
        graph.last_motion = 0
        graph.on_motion(MouseEvent('motion_notify_event', graph.canvas, x + 25, y + 20, button=1))
        graph.on_release(MouseEvent('button_release_event', graph.canvas, x + 25, y + 20, button=1))
        self.assertIn(nodes[0], graph.pins)
        graph.renderer.axes.set_xlim(-.5, .5)
        positions = copy.deepcopy(graph.positions)
        graph.step_event(-1)
        graph.highlight_changes.set(True)
        graph.refresh(force=True)
        self.assertEqual(graph.positions, positions)
        self.assertEqual(graph.renderer.axes.get_xlim(), (-.5, .5))
        self.assertIn(row['id'], graph.renderer.changed_ids)
        self.assertIn('CHANGED', graph.renderer.edge_labels[row['id']].get_text())
        self.assertEqual(self.errors, [])
