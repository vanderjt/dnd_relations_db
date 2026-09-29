"""Soft deletion retains IDs and connections; restoration never merges records."""
from uuid import uuid4
from .relationship_semantics import check_duplicate, connection_label

NOW = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


class Trash:
    def __init__(self, database):
        self.db = database
        self.connection = database.connection

    def delete_character(self, ident):
        with self.connection:
            row = self.connection.execute("SELECT name FROM characters WHERE id=? AND deleted_at IS NULL", (ident,)).fetchone()
            if not row:
                return
            self.connection.execute(f"UPDATE characters SET deleted_at={NOW} WHERE id=?", (ident,))
            self.connection.execute(f"""UPDATE relationships SET deleted_at={NOW},deletion_group=?
                WHERE (source_id=? OR target_id=?) AND deleted_at IS NULL""", (uuid4().hex, ident, ident))
            self.connection.execute("DELETE FROM drafts WHERE key=?", (f"character:{ident}",))
            self.db._log("Character deleted", f"{row['name']} (#{ident}) moved to Trash with attached relationships")

    def delete_relationship(self, ident):
        with self.connection:
            row = self.connection.execute("SELECT * FROM relationships WHERE id=? AND deleted_at IS NULL", (ident,)).fetchone()
            if row:
                self.connection.execute(f"UPDATE relationships SET deleted_at={NOW},deletion_group=NULL WHERE id=?", (ident,))
                self.db._log("Relationship deleted", f"{connection_label(dict(row))} moved to Trash")

    def items(self):
        characters = [dict(row, type="character", label=row["name"]) for row in self.connection.execute(
            "SELECT id,name,deleted_at FROM characters WHERE deleted_at IS NOT NULL")]
        relationships = [dict(row, type="relationship", label=connection_label(dict(row)))
                         for row in self.connection.execute("""SELECT r.*,s.name AS source_name,t.name AS target_name
                             FROM relationships r JOIN characters s ON r.source_id=s.id
                             JOIN characters t ON r.target_id=t.id WHERE r.deleted_at IS NOT NULL""")]
        return sorted(characters + relationships, key=lambda row: row["deleted_at"], reverse=True)

    def restore(self, item_type, ident):
        if item_type not in ("character", "relationship"):
            raise ValueError("Unknown Trash item.")
        with self.connection:
            if item_type == "character":
                if not self.connection.execute("SELECT id FROM characters WHERE id=? AND deleted_at IS NOT NULL", (ident,)).fetchone():
                    raise ValueError("This character is not in Trash.")
                self.connection.execute("UPDATE characters SET deleted_at=NULL WHERE id=?", (ident,))
                candidates = self.connection.execute("""SELECT r.* FROM relationships r
                    JOIN characters s ON s.id=r.source_id JOIN characters t ON t.id=r.target_id
                    WHERE r.deleted_at IS NOT NULL AND r.deletion_group IS NOT NULL
                    AND (r.source_id=? OR r.target_id=?) AND s.deleted_at IS NULL AND t.deleted_at IS NULL""",
                    (ident, ident)).fetchall()
                for row in candidates:
                    self._restore_link(row)
            else:
                row = self.connection.execute("SELECT * FROM relationships WHERE id=?", (ident,)).fetchone()
                if not row:
                    raise ValueError("Relationship no longer exists.")
                self._restore_link(row)
            self.db._log("Trash restored", f"{item_type} #{ident}")

    def _restore_link(self, row):
        count = self.connection.execute("SELECT count(*) FROM characters WHERE id IN (?,?) AND deleted_at IS NULL",
                                        (row["source_id"], row["target_id"])).fetchone()[0]
        if count != 2:
            raise ValueError("Restore both characters before restoring their relationship.")
        if row["baseline_active"]:
            check_duplicate(dict(row), [item for item in self.db.relationship_records() if item["baseline_active"]], exclude=(row["id"],))
        self.connection.execute("UPDATE relationships SET deleted_at=NULL,deletion_group=NULL WHERE id=?", (row["id"],))
        self.db.history.validate()
