"""Review regressions through graph actions and real Tk event dispatch."""
import copy
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from story_atlas.app import StoryAtlas
from story_atlas.event_editor import EventDialog
from story_atlas.scroll_frame import ScrollFrame
from story_atlas.widgets import set_read_only_text


class ReviewCorrections(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = StoryAtlas(Path(self.temp.name) / 'story.db')
        self.db = self.app.database
        self.a = self.db.save_character(dict(name='Ada'))
        self.b = self.db.save_character(dict(name='Ben'))
        self.first = self.db.events.save('Alliance', '', 1, [self.a, self.b])
        self.middle = self.db.events.save('Interlude', '', 2, [])
        self.last = self.db.events.save('Conflict', '', 3, [self.a, self.b])
        self.rel = self.db.save_relationship(self.a, self.b, 'Friend', semantics='mutual')
        self.base = self.db.relationship_records()[0]
        self.ally = self.db.history.write(self.rel, self.first, dict(self.base, kind='Ally'))
        self.enemy = self.db.history.write(self.rel, self.last, dict(self.base, source_id=self.b, target_id=self.a,
            kind='Enemy', semantics='directional', inverse_label='Opponent'), False)
        self.app.refresh()
        self.app.tabs.select(self.app.graph)
        self.app.update()

    def tearDown(self):
        self.app.database.close()
        self.app.destroy()
        self.temp.cleanup()

    def graph_at(self, event, changes=False):
        graph = self.app.graph
        graph.as_of_id = event
        graph.changes_only.set(changes)
        graph.refresh(force=True)
        graph.select_edge(self.rel)
        self.app.update()
        return graph

    def test_current_notes_correction_preserves_ended_active_and_undated_entries(self):
        for variant in ('ended', 'active', 'undated'):
            with self.subTest(variant=variant):
                if variant == 'active':
                    latest = self.db.history.rows(self.rel)[-1]
                    self.db.history.write(self.rel, self.last, latest, True, latest['id'])
                elif variant == 'undated':
                    self.db.connection.execute('DELETE FROM relationship_history')
                    self.db.connection.commit()
                graph = self.graph_at(self.last if variant == 'ended' else None, variant == 'ended')
                before = copy.deepcopy(self.db.history.rows(self.rel))
                baseline = copy.deepcopy(self.db.relationship_records())
                view = graph.capture_state()
                with patch('story_atlas.graph_view.messagebox.askyesno', return_value=True):
                    dialog = graph.inspector.edit_selected()
                expected = before[-1] if before else baseline[0]
                self.assertEqual(dialog.variables['kind'].get(), expected['kind'])
                self.assertEqual(dialog.variables['inverse_label'].get(), expected['inverse_label'])
                dialog.notes.delete('1.0', 'end')
                dialog.notes.insert('1.0', 'Notes only ' + variant)
                self.assertTrue(dialog.save())
                dialog.destroy()
                self.app.update()
                expected['notes'] = 'Notes only ' + variant
                self.assertEqual(self.db.history.rows(self.rel), before)
                self.assertEqual(self.db.relationship_records(), baseline)
                self.assertEqual(graph.capture_state(), view)

    def test_graph_history_corrects_exact_effective_entry_and_returns_context(self):
        for scope, changes, key, label in ((None, False, str(self.enemy), 'Current'),
                (0, False, 'baseline', 'Before first event'),
                (self.first, False, str(self.ally), 'Alliance'),
                (self.middle, False, str(self.ally), 'Interlude'),
                (self.last, True, str(self.enemy), 'Conflict')):
            with self.subTest(scope=scope):
                graph = self.graph_at(scope, changes)
                graph.renderer.axes.set_xlim(-2, 2)
                graph.renderer.axes.set_ylim(-3, 3)
                view = graph.capture_state()
                before = copy.deepcopy(self.db.history.rows(self.rel))
                baseline = copy.deepcopy(self.db.relationship_records())
                history = graph.inspector.history_selected()
                self.app.update()
                self.assertEqual(history.as_of_id, scope)
                self.assertEqual(history.tree.selection(), (key,))
                self.assertIn(label, history.context.get())
                self.assertIn('baseline' if key == 'baseline' else 'state #' + key, history.context.get())
                editor = history.edit(True)
                self.assertEqual(editor.row['event_id'], None if key == 'baseline' else self.first if key == str(self.ally) else self.last)
                editor.notes.delete('1.0', 'end')
                note = 'Corrected from ' + label
                editor.notes.insert('1.0', note)
                editor.save()
                self.assertEqual(editor.step, 'review')
                editor.save()
                self.assertIsNone(history.editor)
                history.close()
                self.app.update()
                target = baseline[0] if key == 'baseline' else next(row for row in before if str(row['id']) == key)
                target['notes'] = note
                self.assertEqual(self.db.history.rows(self.rel), before)
                self.assertEqual(self.db.relationship_records(), baseline)
                self.assertEqual(graph.capture_state(), view)

    def test_real_wheel_dispatch_nearest_container_native_widgets_and_boundaries(self):
        for i in range(98):
            self.db.save_character(dict(name=f'Person {i:03}'))
        dialog = EventDialog(self.app.events, self.db, self.app.refresh)
        outer = next(child for child in dialog.winfo_children() if isinstance(child, ScrollFrame))
        inner = dialog.participants.list
        preview = dialog.participants.preview
        self.app.update()

        def dispatch(widget, expected, x=5, y=5, delta=-120):
            self.app.update()
            with patch.object(outer.canvas, 'yview_scroll', wraps=outer.canvas.yview_scroll) as out, patch.object(inner.canvas, 'yview_scroll', wraps=inner.canvas.yview_scroll) as inside:
                widget.event_generate('<MouseWheel>', delta=delta, x=x, y=y)
                self.app.update()
                self.assertEqual((out.call_count, inside.call_count), expected)

        first = dialog.participants.buttons[self.a]
        outer.canvas.yview_moveto(0)
        inner.canvas.yview_moveto(0)
        dispatch(first, (0, 1))
        self.assertGreater(inner.canvas.yview()[0], 0)
        # Padding to the right of the packed checkbox is actual list background.
        dispatch(inner.content, (0, 1), x=inner.content.winfo_width()-3, y=int(inner.canvas.canvasy(3)))
        inner.canvas.yview_moveto(1)
        self.app.update()
        bottom = inner.canvas.yview()
        dispatch(inner.content, (0, 1), x=inner.content.winfo_width()-3, y=int(inner.canvas.canvasy(3)))
        self.assertEqual(inner.canvas.yview(), bottom)
        outer.canvas.yview_moveto(1)
        self.app.update()
        set_read_only_text(preview, '\n'.join(f'Goal {i}' for i in range(100)))
        preview.see('1.0')
        dispatch(preview, (0, 0))
        self.assertGreater(preview.yview()[0], 0)
        dispatch(outer.content, (1, 0), x=outer.content.winfo_width()-3, y=int(outer.canvas.canvasy(3)), delta=120)
        # Native Treeview retains its own class wheel handling inside a form.
        tree = ttk.Treeview(outer.content, height=3)
        tree.pack(fill='x')
        for i in range(100):
            tree.insert('', 'end', text=str(i))
        self.app.update()
        outer.canvas.yview_moveto(1)
        self.app.update()
        dispatch(tree, (0, 0), y=35)
        self.assertGreater(tree.yview()[0], 0)
        last = list(dialog.participants.buttons.values())[-1]
        inner.canvas.yview_moveto(0)
        last.focus_force()
        self.app.update()
        self.assertGreater(inner.canvas.yview()[0], 0)
        self.assertGreaterEqual(last.winfo_rooty(), inner.canvas.winfo_rooty()-1)
        self.assertLessEqual(last.winfo_rooty()+last.winfo_height(), inner.canvas.winfo_rooty()+inner.canvas.winfo_height()+1)
        dialog.destroy()


if __name__ == '__main__':
    unittest.main()
