"""Profile evolution, portrait storage, duplicate policy, and actual Tk navigation."""
import sqlite3
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from story_atlas.app import StoryAtlas
from story_atlas.backup import snapshot, restore_backup, backup_directory
from story_atlas.database import Database
from story_atlas.migrations import initial_schema, recovery_schema
from story_atlas.models import LEGACY_PROFILE_FIELDS, PROFILE_FIELDS
from story_atlas.imports import import_payload, read_export


class ProfileStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def database(self, filename="story.db"):
        database = Database(self.folder / filename)
        self.addCleanup(database.close)
        return database

    def test_version_two_migration_preserves_every_field_trash_and_draft(self):
        path = self.folder / "legacy.db"
        connection = sqlite3.connect(path)
        initial_schema(connection)
        recovery_schema(connection)
        values = {field: f"  {field} — 雪\nlegacy  " for field in LEGACY_PROFILE_FIELDS}
        fields = ",".join(values)
        marks = ",".join("?" for _ in values)
        connection.execute(f"INSERT INTO characters (id,{fields}) VALUES (5,{marks})", tuple(values.values()))
        connection.execute("INSERT INTO drafts(key,payload) VALUES ('character:5','{\"name\":\"Draft\"}')")
        connection.execute("PRAGMA user_version=2")
        connection.commit()
        connection.close()
        database = Database(path)
        self.addCleanup(database.close)
        profile = database.characters()[0]
        for field, value in values.items():
            self.assertEqual(profile[field], value)
        self.assertEqual(profile["summary"], "")
        self.assertEqual(profile["portrait"], "")
        self.assertEqual(database.drafts.list()[0]["values"]["name"], "Draft")
        self.assertTrue(list(backup_directory(path).glob("pre-migration-v2-*.db")))

    def test_duplicate_copies_profile_and_portrait_but_no_connections_or_drafts(self):
        database = self.database()
        source = self.folder / "portrait.jpg"
        Image.new("RGB", (100, 200), "navy").save(source)
        portrait = database.assets.import_image(source)
        values = {field: f"Text for {field}" for field in PROFILE_FIELDS}
        values["portrait"] = portrait
        values['narrative_role'] = 'protagonist'
        values['classification'] = 'NPC Ally'
        values['character_type'] = 'Allied NPC'
        values['narrative_role'] = 'neutral'
        original = database.save_character(values)
        other = database.save_character({"name": values["name"]})
        database.save_relationship(original, other, "Friend")
        database.drafts.save(original, {"name": "Uncommitted version"})
        duplicate = database.duplicate_character(original)
        copied = next(row for row in database.characters() if row["id"] == duplicate)
        for field, value in values.items():
            self.assertEqual(copied[field], value + " (copy)" if field == "name" else value)
        self.assertEqual(len(database.relationships()), 1)
        self.assertNotIn(duplicate, (database.relationships()[0]["source_id"], database.relationships()[0]["target_id"]))
        self.assertEqual(len(database.drafts.list()), 1)

    def test_backup_is_self_contained_and_restore_rebuilds_managed_portraits(self):
        database = self.database()
        source = self.folder / "original.png"
        Image.new("RGB", (1400, 700), "teal").save(source)
        original_bytes = source.read_bytes()
        portrait = database.assets.import_image(source)
        self.assertEqual(source.read_bytes(), original_bytes)
        managed = database.assets.resolve(portrait)
        self.assertEqual(managed.parent, database.assets.folder)
        with Image.open(managed) as image:
            self.assertEqual(image.size, (1024, 512))
        ident = database.save_character({"name": "Mira", "portrait": portrait, "summary": "Keeper of the light"})
        database.delete_character(ident)
        database.drafts.save(None, {"name": "Draft", "portrait": portrait})
        backup = snapshot(database.connection, database.path)
        source.unlink()
        managed.unlink()
        destination = restore_backup(backup, self.folder / "restored.db")
        restored = Database(destination)
        self.addCleanup(restored.close)
        restored.trash.restore("character", ident)
        self.assertEqual(restored.characters()[0]["summary"], "Keeper of the light")
        recovered_image = restored.assets.resolve(portrait)
        self.assertTrue(recovered_image.exists())
        self.assertNotEqual(recovered_image.parent, database.assets.folder)
        self.assertEqual(restored.drafts.list()[0]["values"]["portrait"], portrait)
        self.assertIsNotNone(restored.assets.thumbnail(portrait))

    def test_missing_invalid_and_json_only_portraits_are_safe(self):
        database = self.database()
        missing = "a" * 64 + ".png"
        database.save_character({"name": "Missing image", "portrait": missing})
        self.assertIsNone(database.assets.thumbnail(missing))
        self.assertIsNone(database.assets.resolve("../../outside.png"))
        invalid = self.folder / "broken.png"
        invalid.write_text("not an image")
        with self.assertRaises(ValueError):
            database.assets.import_image(invalid)
        path = self.folder / "export.json"
        database.export_json(path)
        imported_path = import_payload(read_export(path), self.folder / "imported.db")
        imported = Database(imported_path)
        self.addCleanup(imported.close)
        self.assertEqual(imported.characters()[0]["portrait"], missing)
        self.assertIsNone(imported.assets.thumbnail(missing))


class ProfileUITests(unittest.TestCase):
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
        self.view = self.app.characters

    def cleanup_app(self):
        self.app.database.close()
        self.app.destroy()

    def test_name_only_creation_templates_and_editing_all_fields(self):
        self.view.fields["name"].set("Mira")
        self.assertTrue(self.view.save())
        self.assertEqual(self.app.database.characters()[0]["backstory"], "")
        self.assertEqual(self.view.profile_tabs.select(), str(self.view.editor))
        self.view.profile_tabs.select(self.view.editor)
        self.view.fields["backstory"].insert("1.0", "Existing backstory")
        for template in ("Minor NPC", "Protagonist", "Antagonist"):
            self.view.editor.template.set(template)
            self.view.editor.apply_template()
            self.assertEqual(self.view.fields["backstory"].get("1.0", "end-1c"), "Existing backstory")
        self.view.fields["summary"].delete("1.0", "end")
        self.view.fields["summary"].insert("1.0", "Lighthouse keeper")
        self.view.fields["faction"].set("Harbor Watch")
        self.assertTrue(self.view.save())
        self.assertEqual(self.view.overview.summary.cget("text"), "Lighthouse keeper")
        self.assertIn("Harbor Watch", self.view.overview.details.cget("text"))

    def test_directional_navigation_duplicate_names_and_add_relationship(self):
        database = self.app.database
        first, second = [database.save_character({"name": "Same name"}) for _ in range(2)]
        database.save_relationship(first, second, "Mentor")
        database.save_relationship(second, first, "Rival")
        self.app.refresh()
        self.view.open_character(first)
        self.assertEqual(len(self.view.overview.links), 2)
        self.view.overview.links[0][1].invoke()
        self.assertEqual(self.view.character_id, second)
        self.assertIn(f"#{second}", self.view.overview.name.cget("text"))
        dialog = self.view.add_relationship()
        labels = list(dialog.choices)
        self.assertEqual(dialog.values()["category"], "Other")
        self.assertEqual({key: value for key, value in dialog.values().items() if key != "category"}, {key: "" for key in dialog.values() if key != "category"})
        dialog.variables["source"].set(labels[0])
        dialog.variables["target"].set(labels[1])
        dialog.variables["kind"].set("Family")
        dialog.variables["semantics"].set("Directional")
        self.assertTrue(dialog.save())
        self.app.update()
        self.assertEqual(dialog.values()["category"], "Other")
        self.assertEqual({key: value for key, value in dialog.values().items() if key != "category"}, {key: "" for key in dialog.values() if key != "category"})
        self.assertTrue(dialog.winfo_exists())
        self.assertEqual(len(self.view.overview.links), 3)
        dialog.close()

    def test_relationship_entry_is_available_before_two_characters_exist(self):
        dialog = self.app.relationships.edit()
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.choices, {})
        self.assertIn("source", dialog.create_buttons)
        dialog.close()

    def test_profile_relationship_context_requires_explicit_source_action(self):
        mira = self.app.database.save_character({"name": "Mira"})
        pip = self.app.database.save_character({"name": "Pip"})
        self.app.refresh()
        self.view.open_character(mira)
        dialog = self.view.add_relationship_from_profile()
        self.assertEqual(dialog.values()["category"], "Other")
        self.assertEqual({key: value for key, value in dialog.values().items() if key != "category"}, {key: "" for key in dialog.values() if key != "category"})
        self.assertEqual(dialog.use_source_button.cget("text"), "Use Mira as Source")
        dialog.use_source_button.invoke()
        source = dialog.variables["source"].get()
        self.assertEqual(dialog.choices[source], mira)
        target = next(label for label, ident in dialog.choices.items() if ident == pip)
        dialog.variables["target"].set(target)
        dialog.variables["kind"].set("Friend")
        dialog.variables["semantics"].set("Directional")
        self.assertTrue(dialog.save())
        self.assertEqual(dialog.values()["category"], "Other")
        self.assertEqual({key: value for key, value in dialog.values().items() if key != "category"}, {key: "" for key in dialog.values() if key != "category"})
        dialog.close()

    def test_delete_then_undo_restores_the_character_in_place(self):
        mira = self.app.database.save_character({"name": "Mira"})
        self.app.refresh()
        self.view.open_character(mira)
        with patch("story_atlas.characters.messagebox.askyesno", return_value=True):
            self.view.delete()
        self.assertFalse(self.app.database.characters())
        self.assertEqual(self.view.undo_target, mira)
        self.assertNotIn("disabled", self.view.undo_button.state())
        self.view.undo_delete()
        self.assertEqual([row["id"] for row in self.app.database.characters()], [mira])
        self.assertEqual(self.view.character_id, mira)
        self.assertIsNone(self.view.undo_target)
        self.assertIn("disabled", self.view.undo_button.state())

    def test_overview_relationship_actions_target_exact_connection_and_return(self):
        database = self.app.database
        mira = database.save_character({"name": "Mira"})
        thorne = database.save_character({"name": "Thorne"})
        ally = database.save_relationship(mira, thorne, "Ally", "First connection", semantics="mutual")
        rival = database.save_relationship(mira, thorne, "Rival", "Second connection")
        self.app.refresh()
        self.view.open_character(mira)
        overview = self.view.overview
        self.assertEqual(set(overview.relationship_actions), {ally, rival})
        control = overview.relationship_actions[rival]
        editor = overview.edit_relationship(next(row for row in database.relationships() if row["id"] == rival), control)
        self.assertEqual(editor.relationship_id, rival)
        editor.variables["kind"].set("Enemy")
        self.assertTrue(editor.save())
        editor.close()
        self.app.update()
        self.assertEqual(self.view.character_id, mira)
        self.assertEqual(next(row for row in database.relationships() if row["id"] == rival)["kind"], "Enemy")
        self.assertEqual(next(row for row in database.relationships() if row["id"] == ally)["kind"], "Ally")
        self.assertIn(ally, overview.relationship_actions)
        canceled = overview.edit_relationship(next(row for row in database.relationships() if row["id"] == ally), overview.relationship_actions[ally])
        canceled.close()
        self.app.update()
        self.assertEqual(next(row for row in database.relationships() if row["id"] == ally)["kind"], "Ally")
        self.assertEqual(self.view.character_id, mira)
        history = overview.view_history(next(row for row in database.relationships() if row["id"] == ally), overview.relationship_actions[ally])
        self.assertEqual(history.choices[history.choice.get()]["id"], ally)
        history.destroy()
        self.app.update()
        self.assertEqual(self.view.character_id, mira)

    def test_duplicate_confirmation_and_missing_portrait_placeholder(self):
        ident = self.app.database.save_character({"name": "Mira", "portrait": "b" * 64 + ".png"})
        self.app.refresh()
        self.view.open_character(ident)
        self.assertIn("unavailable", self.view.overview.portrait.cget("text"))
        with patch("story_atlas.characters.messagebox.askyesno", return_value=True) as confirmation:
            self.view.duplicate()
        self.assertIn("NOT be copied", confirmation.call_args.args[1])
        self.assertNotEqual(self.view.character_id, ident)
        self.assertEqual(self.view.fields["name"].get(), "Mira (copy)")
        self.assertEqual(self.view.profile_tabs.select(), str(self.view.editor))

    def test_portrait_import_remove_and_draft_recovery(self):
        image = self.folder / "portrait.png"
        Image.new("RGB", (80, 100), "purple").save(image)
        self.view.fields["name"].set("Portrait character")
        with patch("story_atlas.profile_editor.filedialog.askopenfilename", return_value=str(image)):
            self.view.editor.import_portrait()
        portrait = self.view.fields["portrait"].get()
        self.assertTrue(portrait.endswith(".png"))
        self.assertTrue(self.view.save())
        self.assertIsNotNone(self.view.overview.photo)
        self.view.fields["summary"].insert("1.0", "Uncommitted summary")
        self.view.draft.cancel()
        self.view.draft.flush()
        draft = self.app.database.drafts.list()[0]
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=False):
            self.assertTrue(self.view.recover_draft(draft))
        self.assertEqual(self.view.fields["portrait"].get(), portrait)
        self.view.fields["portrait"].set("")
        self.assertTrue(self.view.save())
        self.assertEqual(self.app.database.characters()[0]["portrait"], "")
        self.assertIsNotNone(self.app.database.assets.resolve(portrait))
