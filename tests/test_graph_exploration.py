"""Graph queries, view persistence, and interaction/refresh regression tests."""
import copy
import json
from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch
from matplotlib.backend_bases import MouseEvent

from story_atlas.app import StoryAtlas
from story_atlas.graph import build_graph
from story_atlas.graph_state import filter_graph, layout_positions, SavedViews, validate_view
from story_atlas.database import Database
from story_atlas.backup import snapshot, restore_backup


def fixture_graph():
    characters = [dict(id=node, name=str(node)) for node in range(1, 6)]
    relationships = [dict(id=ident, source_id=source, target_id=target, kind=kind)
                     for ident, source, target, kind in ((1, 1, 2, "Friend"), (2, 2, 1, "Rival"),
                         (3, 1, 2, "Family"), (4, 2, 3, "Friend"), (5, 4, 1, "Mentor"))]
    return build_graph(characters, relationships)


class GraphQueryTests(unittest.TestCase):
    def test_direction_depth_types_and_isolates(self):
        graph = fixture_graph()
        outgoing = filter_graph(graph, 1, "Direct", "Outgoing")
        self.assertEqual(set(outgoing), {1, 2})
        self.assertEqual({key for _, _, key in outgoing.edges(keys=True)}, {1, 3})
        incoming = filter_graph(graph, 1, "Direct", "Incoming")
        self.assertEqual(set(incoming), {1, 2, 4})
        self.assertEqual({key for _, _, key in incoming.edges(keys=True)}, {2, 5})
        self.assertEqual(set(filter_graph(graph, 1, "Two steps", "Outgoing")), {1, 2, 3})
        self.assertEqual(set(filter_graph(graph, 1, "Two steps", "Both")), {1, 2, 3, 4})
        self.assertNotIn(5, filter_graph(graph, isolates=False))
        self.assertEqual(len(filter_graph(graph, None, "Direct")), 0)
        characters = [data for _, data in graph.nodes(data=True)]
        relationships = [data for _, _, data in graph.edges(data=True)]
        typed = build_graph(characters, relationships, "Family")
        self.assertEqual(set(filter_graph(typed, isolates=False)), {1, 2})

    def test_layout_retains_existing_and_pinned_positions(self):
        graph = fixture_graph()
        positions = layout_positions(graph, {}, set())
        graph.add_node(6, id=6, name="new")
        updated = layout_positions(graph, positions, set())
        for node, point in positions.items():
            self.assertEqual(updated[node], point)
        updated[1] = [3., 4.]
        reset = layout_positions(graph, updated, {1}, reset=True)
        self.assertEqual(reset[1], [3., 4.])


class GraphExplorationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        try:
            self.app = StoryAtlas(self.folder / "story.db")
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.cleanup_app)
        self.app.update()
        self.graph = self.app.graph
        self.ids = [self.app.database.save_character({"name": name}) for name in ("A", "B", "C", "Isolate")]
        self.edges = [self.app.database.save_relationship(source, target, kind) for source, target, kind in (
            (self.ids[0], self.ids[1], "Friend"), (self.ids[0], self.ids[1], "Family"),
            (self.ids[1], self.ids[0], "Rival"), (self.ids[1], self.ids[2], "Mentor"))]
        self.app.refresh()

    def cleanup_app(self):
        self.app.database.close()
        self.app.destroy()

    def show(self):
        self.app.tabs.select(self.graph)
        self.app.update()
        self.graph.canvas.draw()

    def event(self, name, node=None, point=None):
        point = point or self.graph.positions[node]
        x, y = self.graph.renderer.axes.transData.transform(point)
        event = MouseEvent(name, self.graph.canvas, x, y, button=1)
        self.graph.canvas.callbacks.process(name, event)
        return event

    def test_hidden_graph_defers_work_and_profile_edits_do_not_redraw(self):
        before = self.graph.renderer.draw_count
        self.assertEqual(before, 1)
        self.app.refresh()
        self.assertEqual(self.graph.renderer.draw_count, before)
        self.show()
        self.graph.select_node(self.ids[0])
        axes = self.graph.renderer.axes
        axes.set_xlim(-.2, .4)
        axes.set_ylim(-.3, .5)
        positions = copy.deepcopy(self.graph.positions)
        count = self.graph.renderer.draw_count
        character = self.app.database.characters()[0]
        character["notes"] = "A note that should not move the graph"
        character["summary"] = "Inspector should update"
        self.app.database.save_character(character, character["id"])
        self.app.refresh()
        self.app.update()
        self.assertEqual(self.graph.renderer.draw_count, count)
        self.assertEqual(self.graph.positions, positions)
        self.assertEqual(axes.get_xlim(), (-.2, .4))
        self.assertEqual(self.graph.selection, ("node", self.ids[0]))
        self.assertIn("Inspector should update", self.graph.inspector.details.get("1.0", "end"))
        self.app.tabs.select(self.app.characters)
        self.app.update()
        character["name"] = "Renamed"
        self.app.database.save_character(character, character["id"])
        self.app.refresh()
        self.assertEqual(self.graph.renderer.draw_count, count)
        self.show()
        self.assertEqual(self.graph.renderer.draw_count, count + 1)
        self.assertEqual(self.graph.positions, positions)
        self.assertEqual(axes.get_xlim(), (-.2, .4))

    def test_node_click_inspects_drag_pins_and_reset_keeps_pin(self):
        self.show()
        node = self.ids[0]
        self.event("button_press_event", node=node)
        self.event("button_release_event", node=node)
        self.assertEqual(self.app.tabs.select(), str(self.graph))
        self.assertEqual(self.graph.selection, ("node", node))
        original = list(self.graph.positions[node])
        self.event("button_press_event", node=node)
        target = [original[0] + .12, original[1] + .1]
        self.event("motion_notify_event", point=target)
        self.event("button_release_event", point=target)
        self.assertIn(node, self.graph.pins)
        moved = list(self.graph.positions[node])
        self.assertNotEqual(moved, original)
        SavedViews(self.app.database).save("Dragged position", self.graph.capture_state())
        self.graph.reset_layout()
        self.assertEqual(self.graph.positions[node], moved)
        self.graph.inspector.open_button.invoke()
        self.assertEqual(self.app.characters.character_id, node)
        self.assertEqual(self.app.characters.profile_tabs.select(), str(self.app.characters.overview))

    def test_parallel_reverse_links_and_export_filtered_view(self):
        self.show()
        self.assertEqual(set(self.graph.renderer.edge_artists), set(self.edges))
        self.assertEqual(len({str(patch.get_path().vertices.tolist()) for patch in self.graph.renderer.edge_artists.values()}), 4)
        for ident in self.edges:
            self.graph.inspector.tree.selection_set(str(ident))
            self.app.update()
            self.assertEqual(self.graph.selection, ("edge", ident))
            self.assertIn(f"#{ident}", self.graph.inspector.heading.cget("text"))
        self.graph._focus_id = self.ids[0]
        self.graph.depth.set("Direct")
        self.graph.direction.set("Outgoing")
        self.graph.refresh(force=True)
        output = self.folder / "filtered.png"
        with patch("story_atlas.graph_actions.filedialog.asksaveasfilename", return_value=str(output)):
            self.graph.export()
        data = json.loads(output.with_suffix(".json").read_text())
        self.assertEqual(len(data["characters"]), 2)
        self.assertEqual({row["id"] for row in data["relationships"]}, set(self.edges[:2]))
        self.assertEqual(self.app.database.activity()[0]["action"], "Graph snapshot exported")

    def test_relationship_changes_preserve_positions_selection_and_zoom(self):
        self.show()
        self.graph.select_edge(self.edges[0])
        axes = self.graph.renderer.axes
        axes.set_xlim(-.5, .6)
        axes.set_ylim(-.4, .7)
        positions = copy.deepcopy(self.graph.positions)
        count = self.graph.renderer.draw_count
        new_edge = self.app.database.save_relationship(self.ids[2], self.ids[0], "Custom pact")
        self.app.refresh()
        self.app.update()
        self.assertEqual(self.graph.renderer.draw_count, count + 1)
        self.assertIn(new_edge, self.graph.renderer.edge_artists)
        self.assertEqual(self.graph.positions, positions)
        self.assertEqual(self.graph.selection, ("edge", self.edges[0]))
        self.assertEqual(axes.get_xlim(), (-.5, .6))
        self.assertEqual(axes.get_ylim(), (-.4, .7))
        self.app.database.save_relationship(self.ids[0], self.ids[1], "Friend", "Updated context", self.edges[0])
        self.app.refresh()
        self.app.update()
        self.assertEqual(self.graph.renderer.draw_count, count + 1)
        self.assertIn("Updated context", self.graph.inspector.details.get("1.0", "end"))

    def test_inspector_relationship_actions_keep_exact_edge_and_graph_context(self):
        self.show()
        ident = self.edges[2]  # Reverse connection: B → A, distinct from A → B.
        self.graph.select_edge(ident)
        axes = self.graph.renderer.axes
        axes.set_xlim(-.5, .6)
        axes.set_ylim(-.4, .7)
        positions = copy.deepcopy(self.graph.positions)
        editor = self.graph.inspector.edit_selected()
        self.assertEqual(editor.relationship_id, ident)
        editor.variables["kind"].set("Enemy")
        self.assertTrue(editor.save())
        editor.close()
        self.app.update()
        self.assertEqual(self.graph.selection, ("edge", ident))
        self.assertEqual(self.graph.positions, positions)
        self.assertEqual(axes.get_xlim(), (-.5, .6))
        self.assertEqual(axes.get_ylim(), (-.4, .7))
        self.assertEqual(next(row for row in self.app.database.relationships() if row["id"] == ident)["kind"], "Enemy")
        canceled = self.graph.inspector.edit_selected()
        canceled.close()
        self.app.update()
        self.assertEqual(self.graph.selection, ("edge", ident))
        history = self.graph.inspector.history_selected()
        self.assertEqual(history.choices[history.choice.get()]["id"], ident)
        history.destroy()

    def test_inspector_labels_historical_context_before_current_edit(self):
        self.show()
        event = self.app.database.events.save("Chapter 2", "A turning point", 2)
        self.graph.as_of_id = event
        self.graph.refresh(force=True)
        self.graph.select_edge(self.edges[0])
        self.assertIn("Chapter 2", self.graph.inspector.heading.cget("text"))
        self.assertIn("Viewing: After: Unassigned / Chapter 2", self.graph.inspector.details.get("1.0", "end"))
        with patch("story_atlas.graph_view.messagebox.askyesno", return_value=False) as choice:
            self.assertIsNone(self.graph.inspector.edit_selected())
        self.assertIn("current relationship", choice.call_args.args[1].lower())
        self.assertEqual(self.graph.selection, ("edge", self.edges[0]))

    def test_graph_profile_links_back_stack_and_cancelled_unsaved_prompt(self):
        self.show()
        origin, connected = self.ids[0], self.ids[1]
        self.graph.select_node(origin)
        axes = self.graph.renderer.axes
        axes.set_xlim(-.5, .6)
        positions = copy.deepcopy(self.graph.positions)
        self.graph.inspector.open_button.invoke()
        self.assertEqual(self.app.characters.character_id, origin)
        self.assertEqual(self.app.back_button.cget("text"), "Back to graph")
        view = self.app.characters
        view.profile_tabs.select(view.overview)
        next(button for ident, button in view.overview.links if ident == connected).invoke()
        self.assertEqual(view.character_id, connected)
        self.assertEqual(self.app.back_button.cget("text"), "Back to A")
        view.fields["summary"].insert("1.0", "Unsaved")
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.app.navigation.back())
        self.assertEqual(view.character_id, connected)
        self.assertEqual(self.app.back_button.cget("text"), "Back to A")
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=False):
            self.assertTrue(self.app.navigation.back())
        self.app.update()
        self.assertEqual(view.character_id, origin)
        self.assertTrue(self.app.navigation.back())
        self.app.update()
        self.assertEqual(self.app.tabs.select(), str(self.graph))
        self.assertEqual(self.graph.selection, ("node", origin))
        self.assertEqual(self.graph.positions, positions)
        self.assertEqual(axes.get_xlim(), (-.5, .6))

    def test_saved_views_survive_reopen_backup_and_missing_characters(self):
        self.show()
        self.graph.select_node(self.ids[0])
        self.graph.toggle_pin()
        self.graph.focus_node(self.ids[0])
        self.graph.renderer.axes.set_xlim(-.4, .8)
        state = self.graph.capture_state()
        store = SavedViews(self.app.database)
        store.save("Cast closeup", state)
        connection = Database(self.app.database.path)
        try:
            self.assertEqual(SavedViews(connection).load("Cast closeup"), state)
        finally:
            connection.close()
        self.graph.selection = None
        self.graph.pins.clear()
        self.graph.apply_state(store.load("Cast closeup"))
        self.assertEqual(self.graph.selection, ("node", self.ids[0]))
        self.assertIn(self.ids[0], self.graph.pins)
        self.assertEqual(self.graph.renderer.axes.get_xlim(), (-.4, .8))
        backup = snapshot(self.app.database.connection, self.app.database.path)
        restored = Database(restore_backup(backup, self.folder / "restored.db"))
        try:
            self.assertEqual(SavedViews(restored).load("Cast closeup"), state)
        finally:
            restored.close()
        self.app.database.delete_character(self.ids[0])
        self.graph.apply_state(store.load("Cast closeup"))
        self.assertIsNone(self.graph.selection)
        self.assertNotIn(self.ids[0], self.graph.positions)
        bad = copy.deepcopy(state)
        bad["positions"][str(self.ids[1])] = [float("nan"), 0]
        with self.assertRaises(ValueError):
            validate_view(bad)

    def test_benchmark_100_characters_300_relationships(self):
        # Use a separate disposable story, including all 300 unique directed edges.
        database = Database(self.folder / "benchmark.db")
        try:
            ids = [database.save_character({"name": f"Character {i:03d}"}) for i in range(100)]
            for i, source in enumerate(ids):
                for step, kind in ((1, "Friend"), (7, "Rival"), (13, "Family")):
                    database.save_relationship(source, ids[(i+step) % 100], kind)
        finally:
            database.close()
        self.app.switch_database(self.folder / "benchmark.db")
        start = time.perf_counter()
        self.show()
        initial = time.perf_counter() - start
        self.assertEqual(len(self.graph.graph), 100)
        self.assertEqual(self.graph.graph.number_of_edges(), 300)
        count = self.graph.renderer.draw_count
        node = self.app.database.characters()[0]
        node["notes"] = "An unrelated profile note"
        self.app.database.save_character(node, node["id"])
        start = time.perf_counter()
        self.app.refresh()
        self.app.update()
        note_edit = time.perf_counter() - start
        self.assertEqual(self.graph.renderer.draw_count, count)
        start = time.perf_counter()
        self.graph.focus_node(ids[0])
        self.graph.canvas.draw()
        focus = time.perf_counter() - start
        print(f"\nGraph benchmark (100 nodes / 300 edges): initial={initial:.3f}s, note refresh={note_edit:.3f}s, direct focus={focus:.3f}s")
