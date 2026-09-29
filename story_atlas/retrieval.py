"""Literal search and exact, composable roster filters; independent of Tk."""
import json
from .models import PROFILE_FIELDS
from .relationship_semantics import connection_label

FILTER_FIELDS = ("faction", "location", "status", "tags")


def tags(text):
    # Trim separator whitespace only. Case and spelling remain distinct.
    return [value.strip() for value in text.split(",") if value.strip()]


def suggestions(database, field):
    values = [row[field] for row in database.characters()]
    if field == "tags":
        values = [tag for value in values for tag in tags(value)]
    return sorted({value for value in values if value}, key=lambda value: (value.casefold(), value))


def filter_characters(database, query="", filters=None):
    filters = filters or {}
    return [row for row in database.characters(query) if
            all(not filters.get(field) or row[field] == filters[field] for field in FILTER_FIELDS[:-1])
            and all(tag in tags(row["tags"]) for tag in tags(filters.get("tags", "")))]


def snippet(text, query, length=130):
    text = " ".join(text.split())
    offset = max(0, text.casefold().find(query.casefold()) - 35)
    return ("…" if offset else "") + text[offset:offset+length] + ("…" if len(text) > offset+length else "")


def search(database, query):
    """Return all matches with stable IDs, field labels and matching context."""
    query = query.strip()
    if not query:
        return []
    results = []
    needle = query.casefold()
    def matching(fields):
        return next(((label, value) for label, value in fields if needle in value.casefold()), None)
    for row in database.characters():
        match = matching((label, row[field]) for field, label in PROFILE_FIELDS.items())
        if match:
            label, text = match
            results.append(dict(kind="character", id=row["id"], title=f"{row['name']} (#{row['id']})",
                                snippet=f"{label}: {snippet(text, query)}"))
    for row in database.chapters.list():
        match = matching((("Title", row['title']), ("Summary", row['summary'])))
        if match:
            label, value = match
            results.append(dict(kind='chapter', id=row['id'], title=f"{row['title']} (#{row['id']})",
                                snippet=f"{label}: {snippet(value, query)}"))
    for row in database.events.list():
        match = matching((("Title", row['title']), ("Summary", row['summary'])))
        if match:
            label, value = match
            results.append(dict(kind='event', id=row['id'], title=f"{row['title']} (#{row['id']})",
                                snippet=f"{label}: {snippet(value, query)}"))
    current = {row['id']: row for row in database.relationships()}
    records = database.relationship_records()  # Already excludes Trash and trashed endpoints.
    events = {row['id']: row for row in database.events.list()}
    history = database.history.rows()
    names = {row['id']: row['name'] for row in database.characters()}
    by_relationship = {}
    for state in history:
        by_relationship.setdefault(state['relationship_id'], []).append(state)
    def fields(row):
        return (("Notes", row['notes']), ("Type", row['kind']), ("Inverse label", row['inverse_label']),
                ("Meaning", row['semantics']), ("Source", row['source_name']), ("Target", row['target_name']))
    for row in current.values():
        match = matching(fields(row))
        if match:
            label, text = match
            results.append(dict(kind="relationship", id=row["id"],
                                title=f"{connection_label(row)} (#{row['id']})",
                                snippet=f"{label}: {snippet(text, query)}"))
    current_hit_ids = {row['id'] for row in results if row['kind'] == 'relationship'}
    for base in records:
        states = [dict(base, active=base['baseline_active'], event_id=None, state_id='baseline')]
        for state in by_relationship.get(base['id'], []):
            states.append(dict(state, source_name=names.get(state['source_id'], ''),
                               target_name=names.get(state['target_id'], ''), state_id=state['id']))
        for position, state in enumerate(states):
            match = matching(fields(state))
            if not match:
                continue
            if (position == len(states) - 1 and base['id'] in current_hit_ids and
                    all(state[field] == current[base['id']][field]
                        for field in ('kind', 'notes', 'inverse_label', 'semantics', 'source_id', 'target_id'))):
                continue
            label, value = match
            event = events.get(state['event_id'])
            effective = f"event {event['title']} (#{event['id']})" if event else 'Before first event'
            presence = 'Present' if state['active'] else 'Ended'
            results.append(dict(kind='history', id=base['id'], state_id=state['state_id'],
                                event_id=state['event_id'], presence=presence,
                                title=f"Historical · {presence} · {effective} · {connection_label(state)} (#{base['id']})",
                                snippet=f"{label}: {snippet(value, query)}"))
    return results


class SavedFilters:
    def __init__(self, database):
        self.database = database

    def names(self):
        return [row[0] for row in self.database.connection.execute("SELECT name FROM saved_filters ORDER BY name")]

    def save(self, name, state):
        if not name.strip():
            raise ValueError("Enter a filter name.")
        self.validate(state)
        with self.database.connection:
            self.database.connection.execute(
                "INSERT INTO saved_filters VALUES (?,?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload",
                (name.strip(), json.dumps(state)))

    def load(self, name):
        row = self.database.connection.execute("SELECT payload FROM saved_filters WHERE name=?", (name,)).fetchone()
        if row is None:
            raise ValueError("Choose an existing saved filter.")
        return self.validate(json.loads(row[0]))

    def validate(self, state):
        if not isinstance(state, dict) or set(state) != {"query", *FILTER_FIELDS} or any(
                not isinstance(value, str) for value in state.values()):
            raise ValueError("Invalid saved character filter.")
        return state

    def delete(self, name):
        with self.database.connection:
            self.database.connection.execute("DELETE FROM saved_filters WHERE name=?", (name,))
