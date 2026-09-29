"""Recovery contracts use real on-disk databases and deliberately failed writes."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_atlas.database import Database
from story_atlas.models import LEGACY_PROFILE_FIELDS
from story_atlas.migrations import SchemaError, CURRENT_VERSION, initial_schema
from story_atlas.backup import snapshot, backup_directory, restore_backup
from story_atlas.imports import read_export, validate_payload, import_payload


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def database(self, name="active.db"):
        database = Database(self.folder / name)
        self.addCleanup(database.close)
        return database

    def original_database(self):
        path = self.folder / "legacy.db"
        connection = sqlite3.connect(path)
        fields = ",".join(f"{field} TEXT NOT NULL DEFAULT ''" for field in LEGACY_PROFILE_FIELDS)
        connection.executescript(f"""
            CREATE TABLE characters(id INTEGER PRIMARY KEY,{fields});
            CREATE TABLE relationships(id INTEGER PRIMARY KEY,
                source_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                target_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',
                CHECK(source_id != target_id),UNIQUE(source_id,target_id,kind));
            CREATE TABLE activity(id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                action TEXT NOT NULL,details TEXT NOT NULL);
            INSERT INTO characters(id,name,notes) VALUES(4,'Mira','雪'),(9,'Pip','');
            INSERT INTO relationships VALUES(7,4,9,'Ally','Shared history');
            INSERT INTO activity(action,details) VALUES('Created','Original event');
            PRAGMA user_version=1;
        """)
        connection.close()
        return path

    def test_migrates_original_schema_and_keeps_pre_migration_copy(self):
        path = self.original_database()
        database = Database(path)
        self.addCleanup(database.close)
        self.assertEqual(database.connection.execute("PRAGMA user_version").fetchone()[0], CURRENT_VERSION)
        self.assertEqual(database.characters()[0]["notes"], "雪")
        self.assertEqual(database.relationships()[0]["id"], 7)
        self.assertEqual(database.activity()[0]["details"], "Original event")
        backups = list(backup_directory(path).glob("pre-migration-*.db"))
        self.assertEqual(len(backups), 1)
        with sqlite3.connect(backups[0]) as original:
            self.assertEqual(original.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(original.execute("SELECT count(*) FROM characters").fetchone()[0], 2)
        original.close()
        again = Database(path)
        again.close()
        self.assertEqual(len(list(backup_directory(path).glob("pre-migration-*.db"))), 1)

    def test_failed_migration_rolls_back_schema_data_and_version(self):
        path = self.original_database()

        def fail(connection):
            connection.execute("ALTER TABLE characters ADD COLUMN temporary_column TEXT")
            connection.execute("UPDATE characters SET name='Changed'")
            raise RuntimeError("Injected migration failure")

        with patch("story_atlas.migrations.MIGRATIONS", (initial_schema, fail)):
            with self.assertRaises(RuntimeError):
                Database(path)
        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT name FROM characters WHERE id=4").fetchone()[0], "Mira")
            self.assertNotIn("temporary_column", [row[1] for row in connection.execute("PRAGMA table_info(characters)")])
        connection.close()

    def test_backup_failure_blocks_migration_and_newer_version_is_untouched(self):
        path = self.original_database()
        original = path.read_bytes()
        with patch("story_atlas.migrations.snapshot", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                Database(path)
        self.assertEqual(path.read_bytes(), original)
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version=999")
        connection.close()
        original = path.read_bytes()
        with self.assertRaisesRegex(SchemaError, "newer"):
            Database(path)
        self.assertEqual(path.read_bytes(), original)

    def test_backup_retention_and_restore_include_trash_and_drafts(self):
        database = self.database()
        ident = database.save_character({"name": "Mira"})
        database.drafts.save(None, {"name": "Uncommitted"})
        database.delete_character(ident)
        manual = snapshot(database.connection, database.path)
        for _ in range(4):
            snapshot(database.connection, database.path, "auto", retention=2)
        self.assertEqual(len(list(backup_directory(database.path).glob("auto-*.db"))), 2)
        self.assertTrue(manual.exists())
        destination = restore_backup(manual, self.folder / "restored.db")
        restored = Database(destination)
        self.addCleanup(restored.close)
        self.assertEqual(len(restored.trash.items()), 1)
        self.assertEqual(restored.drafts.list()[0]["values"]["name"], "Uncommitted")
        restored.trash.restore("character", ident)
        self.assertEqual(restored.characters()[0]["name"], "Mira")
        self.assertEqual(database.characters(), [])
        with self.assertRaises(ValueError):
            restore_backup(manual, database.path)

    def test_restore_legacy_and_reject_invalid_backup(self):
        legacy = self.original_database()
        before = legacy.read_bytes()
        result = restore_backup(legacy, self.folder / "restored.db")
        self.assertEqual(legacy.read_bytes(), before)
        restored = Database(result)
        self.addCleanup(restored.close)
        self.assertEqual(restored.relationships()[0]["source_id"], 4)
        bad = self.folder / "bad.db"
        bad.write_text("not sqlite")
        with self.assertRaises(sqlite3.DatabaseError):
            restore_backup(bad, self.folder / "failed.db")
        self.assertFalse((self.folder / "failed.db").exists())
        self.assertFalse(list(self.folder.glob(".story-atlas-*")))

    def test_export_import_round_trip_preserves_ids_text_and_activity(self):
        database = self.database()
        first = database.save_character({"name": "Mira", "notes": "雪 and apostrophe's"})
        second = database.save_character({"name": "Pip"})
        database.save_relationship(first, second, "Custom type", "Context")
        path = self.folder / "export.json"
        database.export_json(path)
        data = read_export(path)
        destination = import_payload(data, self.folder / "import.db")
        imported = Database(destination)
        self.addCleanup(imported.close)
        self.assertEqual(imported.characters(), database.characters())
        self.assertEqual(imported.relationships(), database.relationships())
        self.assertEqual(imported.activity(), data["activity"])

    def test_malformed_imports_never_touch_active_database(self):
        database = self.database()
        database.save_character({"name": "Existing"})
        before = list(database.connection.iterdump())
        base = dict(format_version=1, characters=[dict(id=1, name="Mira"), dict(id=2, name="Pip")],
                    relationships=[dict(id=1, source_id=1, target_id=2, kind="Friend", notes="")], activity=[])
        cases = []
        for edit in (
            lambda data: data.update(format_version=999),
            lambda data: data["characters"].append(data["characters"][0]),
            lambda data: data["characters"][0].update(name=123),
            lambda data: data["relationships"][0].update(target_id=99),
            lambda data: data["relationships"][0].update(source_id=True),
            lambda data: data["characters"][0].update(id=2**100),
            lambda data: data["relationships"].append(dict(id=2, source_id=1, target_id=2, kind="Friend")),
            lambda data: data.update(activity=[dict(id=1, action="broken")]),
        ):
            data = copy.deepcopy(base)
            edit(data)
            cases.append(data)
        for data in cases:
            with self.assertRaises(ValueError):
                import_payload(data, self.folder / "bad-import.db")
            self.assertFalse((self.folder / "bad-import.db").exists())
        invalid_json = self.folder / "bad.json"
        invalid_json.write_text("{invalid")
        with self.assertRaises(ValueError):
            read_export(invalid_json)
        self.assertEqual(list(database.connection.iterdump()), before)

    def test_import_mid_write_failure_leaves_no_destination(self):
        class BrokenDatabase(Database):
            def __init__(self, path):
                super().__init__(path)
                self.connection.execute("""CREATE TRIGGER fail_import BEFORE INSERT ON relationships
                    BEGIN SELECT RAISE(ABORT,'Injected failure'); END""")

        data = dict(characters=[dict(id=1, name="Mira"), dict(id=2, name="Pip")],
                    relationships=[dict(id=1, source_id=1, target_id=2, kind="Friend")])
        with patch("story_atlas.imports.Database", BrokenDatabase):
            with self.assertRaises(sqlite3.IntegrityError):
                import_payload(data, self.folder / "failed.db")
        self.assertFalse((self.folder / "failed.db").exists())
        self.assertFalse(list(self.folder.glob(".story-atlas-*")))

    def test_trash_restore_multiple_deleted_endpoints_and_explicit_links(self):
        database = self.database()
        first, second = [database.save_character({"name": name}) for name in ("A", "B")]
        automatic = database.save_relationship(first, second, "Ally")
        explicit = database.save_relationship(first, second, "Family")
        database.delete_relationship(explicit)
        database.delete_character(first)
        database.delete_character(second)
        with self.assertRaises(ValueError):
            database.trash.restore("relationship", automatic)
        database.trash.restore("character", first)
        self.assertEqual(database.relationships(), [])
        database.trash.restore("character", second)
        self.assertEqual([row["id"] for row in database.relationships()], [automatic])
        database.trash.restore("relationship", explicit)
        self.assertEqual(len(database.relationships()), 2)
        self.assertEqual(database.connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_trash_duplicate_conflict_preserves_original(self):
        database = self.database()
        first, second = [database.save_character({"name": name}) for name in ("A", "B")]
        old = database.save_relationship(first, second, "Ally", "Original context")
        database.delete_relationship(old)
        new = database.save_relationship(first, second, "Ally", "New context")
        with self.assertRaises(ValueError):
            database.trash.restore("relationship", old)
        self.assertEqual(database.relationships()[0]["id"], new)
        database.delete_relationship(new)
        database.trash.restore("relationship", old)
        self.assertEqual(database.relationships()[0]["notes"], "Original context")

    def test_drafts_are_uncommitted_and_save_clear_is_atomic(self):
        database = self.database()
        ident = database.save_character({"name": "Mira"})
        activity_count = len(database.activity())
        for note in ("a", "ab", "abc"):
            database.drafts.save(ident, {"name": "Draft name", "notes": note})
        self.assertEqual(database.characters()[0]["name"], "Mira")
        self.assertEqual(len(database.activity()), activity_count)
        self.assertEqual(len(database.drafts.list()), 1)
        with patch.object(database, "_log", side_effect=sqlite3.OperationalError("Injected failure")):
            with self.assertRaises(sqlite3.OperationalError):
                database.save_character({"name": "Changed"}, ident)
        self.assertEqual(len(database.drafts.list()), 1)
        self.assertEqual(database.characters()[0]["name"], "Mira")
        database.save_character({"name": "Changed"}, ident)
        self.assertEqual(database.drafts.list(), [])
