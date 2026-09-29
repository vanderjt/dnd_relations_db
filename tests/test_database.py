"""Integration tests exercise real SQLite files in disposable directories."""
import json
import tempfile
import unittest
from pathlib import Path
from story_atlas.database import Database
from story_atlas.graph import build_graph, draw_graph
from matplotlib.figure import Figure


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "test.db"
        self.db = Database(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_profile_roundtrip_search_and_update(self):
        character = self.db.save_character({"name": "O'Brien", "inventory": "100% silver", "notes": "雪"})
        self.db.close()
        self.db = Database(self.path)
        self.assertEqual(self.db.characters("100%")[0]["id"], character)
        self.assertEqual(self.db.characters()[0]["notes"], "雪")
        self.db.save_character({"name": "Updated"}, character)
        self.assertEqual(self.db.characters()[0]["name"], "Updated")
        with self.assertRaises(ValueError):
            self.db.save_character({"name": "  "})

    def test_relationship_validation_update_and_cascade(self):
        first = self.db.save_character({"name": "First"})
        second = self.db.save_character({"name": "Second"})
        relation = self.db.save_relationship(first, second, "Ally")
        before = len(self.db.activity())
        for source, target, kind in ((first, second, "Ally"), (first, first, "Friend"), (first, 999, "Ally")):
            with self.assertRaises(ValueError):
                self.db.save_relationship(source, target, kind)
        self.assertEqual(len(self.db.activity()), before)
        self.db.save_relationship(second, first, "Rival", "A betrayal", relation)
        self.assertEqual(self.db.relationships()[0]["source_id"], second)
        self.db.delete_character(first)
        self.assertEqual(self.db.relationships(), [])

    def test_graph_multiple_edges_filter_isolates_and_exports(self):
        first, second, isolated = [self.db.save_character({"name": name}) for name in ("A", "B", "C")]
        self.db.save_relationship(first, second, "Ally")
        self.db.save_relationship(first, second, "Family")
        self.db.save_relationship(second, first, "Rival")
        graph = build_graph(self.db.characters(), self.db.relationships())
        self.assertEqual(graph.number_of_edges(), 3)
        self.assertIn(isolated, graph)
        filtered = build_graph(self.db.characters(), self.db.relationships(), "Ally")
        self.assertEqual(filtered.number_of_edges(), 1)
        for layout in ("Spring", "Circle"):
            figure = Figure()
            self.assertEqual(len(draw_graph(figure, graph, layout)), 3)
            figure.savefig(Path(self.temp.name) / f"{layout}.png")
        path = Path(self.temp.name) / "backup.json"
        self.db.export_json(path)
        exported = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(exported["characters"]), 3)
        self.assertEqual(len(exported["relationships"]), 3)
        self.assertEqual(self.db.activity()[0]["action"], "JSON exported")

    def test_empty_graph_and_deleted_relationship_history(self):
        self.assertEqual(draw_graph(Figure(), build_graph([], [])), {})
        first = self.db.save_character({"name": "Same name"})
        second = self.db.save_character({"name": "Same name"})
        relation = self.db.save_relationship(first, second, "Friend")
        self.db.delete_relationship(relation)
        self.assertEqual(self.db.relationships(), [])
        self.assertIn("Friend", self.db.activity()[0]["details"])


if __name__ == "__main__":
    unittest.main()
