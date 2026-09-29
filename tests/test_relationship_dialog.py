"""Real Tk widgets and disposable SQLite data exercise the entry workflow.

These tests require a graphical desktop; they skip if Tk cannot open a display.
"""
import sqlite3
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from story_atlas.database import Database
from story_atlas.relationship_dialog import RelationshipDialog
from story_atlas.quick_character import QuickCharacterDialog
from story_atlas.theme import apply_theme


class RelationshipDialogTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        apply_theme(self.root)
        self.root.geometry("200x100")
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")
        self.ids = [self.db.save_character({"name": name}) for name in ("Mira", "Pip", "Pip")]
        self.changed = Mock()
        self.dialog = RelationshipDialog(self.root, self.db, self.changed)
        self.root.update()
        self.dialog.focus_force()
        self.dialog.boxes["source"].focus_set()

    def tearDown(self):
        if hasattr(self, "db"):
            self.root.update_idletasks()
            self.root.destroy()
            self.db.close()
            self.temp.cleanup()

    def fill(self, kind="Friend", source=0, target=1):
        labels = list(self.dialog.choices)
        self.dialog.variables["source"].set(labels[source])
        self.dialog.variables["target"].set(labels[target])
        self.dialog.variables["kind"].set(kind)
        self.dialog.variables["semantics"].set("Directional")

    def test_ten_additions_clear_every_field_and_refocus(self):
        self.assertEqual(self.dialog.values()["category"], "Other")
        self.assertEqual({key: value for key, value in self.dialog.values().items() if key != "category"}, {key: "" for key in self.dialog.values() if key != "category"})
        for index in range(10):
            self.fill(f"Custom {index}")
            self.dialog.notes.insert("1.0", "A different connection")
            self.assertTrue(self.dialog.save())
            self.root.update()
            self.assertTrue(self.dialog.winfo_exists())
            self.assertEqual(self.dialog.values()["category"], "Other")
            self.assertEqual({key: value for key, value in self.dialog.values().items() if key != "category"}, {key: "" for key in self.dialog.values() if key != "category"})
            self.assertIs(self.dialog.focus_get(), self.dialog.boxes["source"])
            self.assertIn(f"Custom {index}", self.dialog.boxes["kind"].choices)
            self.assertIn("Mira", self.dialog.status.get())
        self.assertEqual(len(self.db.relationships()), 10)
        self.assertEqual(self.changed.call_count, 10)
        self.dialog.destroy()
        self.dialog = RelationshipDialog(self.root, self.db, self.changed)
        self.assertIn("Custom 9", self.dialog.boxes["kind"].choices)
        self.assertIn("Ally", self.dialog.boxes["kind"].choices)

    def test_filtering_preview_and_duplicate_names(self):
        self.dialog.variables["source"].set("PI")
        self.assertEqual(len(self.dialog.boxes["source"].cget("values")), 2)
        self.dialog.variables["source"].set("no matches")
        self.assertFalse(self.dialog.boxes["source"].cget("values"))
        self.fill("Mentor", source=1, target=2)
        self.assertIn("Mentor", self.dialog.preview.get())
        self.assertIn("→", self.dialog.preview.get())
        self.assertTrue(self.dialog.save())
        relationship = self.db.relationships()[0]
        self.assertNotEqual(relationship["source_id"], relationship["target_id"])

    def test_validation_and_duplicate_preserve_input(self):
        self.assertFalse(self.dialog.save())
        self.assertTrue(all(variable.get() for variable in self.dialog.errors.values()))
        self.fill(source=0, target=0)
        self.assertFalse(self.dialog.save())
        self.assertIn("different", self.dialog.errors["target"].get())
        self.fill()
        self.assertTrue(self.dialog.save())
        self.fill()
        self.dialog.notes.insert("1.0", "Keep this note")
        before = self.dialog.values()
        self.assertFalse(self.dialog.save())
        self.assertEqual(self.dialog.values(), before)
        self.assertIn("already", self.dialog.errors["kind"].get())
        self.assertEqual(len(self.db.relationships()), 1)

    def test_database_failure_preserves_input(self):
        self.fill()
        before = self.dialog.values()
        with patch.object(self.db, "save_relationship", side_effect=sqlite3.OperationalError("database is locked")):
            self.assertFalse(self.dialog.save())
        self.assertEqual(self.dialog.values(), before)
        self.assertIn("kept", self.dialog.status.get())
        self.assertEqual(self.db.relationships(), [])

    def test_edit_updates_same_record_and_missing_record_fails(self):
        ident = self.db.save_relationship(self.ids[0], self.ids[1], "Friend", "Old note")
        self.dialog.destroy()
        self.dialog = RelationshipDialog(self.root, self.db, self.changed, self.db.relationships()[0])
        self.dialog.variables["kind"].set("Ally")
        self.assertTrue(self.dialog.save())
        self.dialog.variables["kind"].set("Rival")
        self.assertTrue(self.dialog.save())
        self.assertEqual(len(self.db.relationships()), 1)
        self.assertEqual(self.db.relationships()[0]["id"], ident)
        self.assertEqual(self.db.relationships()[0]["kind"], "Rival")
        self.db.delete_relationship(ident)
        before = self.dialog.values()
        self.assertFalse(self.dialog.save())
        self.assertEqual(self.dialog.values(), before)

    def test_close_cancel_failed_save_discard_and_save(self):
        self.dialog.variables["kind"].set("Unfinished")
        for answer in (None, True):
            with patch("story_atlas.relationship_dialog.messagebox.askyesnocancel", return_value=answer):
                self.dialog.close()
            self.assertTrue(self.dialog.winfo_exists())
            self.assertEqual(self.dialog.variables["kind"].get(), "Unfinished")
        with patch("story_atlas.relationship_dialog.messagebox.askyesnocancel", return_value=False):
            self.dialog.close()
        self.assertFalse(self.dialog.winfo_exists())
        self.dialog = RelationshipDialog(self.root, self.db, self.changed)
        self.fill()
        with patch("story_atlas.relationship_dialog.messagebox.askyesnocancel", return_value=True):
            self.dialog.close()
        self.assertFalse(self.dialog.winfo_exists())
        self.assertEqual(len(self.db.relationships()), 1)

    def test_keyboard_selection_navigation_and_ctrl_enter(self):
        source = self.dialog.boxes["source"]
        self.dialog.variables["source"].set("mir")
        source.focus_force()
        source.event_generate("<Down>")
        self.root.update()
        # Drive the native popdown list, exactly where keyboard events go.
        popup = source.tk.call("ttk::combobox::PopdownWindow", str(source))
        listbox = f"{popup}.f.l"
        source.tk.call("event", "generate", listbox, "<Return>")
        self.root.update()
        self.assertEqual(self.dialog.variables["source"].get(), list(self.dialog.choices)[0])
        source.event_generate("<Tab>")
        self.root.update()
        self.assertIs(self.dialog.focus_get(), self.dialog.boxes["target"])
        self.dialog.boxes["target"].event_generate("<Tab>")
        self.root.update()
        self.assertIs(self.dialog.focus_get(), self.dialog.boxes["kind"])
        self.fill()
        if not self.dialog.optional_open:
            self.dialog.toggle_optional()
            self.root.update()
        self.dialog.notes.focus_set()
        self.dialog.notes.event_generate("<Tab>")
        self.root.update()
        self.assertIs(self.dialog.focus_get(), self.dialog.save_button)
        self.dialog.save_button.event_generate("<Tab>")
        self.root.update()
        self.assertIs(self.dialog.focus_get(), self.dialog.close_button)
        if not self.dialog.optional_open:
            self.dialog.toggle_optional()
            self.root.update()
        self.dialog.notes.focus_set()
        self.dialog.notes.event_generate("<Shift-Tab>")
        self.root.update()
        self.assertIs(self.dialog.focus_get(), self.dialog.boxes["start_event"])
        if not self.dialog.optional_open:
            self.dialog.toggle_optional()
            self.root.update()
        self.dialog.notes.focus_set()
        self.dialog.notes.insert("1.0", "Keyboard save")
        self.dialog.notes.event_generate("<Control-Return>")
        self.root.update()
        self.assertEqual(len(self.db.relationships()), 1)
        self.assertEqual(self.db.relationships()[0]["notes"], "Keyboard save")
        self.assertEqual(self.dialog.values()["category"], "Other")
        self.assertEqual({key: value for key, value in self.dialog.values().items() if key != "category"}, {key: "" for key in self.dialog.values() if key != "category"})
        self.assertIs(self.dialog.focus_get(), source)

    def test_click_text_keeps_dropdown_closed_and_clean_close_needs_no_prompt(self):
        box = self.dialog.boxes["kind"]
        box.event_generate("<Button-1>", x=25, y=box.winfo_height() // 2)
        self.root.update()
        popup = box.tk.call("ttk::combobox::PopdownWindow", str(box))
        self.assertFalse(int(box.tk.call("winfo", "ismapped", popup)))
        box.tk.call("ttk::combobox::Unpost", str(box))
        with patch("story_atlas.relationship_dialog.messagebox.askyesnocancel") as prompt:
            self.dialog.close()
            prompt.assert_not_called()

    def test_create_character_resumes_the_selector_without_losing_entry(self):
        labels = list(self.dialog.choices)
        self.dialog.variables["source"].set(labels[0])
        self.dialog.variables["kind"].set("Friend")
        self.dialog.notes.insert("1.0", "Keep this pending")
        self.dialog.create_character("target")
        creator = next(child for child in self.dialog.winfo_children() if isinstance(child, QuickCharacterDialog))
        creator.name.set("Pip")  # Existing duplicate names remain distinct by ID.
        self.assertTrue(creator.save())
        self.root.update()
        selected = self.dialog.variables["target"].get()
        self.assertEqual(sum(row["name"] == "Pip" for row in self.db.characters()), 3)
        self.assertEqual(selected, f"Pip (#{self.dialog.choices[selected]})")
        self.assertEqual(self.dialog.variables["source"].get(), labels[0])
        self.assertEqual(self.dialog.variables["kind"].get(), "Friend")
        self.assertEqual(self.dialog.notes.get("1.0", "end-1c"), "Keep this pending")
        self.assertIn("not saved", self.dialog.status.get())
        created_id = self.dialog.choices[selected]
        with patch("story_atlas.relationship_dialog.messagebox.askyesnocancel", return_value=False):
            self.dialog.close()
        self.assertTrue(any(row["id"] == created_id for row in self.db.characters()))

    def test_cancelled_or_failed_character_creation_keeps_relationship_input(self):
        labels = list(self.dialog.choices)
        self.dialog.variables["source"].set(labels[0])
        self.dialog.variables["kind"].set("Friend")
        self.dialog.notes.insert("1.0", "Still pending")
        before = self.dialog.values()
        self.dialog.create_character("target")
        creator = self.dialog.character_step
        self.assertNotIsInstance(creator, tk.Toplevel)
        creator.cancel()
        self.root.update()
        self.assertEqual(self.dialog.values(), before)
        self.dialog.create_character("target")
        creator = self.dialog.character_step
        self.assertFalse(creator.save())
        self.assertTrue(self.dialog.character_step.winfo_exists())
        self.assertEqual(self.dialog.values(), before)
        self.assertTrue(creator.status.get())


if __name__ == "__main__":
    unittest.main()
