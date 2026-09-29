"""Simple-mode domain invariants and real Tk interaction regressions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from matplotlib.backend_bases import MouseEvent
from story_atlas.database import Database
from story_atlas.app import StoryAtlas
from story_atlas.story_setup import create_story
from story_atlas.introductions import visible_cast
from story_atlas.imports import read_export, import_payload
from story_atlas.selection import OrderedSelection
from story_atlas.settings import Settings


class SimpleStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        path = create_story(self.folder / 'story.db', 'My story', 'First', 'Opening')
        self.db = Database(path)
        self.addCleanup(self.db.close)
        self.first = self.db.events.list()[0]['id']
        self.later = self.db.events.save('Later', '', 2)
        self.a = self.db.save_character(dict(name='Same', introduction_event_id=self.first, narrative_role='protagonist'))
        self.b = self.db.save_character(dict(name='Same', introduction_event_id=self.later, narrative_role='antagonist'))
        self.c = self.db.save_character(dict(name='C'))

    def test_setup_isolation_visibility_and_current_roles(self):
        before = self.db.path.read_bytes()
        with self.assertRaises(ValueError):
            create_story(self.db.path, 'Bad', 'Bad')
        self.assertEqual(before, self.db.path.read_bytes())
        self.assertEqual([row['id'] for row in visible_cast(self.db, 0)], [self.c])
        self.assertEqual({row['id'] for row in visible_cast(self.db, self.first)}, {self.a, self.c})
        self.assertEqual(len(visible_cast(self.db, self.later)), 3)
        self.assertEqual([row['id'] for row in visible_cast(self.db, self.first, True) if row['planned']], [self.b])
        self.assertEqual(self.db.connection.execute("SELECT value FROM story_metadata WHERE key='title'").fetchone()[0], 'My story')

    def test_batch_preview_atomic_failure_and_mutual(self):
        payload = ([(self.a, self.b), (self.a, self.c)], 'Father', 'notes', 'directional', 'Child', self.later)
        initial = self.db.activity()
        self.assertEqual(len(self.db.relationship_store.batch(*payload, preview=True)), 2)
        self.assertEqual(self.db.relationship_records(), [])
        self.assertEqual(self.db.activity(), initial)
        with self.assertRaisesRegex(ValueError, 'introduced'):
            self.db.relationship_store.batch(*payload[:-1], self.first)
        self.assertEqual(self.db.relationship_records(), [])
        rows = self.db.relationship_store.batch(*payload)
        self.assertEqual(len(rows), 2)
        with self.assertRaises(ValueError):
            self.db.relationship_store.batch([(self.a, self.c), (self.a, self.b)], 'Father', '', 'directional', 'Child', self.later)
        self.assertEqual(len(self.db.relationship_records()), 2)
        self.db.relationship_store.batch([(self.b, self.c)], 'Friend', '', 'mutual', '', self.later)
        self.assertEqual(len(self.db.relationship_records()), 3)
        self.assertEqual(self.db.relationships(self.first), [])

    def test_early_relationship_introduction_edit_and_reorder_rollback(self):
        with self.assertRaisesRegex(ValueError, 'introduced'):
            self.db.save_relationship(self.a, self.b, 'Friend', start_event=self.first)
        rel = self.db.save_relationship(self.a, self.c, 'Friend', start_event=self.first)
        with self.assertRaisesRegex(ValueError, 'introduced'):
            self.db.save_character(dict(name='Same', introduction_event_id=self.later), self.a)
        self.assertEqual(self.db.characters()[1]['introduction_event_id'], self.first)
        self.db.save_relationship(self.b, self.c, 'Ally', start_event=self.later)
        # Move introduction later than a separate connection beginning.
        end = self.db.events.save('After', '', 3)
        self.db.save_relationship(self.a, self.b, 'Mentor', start_event=end)
        before = self.db.events.list()
        with self.assertRaisesRegex(ValueError, 'introduced'):
            self.db.events.move(self.later, 1)
        self.assertEqual(self.db.events.list(), before)
        self.assertEqual(self.db.history.editing_state(rel)['kind'], 'Friend')

    def test_roundtrip_trash_backup_and_legacy_defaults(self):
        self.db.save_relationship(self.a, self.b, 'Ally', start_event=self.later)
        output = self.folder / 'export.json'
        self.db.export_json(output)
        self.assertEqual(json.loads(output.read_text())['format_version'], 9)
        imported = Database(import_payload(read_export(output), self.folder / 'imported.db'))
        try:
            self.assertEqual(imported.characters(), self.db.characters())
        finally:
            imported.close()
        self.db.delete_character(self.b)
        self.db.trash.restore('character', self.b)
        self.assertEqual(next(row for row in self.db.characters() if row['id'] == self.b)['introduction_event_id'], self.later)
        with self.assertRaises(ValueError):
            self.db.save_character(dict(name='Invalid', narrative_role='evil'))

    def test_ordered_duplicate_names_and_source(self):
        selection = OrderedSelection()
        for ident in (self.a, self.b, self.c):
            selection.select(ident, True)
        self.assertEqual(selection.pairs(), [(self.a, self.b), (self.a, self.c)])
        selection.source(self.c)
        self.assertEqual(selection.pairs(), [(self.c, self.a), (self.c, self.b)])
        selection.select(self.a, True)
        self.assertEqual(selection.ids, [self.c, self.b])

    def test_event_removal_requires_review_and_reassigns_trash_references(self):
        self.db.delete_character(self.b)
        self.db.drafts.save(None, dict(name='Future draft', introduction_event_id=self.later))
        preview = self.db.events.removal_preview(self.later, self.first)
        self.assertEqual(preview['introductions'][0]['id'], self.b)
        self.db.events.remove(preview)
        self.db.trash.restore('character', self.b)
        self.assertEqual(next(row for row in self.db.characters() if row['id'] == self.b)['introduction_event_id'], self.first)
        self.assertEqual(len(self.db.events.list()), 1)
        self.assertEqual(self.db.drafts.list()[0]['values']['introduction_event_id'], self.first)

    def test_conflicting_event_removal_rolls_back_and_backup_roundtrip(self):
        from story_atlas.backup import snapshot, restore_backup
        rel = self.db.save_relationship(self.a, self.c, 'Friend', start_event=self.first)
        self.db.history.write(rel, self.later, dict(source_id=self.a, target_id=self.c, kind='Enemy'))
        before = self.db.events.list(), self.db.history.rows(), self.db.characters()
        with self.assertRaisesRegex(ValueError, 'same relationship'):
            self.db.events.remove(self.db.events.removal_preview(self.first, self.later))
        self.assertEqual((self.db.events.list(), self.db.history.rows(), self.db.characters()), before)
        backup = snapshot(self.db.connection, self.db.path)
        restored = Database(restore_backup(backup, self.folder / 'restored.db'))
        try:
            self.assertEqual(restored.characters(), self.db.characters())
        finally:
            restored.close()

    def test_v8_migration_backs_up_preserves_cast_and_relationships(self):
        import sqlite3
        from story_atlas.migrations import MIGRATIONS, CURRENT_VERSION
        from story_atlas.backup import backup_directory
        path = self.folder / 'v8.db'
        connection = sqlite3.connect(path)
        for migration in MIGRATIONS[:8]:
            migration(connection)
        connection.execute("INSERT INTO characters(id,name) VALUES (7,'Legacy'),(8,'Legacy')")
        connection.execute("INSERT INTO relationships(source_id,target_id,kind) VALUES (7,8,'Family')")
        connection.execute('PRAGMA user_version=8')
        connection.commit()
        connection.close()
        migrated = Database(path)
        try:
            self.assertEqual(migrated.connection.execute('PRAGMA user_version').fetchone()[0], CURRENT_VERSION)
            self.assertEqual(len(visible_cast(migrated, 0)), 2)
            self.assertTrue(all(row['introduction_event_id'] is None and row['narrative_role'] == 'neutral' for row in migrated.characters()))
            self.assertEqual(migrated.relationships(0)[0]['kind'], 'Family')
            self.assertTrue(list(backup_directory(path).glob('pre-migration-v8*.db')))
        finally:
            migrated.close()


class SimpleUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        create_story(folder / 'story.db', 'Simple fixture', 'Chapter 1')
        Settings(folder / 'settings.json').save(mode='Simple')
        self.app = StoryAtlas(folder / 'story.db', folder / 'settings.json')
        self.app.tk.call('tk', 'scaling', 96 / 72)
        self.app.set_appearance('dark', 10)
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.addCleanup(self.cleanup)
        self.app.update()
        self.app.focus_force()
        self.app.update()
        self.ws = self.app.simple
        self.db = self.app.database
        self.first = self.db.events.list()[0]['id']
        self.ws.navigate(self.first)

    def cleanup(self):
        if self.app.simple.task and hasattr(self.app.simple.task, 'draft'):
            self.app.simple.task.draft.cancel()
        self.app.destroy()
        self.db.close()

    def cast(self):
        ids = [self.db.save_character(dict(name=name)) for name in ('Alden', 'Bryn', 'Cora')]
        self.app.refresh()
        self.app.update()
        return ids

    def test_provisional_save_cancel_draft_and_position(self):
        self.ws.new_character()
        task = self.ws.task
        self.assertIn(-1, self.ws.graph.graph)
        task.fields['name'].set('Hero')
        task.fields['goals'].insert('1.0', 'Keep the gate open')
        task.draft.flush()
        self.assertEqual(self.db.drafts.list()[0]['values']['introduction_event_id'], self.first)
        self.ws.graph.positions[-1] = [.35, .7]
        self.assertTrue(task.save())
        self.assertEqual(self.ws.graph.positions[task.character_id], [.35, .7])
        self.assertNotIn(-1, self.ws.graph.graph)
        self.assertEqual(self.db.drafts.list(), [])
        self.ws.close_task()
        self.ws.new_character()
        self.assertTrue(self.ws.cancel_task())
        self.assertEqual(len(self.db.characters()), 1)
        self.assertNotIn(-1, self.ws.graph.graph)
        self.app.update()
        self.assertEqual(self.errors, [])

    def test_batch_review_clear_focus_stay_open_failure_retention(self):
        ids = self.cast()
        for ident in ids:
            self.ws.choose_node(ident, True)
        self.ws.new_relationship()
        task = self.ws.task
        task.variables['kind'].set('Father')
        task.variables['semantics'].set('Directional')
        task.variables['inverse_label'].set('Child')
        self.assertFalse(task.save())
        self.assertIn('Cora', task.review_text.get('1.0', 'end'))
        self.assertTrue(task.save())
        self.app.update()
        self.assertIs(self.ws.task, task)
        self.assertEqual(self.ws.ordered.ids, [])
        self.assertTrue(all(not task.variables[key].get() for key in ('source', 'target', 'kind', 'inverse_label')))
        self.assertEqual(task.variables['semantics'].get(), 'Mutual')
        self.assertIn(task.variables['event'].get(), task.events)
        self.assertEqual(task.targets, [])
        self.assertEqual(self.app.focus_get(), task.boxes['source'].search)
        self.assertEqual(len(self.db.relationship_records()), 2)
        self.ws.ordered.ids = ids.copy()
        task.use_selection()
        task.use_event()
        task.variables['kind'].set('Father')
        task.variables['semantics'].set('Directional')
        before = task.values()
        self.assertFalse(task.save())
        self.assertEqual(task.values(), before)
        self.assertEqual(self.ws.ordered.ids, ids)
        self.assertEqual(len(self.db.relationship_records()), 2)

    def test_navigation_cancel_hidden_future_layout_and_no_writes(self):
        a, b, c = self.cast()
        later = self.db.events.save('Future', '', 2)
        self.db.save_character(dict(name='Cora', introduction_event_id=later), c)
        self.ws.navigate(later)
        positions = dict(self.ws.graph.positions)
        limits = self.ws.graph.renderer.axes.get_xlim()
        before = self.db.activity()
        self.ws.navigate(self.first)
        self.assertNotIn(c, self.ws.graph.graph)
        self.assertEqual(self.ws.graph.positions[c], positions[c])
        self.ws.graph.show_planned.set(True)
        self.ws.graph.refresh(force=True)
        self.assertTrue(self.ws.graph.graph.nodes[c]['planned'])
        self.ws.navigate(later)
        self.assertEqual(self.ws.graph.positions, positions)
        self.assertEqual(self.ws.graph.renderer.axes.get_xlim(), limits)
        self.assertEqual(self.db.activity(), before)
        self.ws.edit_character(a)
        self.ws.task.fields['name'].set('Unsaved')
        with patch('story_atlas.simple_workspace.save_discard_stay', return_value=None):
            self.assertFalse(self.ws.navigate(self.first))
        self.assertEqual(self.ws.graph.as_of_id, later)
        self.assertIn('Future', self.ws.timeline.event.get())
        self.assertEqual(self.ws.task.fields['name'].get(), 'Unsaved')

    def test_mode_switch_unsaved_and_existing_preferences(self):
        self.ws.new_character()
        self.ws.task.fields['name'].set('Not yet')
        self.app.mode.set('Advanced')
        with patch('story_atlas.simple_workspace.save_discard_stay', return_value=None):
            self.assertFalse(self.app.switch_mode())
        self.assertEqual(self.app.mode.get(), 'Simple')
        with patch('story_atlas.simple_workspace.save_discard_stay', return_value=False):
            self.app.mode.set('Advanced')
            self.assertTrue(self.app.switch_mode())
        self.assertEqual(self.app.settings.values['mode'], 'Advanced')
        self.assertEqual(self.db.characters(), [])

    def test_event_chapter_commit_and_exact_state_correction(self):
        a, b, c = self.cast()
        rel = self.db.save_relationship(a, b, 'Friend', start_event=self.first)
        self.ws.new_event(True)
        self.ws.task.chapter.set('Chapter 2')
        self.ws.task.title.set('Conflict')
        self.assertTrue(self.ws.task.save())
        second = self.ws.graph.as_of_id
        self.assertEqual(len(self.db.relationships(second)), 1)
        self.ws.state_task(rel, False)
        self.ws.task.variables['kind'].set('Enemy')
        self.ws.task.variables['presence'].set('Ended')
        self.assertFalse(self.ws.task.save())
        self.assertTrue(self.ws.task.save())
        self.ws.navigate(None)
        self.ws.state_task(rel, True)
        task = self.ws.task
        self.assertEqual(task.variables['kind'].get(), 'Enemy')
        before = self.db.history.editing_state(rel)
        task.notes.insert('end', 'Only notes changed')
        self.assertFalse(task.save())
        self.assertTrue(task.save())
        after = self.db.history.editing_state(rel)
        self.assertEqual({k:v for k,v in before.items() if k != 'notes'}, {k:v for k,v in after.items() if k != 'notes'})
        self.ws.navigate(self.first)
        self.ws.state_task(rel, True)
        self.assertEqual(self.ws.task.variables['kind'].get(), 'Friend')

    def test_mouse_shift_pan_zoom_and_node_drag(self):
        ids = self.cast()
        graph = self.ws.graph
        graph.canvas.draw()
        def event(name, x, y, button=1, key=None):
            result = MouseEvent(name, graph.canvas, x, y, button=button, key=key)
            graph.canvas.callbacks.process(name, result)
        for ident in ids:
            x, y = graph.renderer.axes.transData.transform(graph.positions[ident])
            event('button_press_event', x, y, key='shift')
            event('button_release_event', x, y, key='shift')
        self.assertEqual(self.ws.ordered.ids, ids)
        self.assertFalse(graph.drag)
        x, y = graph.renderer.axes.transData.transform(graph.positions[ids[0]])
        event('button_press_event', x, y)
        event('motion_notify_event', x+25, y-20)
        event('button_release_event', x+25, y-20)
        self.assertIn(ids[0], graph.pins)
        before = graph.renderer.axes.get_xlim()
        event('scroll_event', x, y, button='up')
        self.assertNotEqual(graph.renderer.axes.get_xlim(), before)
        graph.canvas.draw()
        box = graph.renderer.axes.bbox
        x, y = box.x0 + 10, box.y0 + 10
        event('button_press_event', x, y)
        self.assertIsNotNone(graph.pan_start)
        before = graph.renderer.axes.get_xlim()
        event('motion_notify_event', x + 20, y + 20)
        event('button_release_event', x + 20, y + 20)
        self.assertNotEqual(graph.renderer.axes.get_xlim(), before)
        self.assertEqual(self.errors, [])

    def test_dense_simple_graph_themes_resize_and_scrub_read_only(self):
        from types import SimpleNamespace
        import time
        ids = [self.db.save_character(dict(name=f'Cast {i}')) for i in range(100)]
        for i, ident in enumerate(ids):
            for step in (1, 2, 99):
                self.db.save_relationship(ident, ids[(i + step) % 100], f'Type {step}')
        started = time.perf_counter()
        self.app.refresh()
        self.app.update()
        self.ws.graph.fit_graph()
        self.assertEqual(len(self.ws.graph.graph), 100)
        self.assertEqual(self.ws.graph.graph.number_of_edges(), 300)
        print(f'Simple 100/300 draw: {time.perf_counter()-started:.3f}s')
        selection = self.db.relationship_records()[37]['id']
        self.ws.graph.select_edge(selection)
        self.assertEqual(self.ws.graph.inspector.relationship_id, selection)
        before = self.db.activity()
        writes = self.db.connection.total_changes
        self.ws.timeline.scrub(SimpleNamespace(x=16))
        self.ws.timeline.release()
        self.assertEqual(self.ws.graph.as_of_id, 0)
        self.assertEqual(self.db.connection.total_changes, writes)
        self.assertEqual(self.db.activity(), before)
        for mode, size in (('light', 14), ('dark', 10)):
            self.app.geometry('900x650')
            self.app.set_appearance(mode, size)
            self.app.update()
            self.ws.new_character()
            self.app.update()
            editor = self.ws.task.editor
            self.assertGreater(editor.winfo_height(), 80)
            self.assertLess(self.ws.timeline.winfo_rooty(), self.app.winfo_rooty() + self.app.winfo_height())
            self.ws.cancel_task()
        self.assertEqual(self.errors, [])
