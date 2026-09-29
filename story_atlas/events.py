"""Fictional events, participants and sequence ordering, separate from activity."""


class Events:
    def __init__(self, database):
        self.db = database

    def list(self):
        return [dict(row) for row in self.db.connection.execute("SELECT * FROM story_events ORDER BY sequence,id")]

    def participants(self):
        return [dict(row) for row in self.db.connection.execute("SELECT * FROM event_participants ORDER BY event_id,character_id")]

    def removal_preview(self, ident, replacement):
        """Explicit review of every reference, including characters in Trash."""
        events = {row['id']: row for row in self.list()}
        if ident not in events or replacement not in events or ident == replacement:
            raise ValueError('Choose the event to remove and a different replacement event.')
        return dict(event=events[ident], replacement=events[replacement],
                    introductions=[dict(row) for row in self.db.connection.execute('SELECT * FROM characters WHERE introduction_event_id=?', (ident,))],
                    states=[row for row in self.db.history.rows() if row['event_id'] == ident],
                    participants=[row for row in self.participants() if row['event_id'] == ident],
                    drafts=[row for row in self.db.drafts.list() if row['values'].get('introduction_event_id') == ident])

    def remove(self, preview):
        ident, replacement = preview['event']['id'], preview['replacement']['id']
        with self.db.connection:
            if self.removal_preview(ident, replacement) != preview:
                raise ValueError('Event references changed. Review the reassignment again.')
            if self.db.connection.execute('SELECT 1 FROM relationship_history a JOIN relationship_history b ON a.relationship_id=b.relationship_id WHERE a.event_id=? AND b.event_id=?', (ident, replacement)).fetchone():
                raise ValueError('Both events contain a state for the same relationship. Choose another replacement; existing entries cannot be merged.')
            from .backup import snapshot
            snapshot(self.db.connection, self.db.path, 'pre-event-removal')
            self.db.connection.execute('UPDATE characters SET introduction_event_id=? WHERE introduction_event_id=?', (replacement, ident))
            import json
            for draft in preview['drafts']:
                values = dict(draft['values'], introduction_event_id=replacement)
                self.db.connection.execute('UPDATE drafts SET payload=? WHERE key=?', (json.dumps(values, ensure_ascii=False), draft['key']))
            self.db.connection.execute('UPDATE relationship_history SET event_id=? WHERE event_id=?', (replacement, ident))
            self.db.connection.execute('INSERT OR IGNORE INTO event_participants SELECT ?,character_id FROM event_participants WHERE event_id=?', (replacement, ident))
            self.db.connection.execute('DELETE FROM event_participants WHERE event_id=?', (ident,))
            self.db.connection.execute('DELETE FROM story_events WHERE id=?', (ident,))
            self.db.history.validate()
            self.db._log('Event removed after reassignment', f"Event #{ident}; introductions, states, participants explicitly reassigned to #{replacement}")

    def save(self, title, summary, sequence, participants=(), ident=None):
        with self.db.connection:
            ident = self.write(title, summary, sequence, participants, ident)
            self.db.history.validate()
            self.db._log("Story event saved", f"Event #{ident}: {title}")
        return ident

    def write(self, title, summary, sequence, participants=(), ident=None):
        """Write within the caller's transaction; defer timeline validation."""
        if not isinstance(title, str) or not title.strip() or not isinstance(summary, str):
            raise ValueError("An event needs a title and text summary.")
        if type(sequence) is not int or not 1 <= sequence <= 1000000000:
            raise ValueError("Sequence must be a whole number from 1 to 1000000000.")
        known = {row[0] for row in self.db.connection.execute("SELECT id FROM characters")}
        if any(type(value) is not int or value not in known for value in participants):
            raise ValueError("Choose existing participating characters.")
        if any(row["sequence"] == sequence and row["id"] != ident for row in self.list()):
            raise ValueError("That sequence number is in use. Choose another number or use Move earlier/later.")
        if ident is None:
            ident = self.db.connection.execute("INSERT INTO story_events(title,summary,sequence) VALUES (?,?,?)",
                                              (title.strip(), summary, sequence)).lastrowid
        elif not self.db.connection.execute("UPDATE story_events SET title=?,summary=?,sequence=? WHERE id=?",
                                           (title.strip(), summary, sequence, ident)).rowcount:
            raise ValueError("This event no longer exists.")
        self.db.connection.execute("DELETE FROM event_participants WHERE event_id=?", (ident,))
        self.db.connection.executemany("INSERT INTO event_participants VALUES (?,?)", [(ident, value) for value in set(participants)])
        return ident

    def move(self, ident, offset):
        rows = self.list()
        chosen = next((row for row in rows if row['id'] == ident), None)
        if chosen:
            rows = [row for row in rows if row['chapter_id'] == chosen['chapter_id']]
        index = next((i for i, row in enumerate(rows) if row["id"] == ident), None)
        if index is None:
            raise ValueError("Choose an existing event.")
        other = index + offset
        if not 0 <= other < len(rows):
            return
        a, b = rows[index], rows[other]
        with self.db.connection:
            temporary = max(row["sequence"] for row in rows) + 1
            self.db.connection.execute("UPDATE story_events SET sequence=? WHERE id=?", (temporary, a["id"]))
            self.db.connection.execute("UPDATE story_events SET sequence=? WHERE id=?", (a["sequence"], b["id"]))
            self.db.connection.execute("UPDATE story_events SET sequence=? WHERE id=?", (b["sequence"], a["id"]))
            self.db.history.validate()
            self.db._log("Story events reordered", f"Events #{a['id']} and #{b['id']} exchanged sequence positions")
