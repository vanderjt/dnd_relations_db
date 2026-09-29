"""Draft snapshots are separate from committed characters and activity history."""
import json


class Drafts:
    def __init__(self, connection):
        self.connection = connection

    @staticmethod
    def key(character_id):
        return f"character:{character_id}" if character_id is not None else "new"

    def save(self, character_id, values):
        self.save_task(self.key(character_id), values)

    def save_task(self, key, values):
        with self.connection:
            self.connection.execute("""INSERT INTO drafts(key,payload) VALUES (?,?)
                ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,
                updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')""",
                (key, json.dumps(values, ensure_ascii=False)))

    def discard(self, character_id):
        self.discard_task(self.key(character_id))

    def discard_task(self, key):
        with self.connection:
            self.connection.execute("DELETE FROM drafts WHERE key=?", (key,))

    def list(self):
        return [dict(row, values=json.loads(row["payload"])) for row in
                self.connection.execute("SELECT * FROM drafts ORDER BY updated_at DESC")]
