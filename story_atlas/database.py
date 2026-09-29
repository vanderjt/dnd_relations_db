"""SQLite persistence. Each write and its activity entry share a transaction."""
import json
import sqlite3
from pathlib import Path

from .models import PROFILE_FIELDS
from .migrations import migrate
from .drafts import Drafts
from .relationship_store import RelationshipStore
from .trash import Trash
from .assets import Assets, valid_reference
from .events import Events
from .chapters import Chapters
from .history import History
from .paths import validate_writable_location


class Database:
    def __init__(self, path, migration_backup=True):
        self.path = validate_writable_location(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        from .undo import Connection
        self.connection = sqlite3.connect(self.path, factory=Connection)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        try:
            migrate(self.connection, self.path, make_backup=migration_backup)
        except Exception:
            self.connection.close()
            raise
        self.drafts = Drafts(self.connection)
        self.trash = Trash(self)
        self.relationship_store = RelationshipStore(self)
        self.assets = Assets(self)
        self.events = Events(self)
        self.chapters = Chapters(self)
        self.history = History(self)
        self.undo = None

    def enable_undo(self):
        from .undo import UndoHistory
        if self.undo is None:
            self.undo = UndoHistory(self)
        return self.undo

    def characters(self, query=""):
        rows = self.connection.execute("SELECT * FROM characters WHERE deleted_at IS NULL ORDER BY name COLLATE NOCASE, id")
        # Literal substring search also handles %, underscores, and apostrophes.
        return [dict(row) for row in rows if query.casefold() in
                " ".join(str(row[field]) for field in PROFILE_FIELDS).casefold()]

    def save_character(self, values, character_id=None):
        data = {field: str(values.get(field, "")).strip() for field in PROFILE_FIELDS}
        if not data["name"]:
            raise ValueError("Please enter a character name.")
        if not valid_reference(data["portrait"]):
            raise ValueError("Choose a portrait using Import portrait.")
        previous = self.connection.execute('SELECT * FROM characters WHERE id=?', (character_id,)).fetchone() if character_id else None
        from .classification import validate
        data['classification'] = validate(values.get('classification') or (previous['classification'] if previous else 'Neutral'))
        data['narrative_role'] = values.get('narrative_role') or (previous['narrative_role'] if previous else 'neutral')
        if data['narrative_role'] not in ('neutral', 'protagonist', 'antagonist'):
            raise ValueError('Choose neutral, protagonist, or antagonist as the narrative role.')
        from .character_type import resolve, legacy_values
        data['character_type'] = resolve(values, previous)
        if values.get('character_type'):
            data['classification'], data['narrative_role'] = legacy_values(values['character_type'])
        data['introduction_event_id'] = values.get('introduction_event_id', previous['introduction_event_id'] if previous else None)
        draft_key = self.drafts.key(character_id)
        with self.connection:
            if character_id is None:
                fields = ", ".join(data)
                placeholders = ", ".join("?" for _ in data)
                cursor = self.connection.execute(
                    f"INSERT INTO characters ({fields}) VALUES ({placeholders})", tuple(data.values()))
                character_id = cursor.lastrowid
                action = "Character created"
            else:
                assignments = ", ".join(f"{field}=?" for field in data)
                cursor = self.connection.execute(f"UPDATE characters SET {assignments} WHERE id=? AND deleted_at IS NULL",
                                               (*data.values(), character_id))
                if not cursor.rowcount:
                    raise ValueError("This character no longer exists.")
                action = "Character updated"
            self.history.validate()
            if data['introduction_event_id'] is not None:
                self.connection.execute('INSERT OR IGNORE INTO event_participants VALUES (?,?)', (data['introduction_event_id'], character_id))
            self.connection.execute("DELETE FROM drafts WHERE key=?", (draft_key,))
            self._log(action, f"{data['name']} (#{character_id})")
        return character_id

    def duplicate_character(self, character_id):
        """Copy committed profile fields and portrait, but never relationships."""
        with self.connection:
            row = self.connection.execute("SELECT * FROM characters WHERE id=? AND deleted_at IS NULL", (character_id,)).fetchone()
            if row is None:
                raise ValueError("Choose an existing character to duplicate.")
            data = {field: row[field] for field in (*PROFILE_FIELDS, "introduction_event_id", "legacy_character_type")}
            data["name"] += " (copy)"
            fields = ",".join(data)
            marks = ",".join("?" for _ in data)
            cursor = self.connection.execute(f"INSERT INTO characters ({fields}) VALUES ({marks})", tuple(data.values()))
            self._log("Character duplicated", f"#{character_id} → #{cursor.lastrowid}; profile and portrait only, no relationships")
            return cursor.lastrowid

    def delete_character(self, character_id):
        self.trash.delete_character(character_id)

    def relationships(self, event_id=None):
        return self.history.states(event_id)

    def relationship_records(self):
        return [dict(row) for row in self.connection.execute("""
            SELECT r.*, s.name AS source_name, t.name AS target_name
            FROM relationships r JOIN characters s ON r.source_id=s.id
            JOIN characters t ON r.target_id=t.id
            WHERE r.deleted_at IS NULL AND s.deleted_at IS NULL AND t.deleted_at IS NULL ORDER BY r.id
        """)]

    def save_relationship(self, source, target, kind, notes="", relationship_id=None,
                          semantics=None, inverse_label=None, start_event=None, category=None):
        return self.relationship_store.save(source, target, kind, notes, relationship_id, semantics, inverse_label, start_event, category)

    def delete_relationship(self, relationship_id):
        self.trash.delete_relationship(relationship_id)

    def activity(self):
        return [dict(row) for row in self.connection.execute("SELECT * FROM activity ORDER BY id DESC")]

    def _log(self, action, details):
        self.connection.execute("INSERT INTO activity (action,details) VALUES (?,?)", (action, details))

    def log(self, action, details):
        with self.connection:
            self._log(action, details)

    def export_json(self, path):
        records = self.relationship_records()
        ids = {row["id"] for row in records}
        characters = self.characters()
        character_ids = {row["id"] for row in characters}
        payload = {"format_version": 9, "characters": characters, "chapters": self.chapters.list(),
                   "relationships": records, "activity": self.activity(), "story_metadata": [dict(row) for row in self.connection.execute("SELECT * FROM story_metadata")], "story_events": self.events.list(),
                   "event_participants": [row for row in self.events.participants() if row["character_id"] in character_ids],
                   "relationship_history": [row for row in self.history.rows() if row["relationship_id"] in ids]}
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log("JSON exported", str(path))

    def close(self):
        self.connection.close()
