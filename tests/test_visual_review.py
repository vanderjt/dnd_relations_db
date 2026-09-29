"""Interaction regressions in the semantic visual-language rollout."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk

from story_atlas.app import StoryAtlas
from story_atlas.widgets import read_only_text_area, set_read_only_text


class VisualReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = StoryAtlas(Path(self.temp.name) / 'story.db')
        self.addCleanup(self.cleanup)
        self.db = self.app.database
        self.a = self.db.save_character({'name': 'Same'})
        self.b = self.db.save_character({'name': 'Same'})
        self.rel = self.db.save_relationship(self.a, self.b, 'Ally')
        self.event = self.db.events.save('Ending', 'A long summary', 1, [self.a, self.b])
        self.app.refresh()
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_detail_keyboard_copy_traversal_and_refresh(self):
        # A child dialog inherits the root palette, without its own atlas_palette.
        dialog = tk.Toplevel(self.app)
        before = ttk.Entry(dialog)
        before.pack()
        detail = read_only_text_area(dialog, height=3)
        detail.pack()
        after = ttk.Button(dialog, text='Next')
        after.pack()
        text = '\n'.join(f'Line {i}' for i in range(30))
        set_read_only_text(detail, text)
        self.app.update()
        dialog.focus_force()
        detail.focus_set()
        detail.event_generate('<Control-a>')
        detail.event_generate('<<Copy>>')
        self.app.update()
        self.assertEqual(dialog.clipboard_get(), text)
        detail.event_generate('<KeyPress-x>')
        self.assertEqual(detail.get('1.0', 'end-1c'), text)
        detail.yview_moveto(.5)
        position = detail.yview()
        selected = detail.tag_ranges('sel')
        set_read_only_text(detail, text)
        self.assertEqual(detail.yview(), position)
        self.assertEqual(detail.tag_ranges('sel'), selected)
        detail.event_generate('<Tab>')
        self.app.update()
        self.assertEqual(self.app.focus_get(), after)
        detail.focus_set()
        detail.event_generate('<Shift-Tab>')
        self.app.update()
        self.assertEqual(self.app.focus_get(), before)
        for mode in ('light', 'dark'):
            self.app.set_appearance(mode, 12)
            self.assertEqual(detail.cget('bg'), self.app.atlas_palette['detail'])
        dialog.destroy()

    def test_ended_relationship_history_is_reachable_without_selection(self):
        row = self.db.relationship_records()[0]
        self.db.history.write(self.rel, self.event, row, active=False)
        self.app.refresh()
        view = self.app.relationships
        self.assertFalse(view.tree.get_children())
        control = next(item for item in view.actions.items
                       if item.cget('text') == 'All relationship history')
        self.assertNotIn('disabled', control.state())
        control.invoke()
        dialog = next(child for child in view.winfo_children() if isinstance(child, tk.Toplevel))
        self.assertIn(self.rel, [row['id'] for row in dialog.choices.values()])
        dialog.destroy()

    def test_focus_description_tracks_actual_scope(self):
        graph = self.app.graph
        self.app.tabs.select(graph)
        self.app.update()
        graph.focus_node(self.a)
        graph.select_node(self.a)
        for scope in ('Direct', 'Two steps', 'Full graph'):
            graph.depth.set(scope)
            graph.filter_changed()
            self.assertIn(f'scope is {scope}', graph.inspector.details.get('1.0', 'end'))

    def test_event_participants_with_duplicate_names_display_without_ids(self):
        self.app.events.tree.selection_set(str(self.event))
        self.app.events.show_details()
        text = self.app.events.cast_body.get('1.0', 'end')
        self.assertEqual(text.count('• Same'), 2)
        goals = self.app.events.goals_tree
        self.assertEqual([goals.item(root, 'text') for root in goals.get_children()], ['Same', 'Same'])
