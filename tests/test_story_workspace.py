"""Expanded sample and cast/event/relationship/graph workflow regressions."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from story_atlas.app import StoryAtlas
from story_atlas.database import Database
from story_atlas.sample_story import create_sample
from story_atlas.relationship_display import centered_connection, relationship_details, relationship_list_label, relationship_list_type
from story_atlas.global_search import SearchDialog
from story_atlas.graph_state import SavedViews


class SampleNarrativeTests(unittest.TestCase):
    def test_sample_chronology_and_complete_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(create_sample(Path(folder) / 'sample.db'))
            try:
                cast = db.characters()
                self.assertEqual(len(cast), 18)
                for row in cast:
                    for field in ('summary', 'backstory', 'traits', 'skills', 'inventory', 'faction', 'location', 'notes'):
                        self.assertTrue(row[field], (row['name'], field))
                events = {row['sequence']: row['id'] for row in db.events.list()}
                self.assertEqual(set(events), set(range(1, 11)))
                self.assertTrue(all(any(p['event_id'] == ident for p in db.events.participants()) for ident in events.values()))
                self.assertGreaterEqual(len({row['kind'] for row in db.relationship_records()}), 20)
                names = {row['name'].split()[0]: row['id'] for row in cast}
                def pair(a, b, chapter):
                    return [r for r in db.relationships(events[chapter]) if {r['source_id'], r['target_id']} == {names[a], names[b]}]
                self.assertEqual(pair('Mira', 'Seraphine', 1), [])
                self.assertEqual(pair('Mira', 'Seraphine', 2)[0]['semantics'], 'mutual')
                self.assertEqual(pair('Mira', 'Seraphine', 5)[0]['kind'], 'Enemy')
                resumed = pair('Thorne', 'Sable', 4)[0]['id']
                self.assertEqual(pair('Thorne', 'Sable', 6), [])
                self.assertEqual(pair('Thorne', 'Sable', 8)[0]['id'], resumed)
                self.assertEqual(len(pair('Garrick', 'Tamsin', 9)), 2)
            finally:
                db.close()


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.app = StoryAtlas(self.folder / 'story.db')
        self.addCleanup(self.cleanup)
        self.errors = []
        self.app.report_callback_exception = lambda *error: self.errors.append(error)
        self.db = self.app.database
        self.a, self.b, self.c, self.d = [self.db.save_character({'name': name}) for name in ('Same', 'Same', 'Other', 'Isolate')]
        self.mentor = self.db.save_relationship(self.a, self.b, 'Mentor', 'unique phrase', inverse_label='Mentee')
        self.friend = self.db.save_relationship(self.a, self.b, 'Friend', semantics='mutual')
        self.enemy = self.db.save_relationship(self.b, self.a, 'Enemy')
        self.next = self.db.save_relationship(self.b, self.c, 'Ally')
        self.event = self.db.events.save('Test event', '', 1, [self.a])
        self.app.refresh()
        self.app.update()

    def cleanup(self):
        self.app.update()
        self.app.database.close()
        self.app.destroy()

    def test_tabs_and_event_to_contextual_relationship_entry(self):
        tabs = [self.app.tabs.tab(tab, 'text') for tab in self.app.tabs.tabs() if self.app.tabs.tab(tab, 'state') != 'hidden']
        self.assertEqual(tabs, ['Characters', 'Chapters & events', 'Relationships', 'Graph'])
        self.app.tabs.select(self.app.events)
        self.app.events.tree.selection_set(str(self.event))
        dialog = self.app.events.connect_characters()
        self.assertEqual(self.app.tabs.select(), str(self.app.events))
        self.assertEqual(dialog.values()["category"], "Other")
        self.assertEqual({key: value for key, value in dialog.values().items() if key != "category"}, {key: "" for key in dialog.values() if key != "category"})
        self.assertIn('Test event', dialog.event_context.get())
        self.assertIn(f'Same (#{self.a})', dialog.event_context.get())
        dialog.close()

    def test_event_relationship_context_batch_and_historical_inspection(self):
        other = self.db.events.save('Later', '', 2)
        self.app.refresh()
        self.app.tabs.select(self.app.events)
        self.app.events.tree.selection_set(str(self.event))
        dialog = self.app.events.connect_characters()
        self.assertIn(f'Same (#{self.a})', dialog.event_context.get())
        self.assertNotIn(f'Same (#{self.b})', dialog.event_context.get())
        self.assertEqual(dialog.variables['start_event'].get(), '')
        self.assertTrue(dialog.use_context_event())
        self.assertEqual(dialog.event_choices[dialog.variables['start_event'].get()], self.event)
        override = next(label for label, ident in dialog.event_choices.items() if ident == other)
        dialog.variables['start_event'].set(override)
        labels = {ident: label for label, ident in dialog.choices.items()}
        for kind in ('New bond one', 'New bond two'):
            dialog.variables['source'].set(labels[self.a])
            dialog.variables['target'].set(labels[self.b])
            dialog.variables['kind'].set(kind)
            dialog.variables['semantics'].set('Directional')
            if kind == 'New bond two':
                dialog.use_context_event()
            dialog.focus_force()
            self.assertTrue(dialog.save())
            saved = dialog.last_saved_id
            self.app.update()
            self.assertEqual(dialog.values()["category"], "Other")
            self.assertEqual({key: value for key, value in dialog.values().items() if key != "category"}, {key: "" for key in dialog.values() if key != "category"})
            self.assertEqual(dialog.focus_lastfor(), dialog.boxes['source'])
            self.assertEqual(next(row['id'] for row in self.db.relationship_records() if row['id'] == saved), saved)
        self.assertEqual(self.db.history.rows(dialog.last_saved_id)[0]['event_id'], self.event)
        self.assertEqual(self.app.tabs.select(), str(self.app.events))
        dialog.variables['kind'].set('Unfinished')
        with patch('story_atlas.relationship_dialog.messagebox.askyesnocancel', return_value=None):
            dialog.close()
        self.assertTrue(dialog.winfo_exists())
        dialog.variables['source'].set(labels[self.a])
        dialog.variables['target'].set(labels[self.b])
        dialog.variables['kind'].set('Mentor')  # Existing duplicate: failed save retains input.
        dialog.variables['semantics'].set('Directional')
        before = dialog.values()
        self.assertFalse(dialog.save())
        self.assertEqual(dialog.values(), before)
        with patch('story_atlas.relationship_dialog.messagebox.askyesnocancel', return_value=False):
            dialog.close()

        self.app.events.tree.selection_set(str(self.event))
        dialog = self.app.events.connect_characters()
        dialog.variables['source'].set(labels[self.a])
        dialog.variables['target'].set(labels[self.b])
        dialog.variables['kind'].set('Temporary bond')
        dialog.variables['semantics'].set('Directional')
        self.assertTrue(dialog.save())
        ended_id = dialog.last_saved_id
        state = next(row for row in self.db.relationships() if row['id'] == ended_id)
        change_id = self.db.history.write(ended_id, self.event, state, active=False)
        self.assertFalse(any(row['id'] == ended_id for row in self.db.relationships()))
        history = dialog.inspect_saved()
        self.assertEqual(history.choice.get(), next(label for label, row in history.choices.items() if row['id'] == ended_id))
        self.assertEqual(history.tree.selection(), (str(change_id),))
        history.destroy()
        self.app.update()
        self.assertEqual(dialog.grab_current(), dialog)
        dialog.close()

    def test_focus_choice_filters_fits_and_does_not_select_node(self):
        graph = self.app.graph
        self.app.tabs.select(graph)
        self.app.update()
        graph.as_of_id = self.event
        graph.refresh(force=True)
        graph.select_node(self.c)
        positions = copy.deepcopy(graph.positions)
        graph.focus.set(next(k for k, v in graph.focus_choices.items() if v == self.a))
        graph.focus_box.event_generate('<<ComboboxSelected>>')
        self.app.update()
        self.assertEqual(graph.depth.get(), 'Direct')
        self.assertEqual(set(graph.graph), {self.a, self.b})
        self.assertEqual(graph.selection, ('node', self.c))
        self.assertEqual(graph.as_of_id, self.event)
        self.assertEqual(graph.positions, positions)
        self.assertEqual(graph.renderer.axes.get_xlim(), graph.renderer.fit_limits[0])
        self.assertEqual(graph.renderer.node_artist.get_sizes()[graph.renderer.nodes.index(self.a)], 850)
        graph.depth.set('Two steps')
        graph.filter_changed()
        self.assertEqual(set(graph.graph), {self.a, self.b, self.c})
        state = graph.capture_state()
        SavedViews(self.db).save('Focused', state)
        graph.depth.set('Full graph')
        graph.filter_changed()
        self.assertEqual(len(graph.graph), 4)
        graph.apply_state(SavedViews(self.db).load('Focused'))
        self.assertEqual(graph.capture_state(), state)
        self.assertEqual(self.errors, [])

    def test_focus_directions_and_isolates(self):
        graph = self.app.graph
        graph.refresh()
        graph.focus_node(self.a)
        for direction, expected in [('Outgoing', {self.mentor, self.friend}), ('Incoming', {self.enemy, self.friend})]:
            graph.direction.set(direction)
            graph.filter_changed()
            self.assertEqual(set(key for _, _, key in graph.graph.edges(keys=True)), expected)
        graph.focus_node(self.d)
        self.assertEqual(set(graph.graph), {self.d})
        graph.isolates.set(False)
        graph.filter_changed()
        self.assertEqual(len(graph.graph), 0)

    def test_cast_roster_arrows_search_and_exact_relationship_actions(self):
        view = self.app.relationships
        self.app.tabs.select(view)
        view.roster.query.set('same')
        self.assertEqual(set(view.roster.tree.get_children()), {'all', str(self.a), str(self.b)})
        view.roster.tree.selection_set(str(self.b))
        self.app.update()
        self.assertEqual(view.character_id, self.b)
        self.assertEqual(len(view.rows), 4)
        mentor = view.rows[str(self.mentor)]
        self.assertIn('←', centered_connection(mentor, self.b))
        self.assertIn('→', centered_connection(mentor, self.a))
        self.assertIn('Mentee', relationship_details(mentor, self.b))
        self.assertIn('↔', centered_connection(view.rows[str(self.friend)], self.b))
        # The selected cast member is named once in the heading; rows keep the
        # other duplicate-named character, direction, perspective, and exact ID.
        self.assertEqual(relationship_list_label(mentor, self.a), f'→ Same (#{self.b})')
        self.assertEqual(relationship_list_type(mentor, self.a), 'Mentor / Mentee')
        self.assertEqual(relationship_list_label(mentor, self.b), f'← Same (#{self.a})')
        self.assertEqual(relationship_list_type(mentor, self.b), 'Mentee / Mentor')
        self.assertEqual(relationship_list_label(view.rows[str(self.friend)], self.b), f'↔ Same (#{self.a})')
        self.assertEqual(relationship_list_label(view.rows[str(self.enemy)], self.b), f'→ Same (#{self.a})')
        self.assertEqual(relationship_list_label(mentor), f'Same (#{self.a}) → Same (#{self.b})')
        self.assertIn(f'Same (#{self.b})', view.heading.cget('text'))
        self.assertEqual(view.tree.item(str(self.mentor), 'values')[:2],
                         (f'← Same (#{self.a})', 'Mentee / Mentor'))
        view.select_character(None)
        self.assertEqual(view.tree.item(str(self.mentor), 'values')[0],
                         f'Same (#{self.a}) → Same (#{self.b})')
        view.select_character(self.d)
        self.assertFalse(view.rows)
        search = SearchDialog(self.app, {})
        search.query.set('unique phrase')
        search.refresh()
        search.tree.selection_set(f'relationship:{self.mentor}')
        search.open_selected()
        self.assertEqual(view.character_id, self.a)
        self.assertEqual(view.tree.selection(), (str(self.mentor),))
        editor = view.edit(view.rows[str(self.mentor)])
        editor.notes.insert('end', ' edited')
        self.assertTrue(editor.save())
        editor.close()
        self.assertEqual(len(self.db.relationships()), 4)
        view.select_relationship(self.mentor)
        with patch('story_atlas.relationships.messagebox.askyesno', return_value=True):
            view.delete()
        view.undo_delete()
        self.assertIn(self.mentor, [r['id'] for r in self.db.relationships()])
        self.assertEqual(self.errors, [])

    def test_pane_and_story_selection_persist(self):
        view = self.app.relationships
        self.app.tabs.select(view)
        self.app.update()
        view.panes.sashpos(0, 300)
        view.select_character(self.b)
        view.roster.query.set('same')
        view.select_relationship(self.enemy)
        other = Database(self.folder / 'other.db')
        other.close()
        self.app.projects.switch(self.folder / 'other.db')
        self.app.projects.switch(self.folder / 'story.db')
        self.assertEqual(view.character_id, self.b)
        self.assertEqual(view.tree.selection(), (str(self.enemy),))
        self.app.close()
        self.app = StoryAtlas(self.folder / 'story.db')
        self.app.tabs.select(self.app.relationships)
        self.app.update()
        self.assertAlmostEqual(self.app.relationships.panes.sashpos(0), 300, delta=5)

    def test_sample_action_cancellation_and_isolation(self):
        self.app.characters.open_character(self.a)
        self.app.characters.fields['name'].set('Pending edit')
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(self.app.projects.try_sample())
        self.assertFalse((self.folder / 'stories').exists())
        with patch('story_atlas.characters.messagebox.askyesnocancel', return_value=False):
            self.assertTrue(self.app.projects.try_sample())
        self.assertEqual(len(self.app.database.characters()), 18)
        original = Database(self.folder / 'story.db')
        self.assertEqual(len(original.characters()), 4)
        original.close()

    def test_relationship_layout_at_laptop_sizes_and_scaling(self):
        view = self.app.relationships
        self.app.tabs.select(view)
        for width, height, scale in ((1280, 720, 1), (1280, 720, 1.5), (900, 600, 1)):
            for theme in ('dark', 'light'):
                self.app.tk.call('tk', 'scaling', 96 / 72 * scale)
                self.app.geometry(f'{width}x{height}')
                self.app.set_appearance(theme, 14)
                self.app.update()
                self.assertGreater(view.tree.winfo_height(), 70, (width, height, scale, theme))
                for widget in view.actions.items:
                    self.assertTrue(widget.winfo_ismapped())
                    self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.app.winfo_rooty() + self.app.winfo_height())
        self.assertEqual(self.errors, [])
