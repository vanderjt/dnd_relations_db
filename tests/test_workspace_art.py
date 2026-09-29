"""Workspace imagery preserves records, drafts and useful compact reading space."""
from io import BytesIO
from hashlib import sha256
from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch
from PIL import Image
from story_atlas.app import StoryAtlas
from story_atlas.tree_art import portrait_photo


class WorkspaceArtTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = StoryAtlas(Path(self.temp.name) / 'story.db')
        self.addCleanup(self.cleanup)
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.ident = self.app.database.save_character({'name': 'Aster', 'character_type': 'Player'})
        self.app.refresh()
        self.app.characters.load(self.app.database.characters()[0])
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_portrait_miss_can_recover_without_restarting(self):
        data = BytesIO()
        Image.new('RGB', (16, 16), 'teal').save(data, format='PNG')
        content = data.getvalue()
        filename = sha256(content).hexdigest() + '.png'
        tree = self.app.characters.tree
        self.assertIsNone(portrait_photo(tree, self.app.database, filename))
        self.app.database.connection.execute('INSERT INTO portrait_assets VALUES (?,?)', (filename, content))
        self.assertIsNotNone(portrait_photo(tree, self.app.database, filename))

    def test_minimal_changes_only_images_preserves_selection_values_and_dirty_form(self):
        view = self.app.characters
        view.tree.selection_set(str(self.ident))
        self.app.update()
        view.edit_profile()
        view.fields['name'].set('Unsaved Aster')
        before = view.tree.item(str(self.ident), 'values')
        view.tree.atlas_refresh_art()
        self.assertTrue(view.tree.item(str(self.ident), 'image'))
        self.app.set_appearance('light', 10, 'Minimal')
        self.app.update()
        self.assertEqual(view.fields['name'].get(), 'Unsaved Aster')
        self.assertEqual(view.tree.item(str(self.ident), 'values'), before)
        self.assertEqual(view.tree.selection(), (str(self.ident),))
        self.assertFalse(view.tree.item(str(self.ident), 'image'))
        self.assertNotIn('Not set', view.overview.details.cget('text'))
        self.assertFalse(self.errors)

    def test_all_advanced_workspaces_retain_reading_region_at_minimum(self):
        other = self.app.database.save_character({'name': 'Bryn'})
        self.app.database.save_relationship(self.ident, other, 'Friend')
        self.app.refresh()
        self.app.geometry('760x480')
        self.app.set_appearance('dark', 16)
        for view, region in ((self.app.events, self.app.events.detail_scroller.canvas),
                             (self.app.relationships, self.app.relationships.tree),
                             (self.app.graph, self.app.graph.canvas.get_tk_widget())):
            self.app.tabs.select(view)
            self.app.update()
            self.assertGreaterEqual(region.winfo_height(), 100, type(view).__name__)
        self.assertFalse(self.errors)

    def test_compact_profile_has_reading_space_and_timeline_stays_inside_canvas(self):
        self.app.geometry('760x480')
        self.app.set_appearance('dark', 16)
        self.app.update()
        self.assertGreaterEqual(self.app.characters.overview.scroller.canvas.winfo_height(), 100)
        self.app.mode.set('Simple')
        self.app.apply_mode()
        self.app.update()
        timeline = self.app.simple.timeline
        timeline.draw()
        height = timeline.canvas.winfo_height()
        for item in timeline.canvas.find_all():
            bounds = timeline.canvas.bbox(item)
            self.assertLessEqual(bounds[3], height + 2)
        graph = self.app.simple.graph
        legend = graph.renderer.axes.get_legend()
        self.assertTrue(legend is None or not legend.get_visible())
        graph.classification_filter = 'Player'
        self.app.simple.refresh_context()
        self.assertIn('Player', self.app.simple.context.get())
        self.assertTrue(self.app.simple.context_label.winfo_manager())
        self.assertFalse(self.errors)

    def test_compact_graph_export_includes_scope_and_restores_canvas(self):
        graph = self.app.graph
        long_name = 'Aster the remarkably long named wandering chronicler'
        row = self.app.database.characters()[0]
        self.app.database.save_character(dict(row, name=long_name), row['id'])
        self.app.tabs.select(graph)
        self.app.geometry('760x480')
        self.app.set_appearance('dark', 16)
        self.app.update()
        graph.refresh(force=True)
        self.app.update()
        before_size = tuple(graph.figure.get_size_inches())
        before_state = graph.capture_state()
        path = Path(self.temp.name) / 'graph.png'
        seen = []
        def exported(*args, **kwargs):
            seen.append(graph.figure._suptitle.get_visible())
            self.assertIn(long_name, graph.renderer.node_labels[self.ident].get_text())
            legend = graph.renderer.axes.get_legend()
            self.assertTrue(legend is None or legend.get_visible())
        with patch('story_atlas.graph_actions.filedialog.asksaveasfilename', return_value=str(path)), patch.object(graph.figure, 'savefig', side_effect=exported):
            graph.export()
        self.assertEqual(seen, [True])
        self.assertEqual(tuple(graph.figure.get_size_inches()), before_size)
        self.assertEqual(graph.capture_state(), before_state)
        self.assertFalse(graph.figure._suptitle.get_visible())
        self.assertNotIn(long_name, graph.renderer.node_labels[self.ident].get_text())

    def test_compact_navigation_menu_indicates_active_tool(self):
        controls = self.app.graph.controls
        controls.actions.invoke(0)
        self.assertTrue(controls.zoom_active.get())
        self.assertFalse(controls.pan_active.get())
        controls.actions.invoke(1)
        self.assertFalse(controls.zoom_active.get())
        self.assertTrue(controls.pan_active.get())
        controls.actions.invoke(1)
        self.assertFalse(controls.zoom_active.get())
        self.assertFalse(controls.pan_active.get())
        controls.toggle('zoom')
        controls.clear_mode()
        self.assertFalse(controls.zoom_active.get())

    def test_greyhaven_planned_graph_first_map_uses_compact_summary(self):
        from story_atlas.sample_story import create_sample
        from tools.capture_gui_overhaul import prepare_release_state, settle
        folder = Path(self.temp.name)
        path = folder / 'greyhaven.db'
        create_sample(path)
        settings = folder / 'planned-settings.json'
        settings.write_text(json.dumps(dict(theme='dark', mode='Advanced', text_size=16)))
        app = StoryAtlas(path, settings_path=settings)
        try:
            app.refresh()
            app.geometry('760x480')
            prepare_release_state(app, 'planned', 'Advanced')
            settle(app)
            graph = app.graph
            self.assertTrue(graph._compact)
            self.assertIn('Planned cast', graph.summary.cget('text'))
            self.assertNotIn('Full historical graph:', graph.summary.cget('text'))
            self.assertGreaterEqual(graph.canvas.get_tk_widget().winfo_height(), 100)
            self.assertFalse(graph.controls.master.winfo_ismapped())
            menu_labels = [graph.filter_menu.entrycget(i, 'label') for i in range(graph.filter_menu.index('end') + 1) if graph.filter_menu.type(i) != 'separator']
            self.assertIn('Graph navigation & layout', menu_labels)
            planned = next(ident for ident, row in graph.graph.nodes(data=True) if row.get('planned'))
            graph.select_node(planned)
            self.assertTrue(graph.renderer.node_labels[planned].get_visible())
            self.assertIn('Planned visual review witness', graph.inspector.heading.cget('text'))
            prepare_release_state(app, 'relationships', 'Advanced')
            settle(app)
            tree = app.relationships.roster.tree
            selected = tree.selection()[0]
            tree.see(selected)
            app.update()
            self.assertTrue(tree.bbox(selected), 'Selected cast row must remain visible below heading')
        finally:
            app.database.close()
            app.destroy()

    def test_renderer_density_adapts_to_canvas_and_keeps_selection(self):
        from matplotlib.figure import Figure
        import networkx as nx
        from story_atlas.graph_render import GraphRenderer
        graph = nx.MultiDiGraph()
        for ident in range(18):
            graph.add_node(ident, name=f'Character {ident}', character_type='Player')
        figure = Figure(figsize=(9, 6), dpi=100)
        renderer = GraphRenderer(figure)
        renderer.draw(graph, nx.circular_layout(graph), set(), text_size=10)
        self.assertTrue(all(label.get_visible() for label in renderer.node_labels.values()))
        figure.set_size_inches(4, 1.14)
        renderer.layout_legend()
        self.assertFalse(any(label.get_visible() for label in renderer.node_labels.values()))
        renderer.highlight(('node', 3))
        self.assertTrue(renderer.node_labels[3].get_visible())
        self.assertFalse(renderer.node_labels[4].get_visible())
        renderer.pins.add(4)
        renderer.ordered_selection = [5]
        renderer.highlight(('node', 3))
        self.assertTrue(renderer.node_labels[4].get_visible())
        self.assertTrue(renderer.node_labels[5].get_visible())
        # Provisional cleanup removes model positions before the queued redraw.
        renderer.positions.pop(4)
        renderer.highlight(('node', 3))
        self.assertTrue(renderer.node_labels[4].get_visible())

    def test_sparse_long_names_remain_separate_inside_narrow_canvas(self):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        import networkx as nx
        from story_atlas.graph_render import GraphRenderer
        graph = nx.MultiDiGraph()
        graph.add_node(1, name='Bryn', character_type='Neutral NPC')
        graph.add_node(2, name='Alden · keeper of the harbour chronicle', character_type='Neutral NPC')
        figure = Figure(figsize=(3.56, 1.8), dpi=100)
        canvas = FigureCanvasAgg(figure)
        renderer = GraphRenderer(figure)
        renderer.draw(graph, {1: (-1, 0), 2: (1, 0)}, set(), text_size=16)
        canvas.draw()
        bounds = [label.get_window_extent(canvas.get_renderer()) for label in renderer.node_labels.values()]
        self.assertFalse(bounds[0].overlaps(bounds[1]))
        for box in bounds:
            self.assertGreaterEqual(box.x0, 0)
            self.assertLessEqual(box.x1, figure.bbox.width)
