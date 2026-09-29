"""First-run choices, sample isolation and upgrade-safe writable locations."""
import os
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from story_atlas.paths import data_root, prepare_data, validate_writable_location, resource
from story_atlas.settings import Settings
from story_atlas.sample_story import create_sample, new_sample
from story_atlas.onboarding import Welcome, resume_path, create_empty, check_existing
from story_atlas.database import Database
from story_atlas.app import StoryAtlas
from story_atlas.guidance import show_help
from story_atlas.version import APPLICATION_VERSION, about_text, build_identity, source_fingerprint
from story_atlas.migrations import CURRENT_VERSION


class DistributionStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_first_launch_resume_and_missing_last_story(self):
        settings = Settings(self.folder / "settings.json")
        self.assertIsNone(resume_path(settings))
        path = create_empty(self.folder / "existing.db")
        db = Database(path)
        ident = db.save_character(dict(name="Keep me"))
        db.close()
        settings.save(last_story=str(path))
        self.assertEqual(resume_path(Settings(settings.path)), path)
        self.assertEqual(check_existing(path), path)
        again = Database(path)
        self.assertEqual(again.characters()[0]["id"], ident)
        again.close()
        settings.save(last_story=str(self.folder / "missing.db"))
        self.assertIsNone(resume_path(Settings(settings.path)))
        with self.assertRaises(ValueError):
            check_existing(self.folder / "missing.db")
        self.assertFalse((self.folder / "missing.db").exists())

    def test_source_build_identity_and_active_schema(self):
        db = Database(self.folder / "identity.db")
        try:
            mode, fingerprint = build_identity()
            self.assertEqual(mode, "Source")
            self.assertEqual(fingerprint, source_fingerprint())
            self.assertEqual(len(fingerprint), 64)
            details = about_text(db)
            self.assertIn(f"Story Atlas {APPLICATION_VERSION}", details)
            self.assertIn("Runtime: Source", details)
            self.assertIn(f"Supported database schema: {CURRENT_VERSION}", details)
            self.assertIn(f"Active database schema: {CURRENT_VERSION}", details)
        finally:
            db.close()

    def test_expanded_sample_never_overwrites_user_story(self):
        user = create_empty(self.folder / "user.db")
        before = user.read_bytes()
        with self.assertRaises(ValueError):
            create_sample(user)
        self.assertEqual(user.read_bytes(), before)
        first, second = new_sample(self.folder), new_sample(self.folder)
        self.assertNotEqual(first, second)
        db = Database(first)
        try:
            self.assertEqual(len(db.characters()), 18)
            self.assertEqual(len(db.relationship_records()), 50)
            self.assertEqual(len(db.relationships()), 49)  # One alliance ended.
            self.assertTrue(any(row["semantics"] == "mutual" for row in db.relationships()))
            self.assertTrue(any(row["inverse_label"] for row in db.relationships()))
            events = db.events.list()
            self.assertEqual(len(events), 10)
            self.assertTrue(any(row["kind"] == "Enemy" for row in db.relationships(events[-1]["id"])))
        finally:
            db.close()
        self.assertEqual(user.read_bytes(), before)

    def test_upgrade_paths_independent_of_program_folder_and_bad_overrides(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.folder)}, clear=True):
            self.assertEqual(data_root(), self.folder / "StoryAtlas")
        with patch.dict(os.environ, {}, clear=True):
            root = prepare_data(self.folder / "user data")
            settings = Settings(root / "settings.json")
            settings.save(theme="light")
            for version in ("version-one", "version-two"):
                executable = self.folder / version / "StoryAtlas.exe"
                with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(executable)):
                    self.assertEqual(validate_writable_location(root / "stories" / "keep.db"), root / "stories" / "keep.db")
                    with self.assertRaises(ValueError):
                        validate_writable_location(executable.parent / "user.db")
                    with self.assertRaises(ValueError):
                        prepare_data(executable.parent / "data")
            self.assertEqual(Settings(root / "settings.json").values["theme"], "light")
        self.assertTrue(resource("story-atlas.ico").is_file())


class WelcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.settings = Settings(self.folder / "settings.json")
        try:
            self.window = Welcome(self.folder, self.settings)
        except tk.TclError as error:
            self.skipTest(str(error))
        self.addCleanup(self.cleanup)
        self.window.update()

    def cleanup(self):
        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def test_cancelled_picker_creates_no_database(self):
        with patch("story_atlas.onboarding.filedialog.asksaveasfilename", return_value=""), patch(
                "story_atlas.onboarding.filedialog.askopenfilename", return_value=""):
            self.window.start_empty()
            self.window.open_story()
        self.assertIsNone(self.window.result)
        self.assertEqual(list(self.folder.rglob("*.db")), [])

    def test_start_empty_and_try_sample_choices(self):
        with patch("story_atlas.onboarding.filedialog.asksaveasfilename", return_value=str(self.folder / "empty.db")):
            setup = self.window.start_empty()
            setup.fields[0].set('My story')
            setup.save()
        db = Database(self.window.result)
        self.assertEqual(db.characters(), [])
        db.close()
        self.window = Welcome(self.folder, self.settings)
        self.window.try_sample()
        self.assertNotEqual(self.window.result, self.folder / "empty.db")
        db = Database(self.window.result)
        self.assertEqual(len(db.characters()), 18)
        db.close()

    def test_open_existing_preserves_data(self):
        path = create_empty(self.folder / "existing.db")
        before = path.read_bytes()
        with patch("story_atlas.onboarding.filedialog.askopenfilename", return_value=str(path)):
            self.window.open_story()
        self.assertEqual(self.window.result, path)
        self.assertEqual(path.read_bytes(), before)


class GuidanceTests(unittest.TestCase):
    def test_dismiss_restore_and_reopen_preferences(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "story.db"
            try:
                app = StoryAtlas(path)
            except tk.TclError as error:
                self.skipTest(str(error))
            try:
                app.update()
                app.guidance.show("graph")
                app.guidance.dismiss()
                self.assertIn("graph", Settings(app.settings.path).values["dismissed_guidance"])
                self.assertFalse(app.guidance.label.winfo_manager())
                show_help(app)
                self.assertTrue(any(isinstance(child, tk.Toplevel) for child in app.winfo_children()))
                app.settings.save(dismissed_guidance=[])
                app.guidance.show("graph")
                self.assertEqual(app.guidance.label.winfo_manager(), "pack")
            finally:
                app.database.close()
                app.destroy()
