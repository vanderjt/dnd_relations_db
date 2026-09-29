"""Story isolation, exact filters, migrations, and keyboard search integration."""
import sqlite3
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from story_atlas.app import StoryAtlas
from story_atlas.database import Database
from story_atlas.migrations import MIGRATIONS, CURRENT_VERSION
from story_atlas.retrieval import filter_characters, suggestions, search, SavedFilters
from story_atlas.settings import Settings
from story_atlas.global_search import SearchDialog
from story_atlas.filter_dialog import FilterDialog
from story_atlas.backup import snapshot, restore_backup
from story_atlas.imports import read_export, import_payload


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.database = Database(self.path / "story.db")
        self.addCleanup(self.database.close)

    def test_combined_exact_filters_tags_and_duplicate_names(self):
        a = self.database.save_character(dict(name="Mira", faction="Guild", location="Port", status="Missing", tags="Mage, Witness"))
        self.database.save_character(dict(name="Mira", faction="guild", location="Port", status="Missing", tags="mage"))
        self.database.save_character(dict(name="Mira", faction="Guild", location="Port", status="Alive", tags="Mage"))
        filters = dict(faction="Guild", location="Port", status="Missing", tags="Mage, Witness")
        self.assertEqual([row["id"] for row in filter_characters(self.database, "mira", filters)], [a])
        self.assertEqual(suggestions(self.database, "faction"), ["Guild", "guild"])
        self.assertEqual(suggestions(self.database, "tags"), ["Mage", "mage", "Witness"])
        self.assertEqual(len(search(self.database, "Mira")), 3)
        self.assertEqual(filter_characters(self.database, "", dict(tags="Mag")), [])
        store = SavedFilters(self.database)
        state = dict(query="mira", **filters)
        store.save("Port witnesses", state)
        self.assertEqual(store.load("Port witnesses"), state)
        other = Database(self.path / "other.db")
        try:
            self.assertEqual(SavedFilters(other).names(), [])
        finally:
            other.close()
        restored = Database(restore_backup(snapshot(self.database.connection, self.database.path), self.path / "restore.db"))
        try:
            self.assertEqual(SavedFilters(restored).load("Port witnesses"), state)
            self.assertEqual(restored.characters()[0]["tags"], "Mage, Witness")
        finally:
            restored.close()

    def test_relationship_only_search_snippet_and_tag_json_roundtrip(self):
        a = self.database.save_character(dict(name="Mira", tags="Mage, mage"))
        b = self.database.save_character(dict(name="Mira"))
        ident = self.database.save_relationship(a, b, "Ally", "Old context. " * 25 + "Unique snowflake pact")
        matches = search(self.database, "snowflake")
        self.assertEqual([(row["kind"], row["id"]) for row in matches], [("relationship", ident)])
        self.assertIn("snowflake", matches[0]["snippet"])
        self.database.export_json(self.path / "export.json")
        imported = Database(import_payload(read_export(self.path / "export.json"), self.path / "import.db"))
        try:
            self.assertEqual(imported.characters()[0]["tags"], "Mage, mage")
        finally:
            imported.close()

    def test_version_four_migration_preserves_records_and_backup(self):
        path = self.path / "legacy.db"
        connection = sqlite3.connect(path)
        for migration in MIGRATIONS[:4]:
            migration(connection)
        connection.execute("INSERT INTO characters (id,name,notes) VALUES (7,'Mira','Keep this')")
        connection.execute("PRAGMA user_version=4")
        connection.commit()
        connection.close()
        migrated = Database(path)
        try:
            self.assertEqual(migrated.characters()[0]["notes"], "Keep this")
            self.assertEqual(migrated.characters()[0]["tags"], "")
            self.assertEqual(migrated.connection.execute("PRAGMA user_version").fetchone()[0], CURRENT_VERSION)
            self.assertEqual(SavedFilters(migrated).names(), [])
            self.assertEqual(len(list((self.path / "backups" / path.name).glob("pre-migration-v4-*.db"))), 1)
        finally:
            migrated.close()


class OrganizationUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        try:
            self.app = StoryAtlas(self.folder / "first.db")
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.cleanup)
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.app.update()

    def cleanup(self):
        self.app.database.close()
        self.app.destroy()

    def test_new_open_isolation_old_connection_closed_and_session_restored(self):
        original = self.app.database
        ident = original.save_character(dict(name="First", faction="Guild"))
        self.app.refresh()
        self.app.open_character(ident)
        self.app.characters.apply_filters(dict(query="First", faction="Guild"))
        self.assertTrue(self.app.projects.switch(self.folder / "second.db", create=True))
        self.app.update()
        self.assertEqual(self.app.database.characters(), [])
        self.assertIsNone(self.app.characters.character_id)
        self.assertEqual(self.app.characters.search.get(), "")
        with self.assertRaises(sqlite3.ProgrammingError):
            original.connection.execute("SELECT 1")
        self.app.database.save_character(dict(name="Second"))
        self.assertTrue(self.app.switch_database(self.folder / "first.db"))
        self.app.update()
        self.assertEqual([row["name"] for row in self.app.database.characters()], ["First"])
        self.assertEqual(self.app.characters.character_id, ident)
        self.assertEqual(self.app.characters.search.get(), "First")
        self.assertEqual(self.app.characters.roster.filters["faction"], "Guild")
        self.assertIn("first", self.app.story_title.cget("text"))
        recent = Settings(self.app.settings.path).values["recent_stories"]
        self.assertEqual(recent, [str(self.folder / "first.db"), str(self.folder / "second.db")])
        self.assertEqual(self.errors, [])

    def test_canceled_switch_missing_invalid_and_existing_new_paths(self):
        original = self.app.database
        self.app.characters.fields["name"].set("Unfinished")
        target = self.folder / "cancelled.db"
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(self.app.projects.switch(target, create=True))
        self.assertFalse(target.exists())
        self.assertIs(self.app.database, original)
        self.assertEqual(self.app.characters.fields["name"].get(), "Unfinished")
        with self.assertRaisesRegex(ValueError, "missing"):
            self.app.switch_database(self.folder / "missing.db")
        self.assertFalse((self.folder / "missing.db").exists())
        with self.assertRaises(ValueError):
            self.app.projects.switch(original.path, create=True)
        invalid = self.folder / "invalid.db"
        invalid.write_text("not sqlite")
        with self.assertRaises(sqlite3.DatabaseError):
            self.app.switch_database(invalid)
        self.assertIs(self.app.database, original)
        self.assertEqual(self.app.characters.fields["name"].get(), "Unfinished")

    def test_save_failure_and_discard_on_story_switch(self):
        self.app.characters.fields["name"].set("Pending")
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=True), patch.object(
                self.app.database, "save_character", side_effect=sqlite3.OperationalError("disk full")), patch(
                "story_atlas.characters.messagebox.showerror"):
            self.assertFalse(self.app.projects.switch(self.folder / "new.db", create=True))
        self.assertFalse((self.folder / "new.db").exists())
        self.app.characters.draft.flush()
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=False):
            self.assertTrue(self.app.projects.switch(self.folder / "new.db", create=True))
        self.app.update()
        self.assertEqual(self.app.database.drafts.list(), [])
        self.assertEqual(self.app.database.characters(), [])
        self.assertEqual(self.errors, [])

    def test_open_failure_after_discard_keeps_recoverable_edits(self):
        path = self.folder / "other.db"
        Database(path).close()
        original = self.app.database
        self.app.characters.fields["name"].set("Keep this draft")
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=False), patch(
                "story_atlas.projects.Database", side_effect=sqlite3.OperationalError("Cannot open")):
            with self.assertRaises(sqlite3.OperationalError):
                self.app.switch_database(path)
        self.assertIs(self.app.database, original)
        self.assertEqual(original.drafts.list()[0]["values"]["name"], "Keep this draft")

    def test_recent_missing_file_can_be_removed_without_creation(self):
        missing = str(self.folder / "missing.db")
        self.app.settings.save(recent_stories=[missing])
        self.app.projects.recent()
        self.app.update()
        dialog = next(child for child in self.app.winfo_children() if isinstance(child, tk.Toplevel))
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        from tkinter import ttk
        tree = next(child for child in descendants(dialog) if isinstance(child, ttk.Treeview))
        tree.selection_set("0")
        self.assertEqual(tree.item("0", "values")[-1], "Missing")
        buttons = {child.cget("text"): child for child in descendants(dialog) if isinstance(child, ttk.Button)}
        with patch("story_atlas.projects.messagebox.showerror") as error:
            buttons["Open selected"].invoke()
            error.assert_called_once()
        self.assertFalse(Path(missing).exists())
        buttons["Remove from list"].invoke()
        self.assertEqual(Settings(self.app.settings.path).values["recent_stories"], [])
        self.assertEqual(tree.get_children(), ())
        dialog.destroy()

    def test_keyboard_relationship_search_and_reopen_state(self):
        a = self.app.database.save_character(dict(name="Mira"))
        b = self.app.database.save_character(dict(name="Mira"))
        ident = self.app.database.save_relationship(a, b, "Ally", "Only relationship has secretword")
        self.app.refresh()
        self.app.focus_force()
        self.app.event_generate("<Control-k>")
        self.app.update()
        dialog = next(child for child in self.app.winfo_children() if isinstance(child, SearchDialog))
        dialog.query.set("secretword")
        self.app.update()
        dialog.entry.event_generate("<Down>")
        self.app.update()
        dialog.tree.event_generate("<Return>")
        self.app.update()
        self.assertEqual(self.app.tabs.select(), str(self.app.relationships))
        self.assertEqual(self.app.relationships.tree.selection(), (str(ident),))
        self.app.refresh()
        self.assertEqual(self.app.relationships.tree.selection(), (str(ident),))
        self.app.projects.search()
        self.app.update()
        dialog = next(child for child in self.app.winfo_children() if isinstance(child, SearchDialog))
        self.assertEqual(dialog.query.get(), "secretword")
        self.assertEqual(dialog.tree.selection(), (f"relationship:{ident}",))
        dialog.query.set("Mira")
        dialog.refresh()
        dialog.tree.selection_set(f"character:{b}")
        dialog.open_selected()
        self.app.update()
        self.assertEqual(self.app.characters.character_id, b)
        self.assertEqual(self.errors, [])

    def test_relationship_search_actions_edit_exact_record_and_stay_open(self):
        a = self.app.database.save_character(dict(name="Mira"))
        b = self.app.database.save_character(dict(name="Pip"))
        first = self.app.database.save_relationship(a, b, "Ally", "unique note phrase")
        second = self.app.database.save_relationship(b, a, "Rival", "another link")
        self.app.refresh()
        dialog = SearchDialog(self.app, {})
        dialog.query.set("unique note phrase")
        dialog.refresh()
        key = f"relationship:{first}"
        dialog.tree.selection_set(key)
        editor = dialog.edit_selected()
        self.assertEqual(editor.relationship_id, first)
        editor.notes.delete("1.0", "end")
        editor.notes.insert("1.0", "unique note phrase corrected")
        self.assertTrue(editor.save())
        editor.close()
        self.app.update()
        self.assertTrue(dialog.winfo_exists())
        self.assertEqual(dialog.query.get(), "unique note phrase")
        self.assertEqual(dialog.tree.selection(), (key,))
        self.assertIn("corrected", dialog.results[key]["snippet"])
        self.assertEqual(next(row for row in self.app.database.relationships() if row["id"] == second)["kind"], "Rival")
        canceled = dialog.edit_selected()
        canceled.close()
        self.app.update()
        self.assertTrue(dialog.winfo_exists())
        history = dialog.history_selected()
        self.assertEqual(history.choices[history.choice.get()]["id"], first)
        history.destroy()
        self.app.update()
        self.app.database.delete_relationship(first)
        dialog.edit_selected()
        self.assertIn("no longer available", dialog.notice.get())
        dialog.destroy()

    def test_saved_filter_ui_and_tab_state(self):
        ident = self.app.database.save_character(dict(name="Mira", faction="Guild", tags="Mage"))
        self.app.refresh()
        self.app.open_character(ident)
        roster = self.app.characters.roster
        dialog = FilterDialog(roster, self.app.database, self.app.characters.apply_filters)
        dialog.fields["faction"].set("Guild")
        dialog.fields["tags"].set("Mage")
        dialog.name.set("Guild mages")
        dialog.save()
        dialog.clear()
        dialog.load()
        dialog.commit()
        self.app.update()
        for tab in (self.app.graph, self.app.relationships, self.app.characters):
            self.app.tabs.select(tab)
            self.app.update()
        self.assertEqual(roster.filters["faction"], "Guild")
        self.assertEqual(roster.tree.selection(), (str(ident),))
        self.assertEqual(self.errors, [])
