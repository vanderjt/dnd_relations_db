"""One stored connection, explicit meanings, and lossless conversion contracts."""
import json
from pathlib import Path
import sqlite3
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from matplotlib.figure import Figure
from matplotlib.patches import ArrowStyle

from story_atlas.database import Database
from story_atlas.migrations import MIGRATIONS, CURRENT_VERSION
from story_atlas.relationship_semantics import profile_connections, claims
from story_atlas.imports import read_export, import_payload, validate_payload
from story_atlas.graph import build_graph
from story_atlas.graph_state import filter_graph, layout_positions, drawing_signature
from story_atlas.graph_render import GraphRenderer
from story_atlas.retrieval import search
from story_atlas.backup import snapshot, restore_backup
from story_atlas.app import StoryAtlas
from story_atlas.relationship_dialog import RelationshipDialog
from story_atlas.consolidation_dialog import ConsolidationDialog


class SemanticStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = Database(self.folder / "story.db")
        self.addCleanup(self.db.close)
        self.a, self.b, self.c = [self.db.save_character(dict(name=name)) for name in ("Mira", "Pip", "Pip")]

    def test_mutual_canonical_identity_and_cross_mode_duplicates(self):
        ident = self.db.save_relationship(self.b, self.a, "Friend", semantics="mutual")
        row = self.db.relationships()[0]
        self.assertEqual((row["source_id"], row["target_id"]), (self.a, self.b))
        self.assertEqual(len(claims(row)), 2)
        for source, target, semantics in ((self.a, self.b, "mutual"), (self.b, self.a, "mutual"),
                                           (self.a, self.b, "directional"), (self.b, self.a, "directional")):
            with self.assertRaises(ValueError):
                self.db.save_relationship(source, target, "Friend", semantics=semantics)
        self.db.save_relationship(self.b, self.a, "Friend", "New note", ident)
        self.assertEqual(self.db.relationships()[0]["semantics"], "mutual")
        self.assertEqual(self.db.relationships()[0]["id"], ident)
        for node in (self.a, self.b):
            groups = profile_connections(self.db.relationships(), node)
            self.assertEqual(len(groups["Mutual"]), 1)
            self.assertEqual(groups["Incoming"] + groups["Outgoing"], [])
        with self.assertRaises(sqlite3.IntegrityError), self.db.connection:
            self.db.connection.execute("INSERT INTO relationships(source_id,target_id,kind) VALUES (?,?,?)", (self.b, self.a, "Friend"))

    def test_hostility_inverse_labels_and_reversed_inverse_duplicates(self):
        hostile = self.db.save_relationship(self.a, self.b, "Enemy")
        mentor = self.db.save_relationship(self.a, self.c, "Mentor", inverse_label="Mentee")
        groups = profile_connections(self.db.relationships(), self.c)
        self.assertEqual(groups["Incoming"][0][3], "Mentee")
        self.assertEqual([row["id"] for row in search(self.db, "Mentee")], [mentor])
        with self.assertRaises(ValueError):
            self.db.save_relationship(self.c, self.a, "Mentee")
        # Hostility in the opposite direction is independent and permitted.
        self.db.save_relationship(self.b, self.a, "Enemy")
        with self.assertRaises(ValueError):
            self.db.save_relationship(self.a, self.b, "Friend", semantics="mutual", inverse_label="Enemy")
        self.assertEqual(next(row for row in self.db.relationships() if row["id"] == hostile)["semantics"], "directional")

    def test_graph_mutual_one_edge_both_directions_and_directional_inverse(self):
        mutual_id = self.db.save_relationship(self.b, self.a, "Friend", semantics="mutual")
        self.db.save_relationship(self.a, self.c, "Employer", inverse_label="Employee")
        graph = build_graph(self.db.characters(), self.db.relationships())
        self.assertEqual(graph.number_of_edges(), 2)
        for node in (self.a, self.b):
            for direction in ("Incoming", "Outgoing"):
                focused = filter_graph(graph, node, "Direct", direction)
                self.assertIn(mutual_id, {key for _, _, key in focused.edges(keys=True)})
        self.assertEqual(set(filter_graph(graph, self.c, "Direct", "Outgoing")), {self.c})
        self.assertEqual(build_graph(self.db.characters(), self.db.relationships(), "Employee").number_of_edges(), 1)
        renderer = GraphRenderer(Figure())
        renderer.draw(graph, layout_positions(graph, {}, set()), set())
        self.assertEqual(len(renderer.edge_artists), 2)
        self.assertIsInstance(renderer.edge_artists[mutual_id].get_arrowstyle(), ArrowStyle.CurveFilledAB)
        self.assertIn("↔", renderer.edge_labels[mutual_id].get_text())
        before = drawing_signature(graph)
        self.db.save_relationship(self.a, self.b, "Friend", relationship_id=mutual_id, semantics="directional")
        self.assertNotEqual(before, drawing_signature(build_graph(self.db.characters(), self.db.relationships())))

    def test_exports_imports_and_legacy_payload(self):
        self.db.save_relationship(self.b, self.a, "Friend", semantics="mutual")
        self.db.save_relationship(self.a, self.c, "Mentor", inverse_label="Mentee")
        path = self.folder / "export.json"
        self.db.export_json(path)
        payload = json.loads(path.read_text())
        self.assertEqual(payload["format_version"], 9)
        imported = Database(import_payload(read_export(path), self.folder / "import.db"))
        try:
            self.assertEqual(imported.relationships(), self.db.relationships())
        finally:
            imported.close()
        bad = json.loads(path.read_text())
        reverse = dict(bad["relationships"][0], id=99, source_id=self.b, target_id=self.a)
        bad["relationships"].append(reverse)
        with self.assertRaises(ValueError):
            validate_payload(bad)
        legacy = dict(format_version=1, characters=payload["characters"], relationships=[
            dict(id=1, source_id=self.a, target_id=self.b, kind="Friend"),
            dict(id=2, source_id=self.b, target_id=self.a, kind="Friend")])
        rows = validate_payload(legacy)["relationships"]
        self.assertEqual([row["semantics"] for row in rows], ["directional", "directional"])

    def test_legacy_migration_never_infers_mutual_and_backs_up(self):
        path = self.folder / "legacy.db"
        con = sqlite3.connect(path)
        for migration in MIGRATIONS[:5]:
            migration(con)
        con.execute("INSERT INTO characters(id,name) VALUES (1,'A'),(2,'B')")
        con.execute("INSERT INTO relationships(source_id,target_id,kind,notes) VALUES (1,2,'Friend','First'),(2,1,'Friend','Second')")
        con.execute("PRAGMA user_version=5")
        con.commit()
        con.close()
        db = Database(path)
        try:
            self.assertEqual([row["semantics"] for row in db.relationships()], ["directional", "directional"])
            self.assertEqual([row["notes"] for row in db.relationships()], ["First", "Second"])
            self.assertEqual(db.connection.execute("PRAGMA user_version").fetchone()[0], CURRENT_VERSION)
            self.assertEqual(len(list((self.folder / "backups" / path.name).glob("pre-migration-v5-*.db"))), 1)
        finally:
            db.close()

    def test_consolidation_preserves_conflicting_notes_labels_and_originals(self):
        first = self.db.save_relationship(self.a, self.b, "Ally", "First notes", inverse_label="Partner")
        second = self.db.save_relationship(self.b, self.a, "Friend", "Different notes")
        preview = self.db.relationship_store.preview_consolidation(first, second, "Friend")
        self.assertEqual(len(self.db.relationships()), 2)  # Preview writes nothing.
        for value in ("First notes", "Different notes", "Ally", "Partner", "Friend"):
            self.assertIn(value, preview["result"]["notes"])
        with patch.object(self.db, "_log", side_effect=sqlite3.OperationalError("disk full")):
            with self.assertRaises(sqlite3.OperationalError):
                self.db.relationship_store.consolidate(preview)
        self.assertEqual(len(self.db.relationships()), 2)
        self.assertEqual(self.db.trash.items(), [])
        ident = self.db.relationship_store.consolidate(preview)
        self.assertEqual(len(self.db.relationships()), 1)
        self.assertEqual(self.db.relationships()[0]["id"], ident)
        self.assertEqual(len(self.db.trash.items()), 2)
        # Original records can be recovered exactly after removing the replacement.
        self.db.delete_relationship(ident)
        self.db.trash.restore("relationship", first)
        self.db.trash.restore("relationship", second)
        self.assertEqual(self.db.relationships(), preview["originals"])

    def test_stale_preview_and_recovery_conflicts_are_atomic(self):
        first = self.db.save_relationship(self.a, self.b, "Friend")
        second = self.db.save_relationship(self.b, self.a, "Friend")
        preview = self.db.relationship_store.preview_consolidation(first, second, "Friend")
        self.db.save_relationship(self.b, self.a, "Friend", "Changed", second)
        with self.assertRaisesRegex(ValueError, "changed"):
            self.db.relationship_store.consolidate(preview)
        self.assertEqual(len(self.db.relationships()), 2)
        self.db.delete_relationship(first)
        self.db.delete_relationship(second)
        mutual_id = self.db.save_relationship(self.a, self.b, "Friend", semantics="mutual")
        with self.assertRaises(ValueError):
            self.db.trash.restore("relationship", second)
        self.db.delete_character(self.b)
        self.assertEqual(self.db.relationships(), [])
        self.db.trash.restore("character", self.b)
        self.assertEqual([row["id"] for row in self.db.relationships()], [mutual_id])
        restored = Database(restore_backup(snapshot(self.db.connection, self.db.path), self.folder / "restored.db"))
        try:
            self.assertEqual(restored.relationships(), self.db.relationships())
        finally:
            restored.close()


class SemanticUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        try:
            self.app = StoryAtlas(Path(self.temp.name) / "story.db")
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.cleanup)
        self.a, self.b = [self.app.database.save_character(dict(name=name)) for name in ("Mira", "Pip")]
        self.app.refresh()
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_explicit_mode_batch_clear_inverse_preview_and_edit(self):
        dialog = RelationshipDialog(self.app, self.app.database, self.app.refresh)
        self.app.update()
        dialog.focus_force()
        labels = list(dialog.choices)
        for kind, mode, inverse in (("Friend", "Mutual", ""), ("Mentor", "Directional", "Mentee")):
            for field, value in dict(source=labels[0], target=labels[1], kind=kind).items():
                dialog.variables[field].set(value)
            self.assertFalse(dialog.save())
            dialog.variables["semantics"].set(mode)
            dialog.variables["inverse_label"].set(inverse)
            self.assertIn("both profiles" if mode == "Mutual" else "Mentee", dialog.preview.get())
            self.assertTrue(dialog.save())
            self.app.update()
            self.assertEqual(dialog.values()["category"], "Other")
            self.assertEqual({key: value for key, value in dialog.values().items() if key != "category"}, {key: "" for key in dialog.values() if key != "category"})
            self.assertTrue(dialog.winfo_exists())
            self.assertIs(dialog.focus_get(), dialog.boxes["source"])
        dialog.destroy()
        row = self.app.database.relationships()[0]
        dialog = RelationshipDialog(self.app, self.app.database, self.app.refresh, row)
        dialog.variables["kind"].set("Family")
        self.assertTrue(dialog.save())
        self.assertEqual(len(self.app.database.relationships()), 2)
        self.assertEqual(self.app.database.relationships()[0]["id"], row["id"])
        dialog.destroy()
        for ident in (self.a, self.b):
            self.app.open_character(ident)
            self.assertEqual(len(self.app.characters.overview.links), 2)

    def test_consolidation_requires_preview_and_cancel_changes_nothing(self):
        db = self.app.database
        first = db.save_relationship(self.a, self.b, "Friend", "One")
        db.save_relationship(self.b, self.a, "Friend", "Two")
        row = db.relationships()[0]
        dialog = ConsolidationDialog(self.app, db, self.app.refresh, row)
        dialog.reverse.set(next(iter(dialog.choices)))
        dialog.kind.set("Friend")
        dialog.commit()
        self.assertEqual(len(db.relationships()), 2)
        dialog.review()
        self.assertIn("One", dialog.details.get("1.0", "end"))
        self.assertIn("Two", dialog.details.get("1.0", "end"))
        dialog.destroy()
        self.assertEqual(len(db.relationships()), 2)
        dialog = ConsolidationDialog(self.app, db, self.app.refresh, row)
        dialog.reverse.set(next(iter(dialog.choices)))
        dialog.kind.set("Friend")
        dialog.review()
        dialog.kind.set("Ally")
        self.assertIsNone(dialog.preview)
        dialog.review()
        dialog.commit()
        self.assertEqual(len(db.relationships()), 1)
        self.assertEqual(db.relationships()[0]["semantics"], "mutual")
        self.assertNotEqual(db.relationships()[0]["id"], first)
