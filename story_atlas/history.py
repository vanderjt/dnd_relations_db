"""Dated relationship states and explicit corrections, with whole-timeline checks."""
from .history_model import STATE_FIELDS, resolve, validate_timeline
from .relationship_semantics import normalize


class History:
    def __init__(self, database):
        self.db = database

    def rows(self, relationship_id=None):
        rows = [dict(row) for row in self.db.connection.execute("""SELECT h.* FROM relationship_history h
            JOIN story_events e ON e.id=h.event_id ORDER BY e.sequence,h.id""")]
        return [row for row in rows if relationship_id is None or row["relationship_id"] == relationship_id]

    def states(self, event_id=None):
        rows = resolve(self.db.relationship_records(), self.rows(), self.db.events.list(), event_id)
        names = {row["id"]: row["name"] for row in self.db.characters()}
        for row in rows:
            row.update(source_name=names[row["source_id"]], target_name=names[row["target_id"]])
        return rows

    def editing_state(self, relationship_id, event_id=None):
        """Exact effective entry, including inactive states; None=Current, 0=baseline.

        Dated entries retain their state ID, not the relationship ID.
        """
        base = next((row for row in self.db.relationship_records() if row['id'] == relationship_id), None)
        if base is None:
            raise ValueError('Choose an existing relationship.')
        state = dict(base, active=bool(base['baseline_active']), event_id=None)
        if event_id == 0:
            return state
        events = {row['id']: row['sequence'] for row in self.db.events.list()}
        if event_id is not None and event_id not in events:
            raise ValueError('The originating event is no longer available.')
        for row in self.rows(relationship_id):
            if event_id is None or events[row['event_id']] <= events[event_id]:
                state = row
        return state

    def state_before(self, relationship_id, event_id):
        """Return the full state immediately before an event, including an ended one."""
        base = next((row for row in self.db.relationship_records() if row["id"] == relationship_id), None)
        event = next((row for row in self.db.events.list() if row["id"] == event_id), None)
        if base is None or event is None:
            raise ValueError("Choose an existing relationship and event.")
        state = dict(base, active=bool(base.get("baseline_active", 1)))
        sequence = event["sequence"]
        events = {row["id"]: row["sequence"] for row in self.db.events.list()}
        for change in self.rows(relationship_id):
            if events[change["event_id"]] < sequence:
                state.update(change)
        return state

    def validate(self):
        validate_timeline(self.db.relationship_records(), self.rows(), self.db.events.list())
        from .introductions import validate_introductions
        cast = [dict(row) for row in self.db.connection.execute('SELECT * FROM characters')]
        validate_introductions(cast, self.db.relationship_records(), self.rows(), self.db.events.list())

    def write(self, relationship_id, event_id, values, active=True, correction_id=None, draft_key=None):
        base = next((row for row in self.db.relationship_records() if row["id"] == relationship_id), None)
        if base is None:
            raise ValueError("Restore this relationship and its characters before editing its history.")
        prior = (next((row for row in self.rows(relationship_id) if row['id'] == correction_id), base)
                 if correction_id is not None else self.state_before(relationship_id, event_id))
        data = normalize(*(values[key] for key in STATE_FIELDS[:3]), values.get("notes", ""),
                         values.get("semantics", "directional"), values.get("inverse_label", ""), values.get("category", prior.get("category", "")))
        if {data["source_id"], data["target_id"]} != {base["source_id"], base["target_id"]}:
            raise ValueError("A relationship timeline keeps the same character pair. Create another relationship for different characters.")
        if type(active) is not bool:
            raise ValueError("Choose whether the connection is present or ended.")
        if event_id not in {row["id"] for row in self.db.events.list()}:
            raise ValueError("Choose an existing story event.")
        with self.db.connection:
            if correction_id is None:
                if self.db.connection.execute("SELECT id FROM relationship_history WHERE relationship_id=? AND event_id=?",
                                              (relationship_id, event_id)).fetchone():
                    raise ValueError("A state already exists at this event. Use Correct entry to fix it.")
                payload = dict(relationship_id=relationship_id, event_id=event_id, active=int(active), **data)
                cursor = self.db.connection.execute(f"INSERT INTO relationship_history ({','.join(payload)}) VALUES ({','.join('?' for _ in payload)})",
                                                    tuple(payload.values()))
                ident = cursor.lastrowid
            else:
                previous = next((row for row in self.rows(relationship_id) if row["id"] == correction_id), None)
                if previous is None:
                    raise ValueError("Select an existing state to correct.")
                if any(row["event_id"] == event_id and row["id"] != correction_id for row in self.rows(relationship_id)):
                    raise ValueError("This relationship already has a state at that event.")
                payload = dict(event_id=event_id, active=int(active), **data)
                self.db.connection.execute(f"UPDATE relationship_history SET {','.join(key+'=?' for key in payload)} WHERE id=?",
                                           (*payload.values(), correction_id))
                ident = correction_id
            self.validate()
            if draft_key:
                self.db.connection.execute('DELETE FROM drafts WHERE key=?', (draft_key,))
            self.db._log("Relationship history corrected" if correction_id else "Story relationship change recorded",
                         f"Relationship #{relationship_id}, event #{event_id}, state #{ident}, {'present' if active else 'ended'}")
        return ident

    def correct_baseline(self, relationship_id, values, active, draft_key=None):
        base = next((row for row in self.db.relationship_records() if row["id"] == relationship_id), None)
        if base is None:
            raise ValueError("Choose an existing relationship.")
        if type(active) is not bool:
            raise ValueError("Choose whether the connection is present or absent.")
        data = normalize(*(values[key] for key in STATE_FIELDS[:3]), values.get("notes", ""),
                         values.get("semantics", "directional"), values.get("inverse_label", ""), values.get("category", base.get("category", "")))
        if self.rows(relationship_id) and {data["source_id"], data["target_id"]} != {base["source_id"], base["target_id"]}:
            raise ValueError("A timeline must keep the same character pair.")
        known = {row["id"] for row in self.db.characters()}
        if data["source_id"] not in known or data["target_id"] not in known:
            raise ValueError("Choose active characters for the starting state.")
        with self.db.connection:
            self.db.connection.execute(f"UPDATE relationships SET {','.join(key+'=?' for key in data)},baseline_active=? WHERE id=?",
                                       (*data.values(), int(active), relationship_id))
            self.validate()
            if draft_key:
                self.db.connection.execute('DELETE FROM drafts WHERE key=?', (draft_key,))
            self.db._log("Relationship baseline corrected", f"Relationship #{relationship_id}; starting state corrected")
