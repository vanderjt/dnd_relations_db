"""Wheel dispatch and persisted legend categories through real connection tasks."""
import json
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from matplotlib.colors import to_rgba
import test_simple_mode as baseline
from story_atlas.database import Database
from story_atlas.imports import read_export, import_payload
from story_atlas.graph_legend import EDGE_STYLES
from story_atlas.scroll_frame import ScrollFrame
from story_atlas.relationship_dialog import RelationshipDialog


class CategoryStorageTests(unittest.TestCase):
    def test_categories_history_roundtrip_reopen_and_immediate_batch_undo(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / 'story.db')
            a, b = [db.save_character(dict(name=name)) for name in ('A', 'B')]
            event = db.events.save('Turn', '', 1)
            undo = db.enable_undo()
            for category in EDGE_STYLES:
                rows = db.relationship_store.batch([(a, b)], category, '', 'directional', '', event, category=category)
                self.assertEqual(rows[0]['category'], category)
                self.assertTrue(undo.apply())
                self.assertNotIn(rows[0]['id'], [r['id'] for r in db.relationships()])
                self.assertTrue(undo.apply(redo=True))
            row = db.relationship_records()[0]
            db.history.correct_baseline(row['id'], dict(row, category='Personal'), False)
            output = Path(folder) / 'export.json'
            db.export_json(output)
            expected = db.relationships(), db.history.rows()
            db.close()
            for path in (Path(folder) / 'story.db', import_payload(read_export(output), Path(folder) / 'copy.db')):
                reopened = Database(path)
                self.assertEqual((reopened.relationships(), reopened.history.rows()), expected)
                reopened.close()


class CategoryUITests(unittest.TestCase):
    setUp = baseline.SimpleUITests.setUp
    cleanup = baseline.SimpleUITests.cleanup
    cast = baseline.SimpleUITests.cast

    def test_batch_category_draft_review_and_rendered_color(self):
        a, b, c = self.cast()
        for ident in (a, b):
            self.ws.choose_node(ident, True)
        self.ws.new_relationship()
        task = self.ws.task
        self.assertEqual(tuple(task.boxes['category']['values']), tuple(EDGE_STYLES))
        task.variables['kind'].set('Friend')
        task.variables['semantics'].set('Mutual')
        task.category.set('Conflict')
        payload = task.draft_payload()
        task.category.set('Other')
        task.restore_draft(payload)
        self.assertEqual(task.category.get(), 'Conflict')
        self.assertFalse(task.save())
        self.assertIn('Category: Conflict', task.review_text.get('1.0', 'end'))
        self.assertTrue(task.save())
        self.app.update()
        row = self.db.relationships()[0]
        self.assertEqual(row['category'], 'Conflict')
        artist = self.ws.graph.renderer.edge_artists[row['id']]
        self.assertEqual(artist.get_edgecolor(), to_rgba(EDGE_STYLES['Conflict'][0]))
        # Another connection with the same descriptive type has its own category.
        other = self.db.save_relationship(a, c, 'Friend', category='Support')
        self.app.refresh()
        self.app.update()
        self.assertEqual(self.ws.graph.renderer.edge_artists[other].get_edgecolor(), to_rgba(EDGE_STYLES['Support'][0]))
        self.assertEqual(self.errors, [])

    def test_advanced_creation_has_category_and_preserves_it_on_edit(self):
        a, b, _ = self.cast()
        dialog = RelationshipDialog(self.app, self.db, self.app.refresh)
        for field, ident in (('source', a), ('target', b)):
            dialog.variables[field].set(next(label for label, value in dialog.choices.items() if value == ident))
        dialog.variables['kind'].set('Friend')
        dialog.variables['semantics'].set('Mutual')
        dialog.category.set('Personal')
        self.assertTrue(dialog.save())
        self.assertEqual(self.db.relationships()[0]['category'], 'Personal')
        dialog.destroy()

    def test_wheel_scrolls_nearest_pane_without_selecting_dropdown(self):
        dialog = tk.Toplevel(self.app)
        dialog.geometry('400x260')
        outer = ScrollFrame(dialog)
        outer.pack(fill='both', expand=True)
        inner = ScrollFrame(outer.content)
        inner.configure(height=150)
        inner.pack(fill='x')
        inner.pack_propagate(False)
        choice = tk.StringVar(dialog, 'Support')
        box = ttk.Combobox(inner.content, textvariable=choice, values=tuple(EDGE_STYLES), state='readonly')
        box.pack(fill='x')
        for index in range(30):
            ttk.Label(inner.content, text=str(index)).pack()
        ttk.Label(outer.content, text='More\n' * 30).pack()
        self.app.update()
        for delta in (-120, 120):
            inner.canvas.yview_moveto(0.4)
            with patch.object(inner.canvas, 'yview_scroll', wraps=inner.canvas.yview_scroll) as inside, patch.object(outer.canvas, 'yview_scroll', wraps=outer.canvas.yview_scroll) as outside:
                box.event_generate('<MouseWheel>', delta=delta, x=5, y=5)
                self.app.update()
                self.assertEqual(inside.call_count, 1)
                self.assertEqual(outside.call_count, 0)
                self.assertEqual(choice.get(), 'Support')
        box.current(2)
        box.event_generate('<<ComboboxSelected>>')
        self.assertEqual(choice.get(), 'Personal')
        dialog.destroy()
        self.assertEqual(self.errors, [])
