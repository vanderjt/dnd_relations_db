"""Unified type persistence and incremental placement, using disposable stories."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from itertools import combinations
import test_simple_mode as baseline
from story_atlas.database import Database
from story_atlas.migrations import MIGRATIONS
from story_atlas.imports import read_export, import_payload
from story_atlas.character_type import CHARACTER_TYPES
from story_atlas.node_placement import free_position


class StorageTests(unittest.TestCase):
    def test_version_eleven_type_mapping_including_trashed_characters(self):
        from story_atlas.legacy_character_type import CHARACTER_TYPES as OLD_TYPES, LEGACY_TYPES
        from story_atlas.character_type import validate
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'v11.db'
            con = sqlite3.connect(path)
            for migration in MIGRATIONS[:11]:
                migration(con)
            for value in (*OLD_TYPES, *LEGACY_TYPES):
                con.execute("INSERT INTO characters(name,character_type,deleted_at) VALUES (?,?, '2026-09-24')", (value, value))
            con.execute('PRAGMA user_version=11')
            con.commit()
            con.close()
            db = Database(path)
            try:
                for row in db.connection.execute('SELECT * FROM characters'):
                    self.assertEqual(row['character_type'], validate(row['name']))
                    self.assertEqual(row['legacy_character_type'], row['name'])
                    self.assertEqual(row['deleted_at'], '2026-09-24')
                self.assertTrue(list(path.parent.rglob('pre-migration-v11*.db')))
            finally:
                db.close()

    def test_migration_preserves_combined_labels_and_roundtrips_all_types(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'legacy.db'
            con = sqlite3.connect(path)
            for migration in MIGRATIONS[:10]:
                migration(con)
            con.execute("INSERT INTO characters(name,classification,narrative_role) VALUES ('Combined','NPC Ally','protagonist')")
            con.execute("INSERT INTO characters(name,narrative_role) VALUES ('Lead','antagonist')")
            con.execute('PRAGMA user_version=10')
            con.commit()
            con.close()
            db = Database(path)
            try:
                rows = db.characters()
                self.assertEqual(rows[0]['character_type'], 'Allied NPC')
                self.assertEqual(rows[1]['character_type'], 'Enemy NPC')
                self.assertEqual(rows[0]['narrative_role'], 'protagonist')
                self.assertEqual(rows[0]['legacy_character_type'], 'NPC Ally · Protagonist')
                self.assertTrue(list(path.parent.rglob('pre-migration-v10*.db')))
                for label in CHARACTER_TYPES:
                    ident = db.save_character(dict(name=label, character_type=label))
                    copy = db.duplicate_character(ident)
                    db.delete_character(copy)
                    db.trash.restore('character', copy)
                    self.assertEqual(next(r for r in db.characters() if r['id'] == copy)['character_type'], label)
                export = path.with_suffix('.json')
                db.export_json(export)
                imported = Database(import_payload(read_export(export), path.parent / 'imported.db'))
                try:
                    self.assertEqual(imported.characters(), db.characters())
                finally:
                    imported.close()
            finally:
                db.close()

    def test_free_positions_include_hidden_nodes_and_zoomed_coordinates(self):
        positions = {0: [1000, -500]}
        for ident in range(1, 60):
            positions[ident] = free_position(positions, (999, 1001), (-501, -499), (800, 500))
        self.assertEqual(positions[0], [1000, -500])
        for a, b in combinations(positions.values(), 2):
            self.assertGreaterEqual(((a[0] - b[0]) * 400 / 135) ** 2 + ((a[1] - b[1]) * 250 / 85) ** 2, .989)


class UITests(unittest.TestCase):
    setUp = baseline.SimpleUITests.setUp
    cleanup = baseline.SimpleUITests.cleanup

    def test_exact_type_options_unique_more_actions_and_round_default(self):
        import tkinter as tk
        from tkinter import ttk
        self.assertEqual(self.ws.graph.layout.get(), 'Circle')
        self.assertEqual(self.app.graph.layout.get(), 'Circle')
        self.ws.new_character()
        expected = ('Player', 'Merchant', 'Allied NPC', 'Neutral NPC', 'Enemy NPC')
        self.assertEqual(tuple(self.ws.task.editor.field_widgets['character_type']['values']), expected)
        self.assertEqual(tuple(self.app.characters.editor.field_widgets['character_type']['values']), expected)
        self.assertEqual(self.ws.task.fields['character_type'].get(), 'Neutral NPC')
        menu_button = next(w for w in self.ws.ribbon.items if isinstance(w, ttk.Menubutton) and w['text'] == 'More')
        menu = self.app.nametowidget(menu_button['menu'])
        labels = [menu.entrycget(i, 'label') for i in range(menu.index('end') + 1) if menu.type(i) != 'separator']
        for duplicate in ('New event', 'Next event', 'Character selection controls', 'Character type · current'):
            self.assertNotIn(duplicate, labels)
        for unique in ('Fit view', 'Export displayed graph…', 'Saved graph views…'):
            self.assertIn(unique, labels)
        self.app.geometry('900x600')
        self.app.update()
        for text in ('New event', 'Next event'):
            button = next(w for w in self.ws.ribbon.items if w['text'] == text)
            self.assertTrue(button.winfo_viewable())
        self.assertTrue(self.ws.selection_toggle.winfo_viewable())

    def test_one_type_control_prompts_and_old_draft_recovery(self):
        from story_atlas.simple_profile import SimpleProfile
        self.ws.new_character()
        task = self.ws.task
        self.assertIn('character_type', task.editor.field_widgets)
        self.assertNotIn('classification', task.editor.field_widgets)
        self.assertNotIn('narrative_role', task.editor.field_widgets)
        self.assertIs(task.editor.template, task.fields['character_type'])
        task.fields['name'].set('Lead')
        task.fields['character_type'].set('Player')
        self.assertEqual(task.fields['summary'].get('1.0', 'end-1c'), '')
        task.editor.apply_template()
        self.assertIn('central conflict', task.fields['summary'].get('1.0', 'end-1c'))
        self.assertTrue(task.save())
        ident = task.character_id
        self.ws.close_task()
        self.ws.edit_character(ident)
        self.assertEqual(self.ws.task.fields['character_type'].get(), 'Player')
        self.assertTrue(self.ws.can_leave())
        self.ws.close_task()
        recovered = dict(name='Legacy draft', classification='Player Enemy', narrative_role='antagonist')
        task = self.ws.mount(lambda: SimpleProfile(self.ws.host, self.ws, recovered=recovered))
        self.assertEqual(task.fields['character_type'].get(), 'Player')
        self.assertTrue(task.save())
        self.assertEqual(self.db.characters()[1]['character_type'], 'Player')
        self.assertNotIn('narrative_role', self.app.characters.editor.field_widgets)
        self.assertEqual(self.errors, [])

    def test_consecutive_creations_keep_positions_and_do_not_overlap(self):
        positions = {}
        for index in range(12):
            self.ws.new_character()
            self.app.update()
            point = list(self.ws.graph.positions[-1])
            self.assertNotIn(point, positions.values())
            task = self.ws.task
            task.fields['name'].set(f'Character {index}')
            task.fields['character_type'].set('Neutral NPC')
            self.assertTrue(task.save())
            self.app.update()
            self.assertEqual(self.ws.graph.positions[task.character_id], point)
            for ident, old in positions.items():
                self.assertEqual(self.ws.graph.positions[ident], old)
            positions[task.character_id] = point
            self.ws.close_task()
        axes = self.ws.graph.renderer.axes
        for a, b in combinations(positions.values(), 2):
            dx = (a[0] - b[0]) / (axes.get_xlim()[1] - axes.get_xlim()[0]) * axes.bbox.width
            dy = (a[1] - b[1]) / (axes.get_ylim()[1] - axes.get_ylim()[0]) * axes.bbox.height
            self.assertGreaterEqual((dx / 135) ** 2 + (dy / 85) ** 2, .98)
        self.assertEqual(self.errors, [])

    def test_direct_creation_gets_free_space_without_moving_existing_nodes(self):
        first = self.db.save_character(dict(name='First'))
        self.app.refresh()
        self.app.update()
        before = list(self.ws.graph.positions[first])
        second = self.db.save_character(dict(name='Second'))
        self.app.refresh()
        self.app.update()
        self.assertEqual(self.ws.graph.positions[first], before)
        self.assertNotEqual(self.ws.graph.positions[second], before)
