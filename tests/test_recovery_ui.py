"""Exercise real editor draft timers and recovery UI with temporary story files."""
import json
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from story_atlas.app import StoryAtlas
from story_atlas.recovery import RecoveryDialog


class RecoveryUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        try:
            self.app = StoryAtlas(self.folder / "active.db")
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.cleanup_app)
        self.app.update()

    def cleanup_app(self):
        self.app.database.close()
        self.app.destroy()

    def wait_for_draft(self):
        self.app.after(1200, self.app.quit)
        self.app.mainloop()

    def test_timed_draft_survives_interruption_and_requires_explicit_commit(self):
        view = self.app.characters
        view.fields["name"].set("Unsaved Mira")
        view.fields["notes"].insert("1.0", "Recovery text")
        self.wait_for_draft()
        self.assertEqual(self.app.database.characters(), [])
        self.assertEqual(self.app.database.activity(), [])
        self.assertEqual(len(self.app.database.drafts.list()), 1)
        self.app.database.close()
        self.app.destroy()  # Simulate interruption without the normal close/save prompt.
        self.app = StoryAtlas(self.folder / "active.db")
        self.app.update()
        self.assertIn("recoverable", self.app.status.get())
        center = RecoveryDialog(self.app)
        center.drafts.selection_set("0")
        center.recover_draft()
        self.assertFalse(center.winfo_exists())
        self.assertEqual(self.app.characters.values()["notes"], "Recovery text")
        self.assertEqual(self.app.database.characters(), [])
        self.assertNotEqual(self.app.characters.values(), self.app.characters.original)
        self.assertTrue(self.app.characters.save())
        self.assertEqual(self.app.database.characters()[0]["name"], "Unsaved Mira")
        self.assertEqual(self.app.database.drafts.list(), [])
        self.assertEqual(len(self.app.database.activity()), 1)

    def test_discard_cancels_pending_draft_and_keeps_committed_profile(self):
        view = self.app.characters
        view.fields["name"].set("Committed")
        view.save()
        view.fields["name"].set("Discard this")
        with patch("story_atlas.characters.messagebox.askyesnocancel", return_value=False):
            view.new()
        self.wait_for_draft()
        self.assertEqual(self.app.database.drafts.list(), [])
        self.assertEqual(self.app.database.characters()[0]["name"], "Committed")

    def test_import_preview_cancel_failure_and_open_new_story(self):
        self.app.database.save_character({"name": "Active original"})
        self.app.refresh()
        original_path = self.app.database.path
        source = self.folder / "source.json"
        source.write_text(json.dumps(dict(format_version=1, characters=[dict(id=42, name="Imported")], relationships=[])))
        center = RecoveryDialog(self.app)
        with patch("story_atlas.recovery.filedialog.askopenfilename", return_value=str(source)), \
                patch("story_atlas.recovery.messagebox.askyesno", return_value=False) as preview:
            center.import_json()
        self.assertIn("1 characters", preview.call_args.args[1])
        self.assertEqual(self.app.database.path, original_path)
        with patch("story_atlas.recovery.filedialog.askopenfilename", return_value=str(source)), \
                patch("story_atlas.recovery.messagebox.askyesno", return_value=True), \
                patch.object(center, "new_path", return_value=str(original_path)):
            with self.assertRaises(ValueError):
                center.import_json()
        self.assertEqual(self.app.database.characters()[0]["name"], "Active original")
        destination = self.folder / "imported.db"
        with patch("story_atlas.recovery.filedialog.askopenfilename", return_value=str(source)), \
                patch("story_atlas.recovery.messagebox.askyesno", return_value=True), \
                patch.object(center, "new_path", return_value=str(destination)):
            center.import_json()
        self.app.update()
        self.assertEqual(self.app.database.path, destination)
        self.assertEqual(self.app.database.characters()[0]["id"], 42)
        self.assertEqual(self.app.characters.character_id, None)
        center.destroy()

    def test_trash_and_backup_buttons_restore_a_separate_story(self):
        ident = self.app.database.save_character({"name": "Mira"})
        self.app.database.delete_character(ident)
        center = RecoveryDialog(self.app)
        center.trash.selection_set("0")
        center.restore_trash()
        self.assertEqual(self.app.database.characters()[0]["id"], ident)
        center.backup()
        manual = next(path for path in center.backup_paths if path.name.startswith("manual-"))
        destination = self.folder / "restored.db"
        with patch.object(center, "new_path", return_value=str(destination)), \
                patch("story_atlas.recovery.messagebox.askyesno", return_value=True):
            center.restore(manual)
        self.assertEqual(self.app.database.path, destination)
        self.assertEqual(self.app.database.characters()[0]["id"], ident)
        center.retention.set("3")
        center.save_retention()
        self.assertEqual(self.app.settings.values["backup_retention"], 3)
        center.destroy()
