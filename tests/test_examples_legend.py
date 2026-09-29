"""Worked examples exercise story services and the actual Simple workspace."""
import tempfile
import unittest
from pathlib import Path
from matplotlib.colors import to_hex
from matplotlib.figure import Figure
from story_atlas.database import Database
from story_atlas.sample_story import create_sample, new_sample
from story_atlas.prometheus import create_prometheus
from story_atlas.graph import build_graph
from story_atlas.graph_render import GraphRenderer
from story_atlas.graph_legend import handles, EDGE_STYLES
from story_atlas.character_type import TYPE_COLORS
from story_atlas.graph_state import SavedViews, layout_positions
from story_atlas.introductions import visible_cast
from story_atlas.imports import read_export, import_payload
import test_simple_mode as baseline


class ExampleStorageTests(unittest.TestCase):
    def test_prometheus_chronology_and_uncertain_ending_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = create_prometheus(Path(folder) / 'prometheus.db')
            db = Database(path)
            try:
                self.assertEqual((len(db.characters()), len(db.events.list()), len(db.chapters.list())), (17, 20, 6))
                self.assertEqual(db.connection.execute("SELECT value FROM story_metadata WHERE key='title'").fetchone()[0], 'the modern prometheus')
                cast = {r['name']: r for r in db.characters()}
                creature = cast['The creature']['id']
                self.assertNotIn(creature, {r['id'] for r in visible_cast(db, 3)})
                self.assertIn(creature, {r['id'] for r in visible_cast(db, 4)})
                self.assertIn('unconfirmed', cast['The creature']['status'])
                self.assertEqual(set(r['character_type'] for r in cast.values()), set(TYPE_COLORS))
                bond = next(r['id'] for r in db.relationships(4) if r['kind'] == 'Abandonment')
                for event, expected in ((4, 'Abandonment'), (10, 'Conditional agreement'), (12, 'Broken promise'), (17, 'Pursuit')):
                    self.assertEqual(next(r['kind'] for r in db.relationships(event) if r['id'] == bond), expected)
                self.assertNotIn(bond, {r['id'] for r in db.relationships(19)})
                spouse = next(r['id'] for r in db.relationships(14) if r['kind'] == 'Spouse')
                self.assertNotIn(spouse, {r['id'] for r in db.relationships(15)})
                self.assertTrue(any(r['kind'] == 'Creator' for r in db.relationships(20)))
                self.assertEqual(len(SavedViews(db).names()), 7)
                for event in (0, *range(1, 21), None):
                    visible = {r['id'] for r in visible_cast(db, event)}
                    self.assertTrue(all({r['source_id'], r['target_id']} <= visible for r in db.relationships(event)))
                db.history.validate()
                export = Path(folder) / 'story.json'
                db.export_json(export)
                imported = Database(import_payload(read_export(export), Path(folder) / 'imported.db'))
                try:
                    self.assertEqual(imported.characters(), db.characters())
                    self.assertEqual(imported.history.rows(), db.history.rows())
                finally:
                    imported.close()
            finally:
                db.close()

    def test_greyhaven_uses_five_types_goals_and_explicit_link_categories(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(create_sample(Path(folder) / 'greyhaven.db'))
            try:
                self.assertEqual(set(r['character_type'] for r in db.characters()), set(TYPE_COLORS))
                self.assertTrue(all(r['goals'] for r in db.characters()))
                preset = SavedViews(db).load('Example overview')
                kinds = {r['kind'] for r in db.relationship_records()} | {r['kind'] for r in db.history.rows()}
                self.assertTrue(kinds <= preset['visual_categories'].keys())
                self.assertEqual(set(preset['visual_categories'].values()), set(EDGE_STYLES))
                self.assertEqual(preset['layout'], 'Circle')
            finally:
                db.close()

    def test_second_example_is_separate_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            first = new_sample(Path(folder), 'prometheus')
            before = first.read_bytes()
            second = new_sample(Path(folder), 'prometheus')
            self.assertNotEqual(first, second)
            with self.assertRaises(ValueError):
                create_prometheus(first)
            self.assertEqual(first.read_bytes(), before)

    def test_legend_dot_and_link_swatches_match_actual_renderer(self):
        swatches = handles()
        self.assertEqual([h.get_label() for h in swatches],
                         list(TYPE_COLORS) + list(EDGE_STYLES))
        for handle, color in zip(swatches, (*TYPE_COLORS.values(), *(v[0] for v in EDGE_STYLES.values()))):
            self.assertEqual(to_hex(handle.get_color()), color)
        graph = build_graph([dict(id=1, name='Player', character_type='Player'), dict(id=2, name='Merchant', character_type='Merchant')],
                            [dict(id=1, source_id=1, target_id=2, kind='Trade', semantics='mutual')])
        renderer = GraphRenderer(Figure())
        renderer.visual_categories = {'Trade': 'Support'}
        renderer.draw(graph, layout_positions(graph, {}, set()), set())
        self.assertEqual(to_hex(renderer.edge_artists[1].get_edgecolor()), EDGE_STYLES['Support'][0])
        self.assertEqual([t.get_text() for t in renderer.axes.get_legend().get_texts()], [h.get_label() for h in swatches])


class ExampleUITests(unittest.TestCase):
    setUp = baseline.SimpleUITests.setUp
    cleanup = baseline.SimpleUITests.cleanup

    def test_open_model_follow_bargain_and_create_a_test_connection(self):
        self.assertTrue(self.app.projects.try_sample('prometheus'))
        self.db = self.app.database
        self.app.update()
        ws = self.app.simple
        store = SavedViews(self.db)
        for name, expected in (('03 · The glacier bargain', 'Conditional agreement'),
                               ('04 · The promise breaks', 'Broken promise')):
            ws.graph.apply_state(store.load(name))
            self.app.update()
            self.assertTrue(any(d['kind'] == expected for *_, d in ws.graph.graph.edges(data=True)))
            self.assertEqual(ws.graph.visual_categories[expected], 'Support' if expected == 'Conditional agreement' else 'Conflict')
        legend = self.app.nametowidget(ws.classification_legend['menu'])
        labels = [legend.entrycget(i, 'label') for i in range(legend.index('end') + 1) if legend.type(i) != 'separator']
        self.assertTrue(any(label.startswith('DOTS') for label in labels))
        self.assertTrue(any(label.startswith('LINKS') for label in labels))
        ws.navigate(20)
        ws.graph.depth.set('Full graph')
        ws.graph.refresh(force=True)
        positions = list(ws.graph.positions.values())
        ws.new_character()
        task = ws.task
        self.assertNotIn(ws.graph.positions[-1], positions)
        task.fields['name'].set('Test reader')
        task.fields['character_type'].set('Neutral NPC')
        self.assertTrue(task.save())
        new_id = task.character_id
        ws.close_task()
        victor = next(r['id'] for r in self.db.characters() if r['name'] == 'Victor Frankenstein')
        ws.clear_selection()
        ws.choose_node(new_id, True)
        ws.choose_node(victor, True)
        ws.new_relationship()
        task = ws.task
        task.variables['kind'].set('Studies account of')
        task.variables['semantics'].set('Directional')
        self.assertFalse(task.save())  # Review first.
        self.assertTrue(task.save(), task.error.get())
        self.assertTrue(any(r['source_id'] == new_id and r['target_id'] == victor and r['kind'] == 'Studies account of' for r in self.db.relationships()))
        self.app.update()
        self.assertEqual(self.errors, [])
