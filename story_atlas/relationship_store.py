"""Transactional writes and explicit, lossless reciprocal consolidation."""
import sqlite3
from .relationship_semantics import normalize, check_duplicate, mutual, connection_label
from .history_model import validate_timeline


class RelationshipStore:
    def __init__(self, database):
        self.db = database

    def validate(self, data, ident=None, exclude=()):
        connection = self.db.connection
        if connection.execute("SELECT count(*) FROM characters WHERE id IN (?,?) AND deleted_at IS NULL",
                              (data["source_id"], data["target_id"])).fetchone()[0] != 2:
            raise ValueError("Choose two existing characters that are not in Trash.")
        if ident is not None and not connection.execute(
                "SELECT id FROM relationships WHERE id=? AND deleted_at IS NULL", (ident,)).fetchone():
            raise ValueError("This relationship no longer exists.")
        check_duplicate(data, self.db.relationships(), (*exclude, ident))

    def insert(self, data):
        fields = ",".join(data)
        return self.db.connection.execute(f"INSERT INTO relationships ({fields}) VALUES ({','.join('?' for _ in data)})",
                                          tuple(data.values())).lastrowid

    def batch(self, pairs, kind, notes, semantics, inverse_label, event_id, preview=False, draft_key=None, category=""):
        """Validate or commit the complete one-to-many batch in one transaction.

        Do not call save() here: its connection context owns a commit.
        Preview executes the identical validation path and rolls it back.
        """
        if not pairs or len(set(pairs)) != len(pairs):
            raise ValueError('Choose a source and distinct targets.')
        if len({source for source, _ in pairs}) != 1:
            raise ValueError('A batch has exactly one source.')
        if event_id is not None and event_id not in {row['id'] for row in self.db.events.list()}:
            raise ValueError('Choose an existing effective event.')
        reviewed = []
        connection = self.db.connection
        connection.execute('SAVEPOINT relationship_batch')
        try:
            for source, target in pairs:
                data = normalize(source, target, kind, notes, semantics, inverse_label, category)
                self.validate(data)
                ident = self.insert(dict(data, baseline_active=int(event_id is None)))
                if event_id is not None:
                    payload = dict(relationship_id=ident, event_id=event_id, active=1, **data)
                    connection.execute(f"INSERT INTO relationship_history ({','.join(payload)}) VALUES ({','.join('?' for _ in payload)})", tuple(payload.values()))
                reviewed.append(dict(data, id=ident, event_id=event_id))
            self.db.history.validate()
            if preview:
                connection.execute('ROLLBACK TO relationship_batch')
            else:
                if draft_key:
                    connection.execute('DELETE FROM drafts WHERE key=?', (draft_key,))
                self.db._log('Relationship batch saved', f"Connections {[row['id'] for row in reviewed]}; event {event_id}")
            connection.execute('RELEASE relationship_batch')
        except Exception:
            connection.execute('ROLLBACK TO relationship_batch')
            connection.execute('RELEASE relationship_batch')
            raise
        if not preview and self.db.undo is not None and not connection.in_transaction:
            self.db.undo.checkpoint()
        return reviewed

    def save(self, source, target, kind, notes="", ident=None, semantics=None, inverse_label=None, start_event=None, category=None):
        previous = self.db.history.editing_state(ident) if ident is not None else {}
        category = previous.get("category", "") if category is None else category
        # Callers editing notes must not implicitly convert an existing record.
        semantics = previous.get("semantics", "directional") if semantics is None else semantics
        inverse_label = previous.get("inverse_label", "") if inverse_label is None else inverse_label
        data = normalize(source, target, kind, notes, semantics, inverse_label, category)
        data["notes"] = data["notes"].strip()
        dated = self.db.history.rows(ident) if ident is not None else []
        if dated:
            latest = dated[-1]
            self.db.history.write(ident, latest["event_id"], data, bool(latest["active"]), latest["id"])
            return ident
        try:
            with self.db.connection:
                self.validate(data, ident)
                if ident is None:
                    ident = self.insert(dict(data, baseline_active=0 if start_event is not None else 1))
                    if start_event is not None:
                        if start_event not in {row["id"] for row in self.db.events.list()}:
                            raise ValueError("Choose an existing start event.")
                        payload = dict(relationship_id=ident, event_id=start_event, active=1, **data)
                        self.db.connection.execute(f"INSERT INTO relationship_history ({','.join(payload)}) VALUES ({','.join('?' for _ in payload)})", tuple(payload.values()))
                else:
                    self.db.connection.execute(f"UPDATE relationships SET {','.join(field+'=?' for field in data)} WHERE id=?",
                                               (*data.values(), ident))
                self.db.history.validate()
                self.db._log("Relationship saved", f"#{ident}: {connection_label(data)}; {semantics}; {data['notes']}")
        except sqlite3.IntegrityError as error:
            raise ValueError("That relationship already exists or conflicts with another connection.") from error
        return ident

    def preview_consolidation(self, first_id, second_id, kind):
        rows = {row["id"]: row for row in self.db.relationships()}
        if first_id == second_id or first_id not in rows or second_id not in rows:
            raise ValueError("Select two existing reciprocal records.")
        first, second = rows[first_id], rows[second_id]
        if self.db.history.rows(first_id) or self.db.history.rows(second_id):
            raise ValueError("Consolidation supports undated records only. Use History to record a dated story change without discarding its timeline.")
        if mutual(first) or mutual(second) or (first["source_id"], first["target_id"]) != (second["target_id"], second["source_id"]):
            raise ValueError("Consolidation requires two directional records with reversed endpoints.")
        # Keep BOTH notes, even if identical. Provenance retains conflicting
        # labels and inverse labels; exact original records also remain in Trash.
        notes = "\n\n".join(f"Original relationship #{row['id']}: {connection_label(row)}\n"
                             f"Directional; inverse label: {row['inverse_label'] or '(none)'}\nNotes:\n{row['notes']}"
                             for row in (first, second))
        data = normalize(first["source_id"], first["target_id"], kind, notes, "mutual")
        self.validate(data, exclude=(first_id, second_id))
        remaining = [row for row in self.db.relationship_records() if row["id"] not in (first_id, second_id)]
        validate_timeline([*remaining, dict(data, id=-1, baseline_active=1)], self.db.history.rows(), self.db.events.list())
        return dict(originals=[first, second], result=data)

    def consolidate(self, preview):
        with self.db.connection:
            self.db.connection.execute("BEGIN IMMEDIATE")
            first, second = preview["originals"]
            current = self.preview_consolidation(first["id"], second["id"], preview["result"]["kind"])
            if current != preview:
                raise ValueError("These records changed after the preview. Review a fresh preview before consolidating.")
            self.db.connection.execute("""UPDATE relationships SET deleted_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                deletion_group=NULL WHERE id IN (?,?)""", (first["id"], second["id"]))
            ident = self.insert(current["result"])
            self.db.history.validate()
            self.db._log("Relationships consolidated", f"Directional #{first['id']} and #{second['id']} retained in Trash; new mutual #{ident}")
        return ident
