"""One recent creation, refused if any later committed action occurred."""
class RecentCreation:
    def __init__(self, database, ident):
        self.database, self.ident = database, ident
        self.row = next(row for row in database.characters() if row['id'] == ident)
        self.revision = database.activity()[0]['id']

    def undo(self):
        db = self.database
        current = next((row for row in db.characters() if row['id'] == self.ident), None)
        if not db.activity() or db.activity()[0]['id'] != self.revision or current != self.row:
            raise ValueError('Later changes exist. Undo is unavailable; use the profile and Trash tools instead.')
        if any(self.ident in (r['source_id'], r['target_id']) for r in db.relationship_records()):
            raise ValueError('This character now has connections. Undo is unavailable.')
        db.delete_character(self.ident)
