"""Opt-in web-profile persistence foundation; not enabled by the Tkinter app.

Use disposable story copies until export/import and legacy UI integration ship.
The caller owns Database and must use this service on its connection's thread.
"""
import hashlib
import json


FIELDS = (
    'name', 'species', 'role', 'age', 'status', 'location', 'faction',
    'summary', 'health', 'armor', 'mana', 'inventory', 'skills', 'goals',
    'traits', 'backstory', 'notes', 'language', 'belief', 'title',
)
SCOPES = ('event_only', 'carry_forward')


class ProfileConflict(ValueError):
    """The story changed after this editor read its profile."""


def resolve_profile(baseline, changes, events, event_id):
    """Resolve exact overrides, then continuing decisions, then baseline.

    IDs identify moments; sequence determines order. Blank is an authored value.
    Changes passed here must belong to one character.
    """
    order = {event['id']: event['sequence'] for event in events}
    if event_id not in order:
        raise ValueError('Choose an existing event.')
    values = {key: str(baseline.get(key, '') or '') for key in FIELDS}
    sources = {key: None for key in FIELDS}
    for row in sorted(changes, key=lambda r: order[r['event_id']]):
        if row['field'] not in FIELDS or row['scope'] not in SCOPES:
            raise ValueError('Invalid stored profile decision.')
        if order[row['event_id']] > order[event_id]:
            continue
        if row['scope'] == 'carry_forward' or row['event_id'] == event_id:
            values[row['field']] = row['value']
            sources[row['field']] = {'event_id': row['event_id'], 'scope': row['scope']}
    return {'values': values, 'sources': sources}


class ProfileHistory:
    """Explicit experimental schema, atomic saves, and stale-editor protection.

    Tables are deliberately not part of migrations.MIGRATIONS yet: this is a
    test/development service, not a supported production-file upgrade path.
    No baseline columns or existing relationship records are rewritten.
    """
    def __init__(self, database):
        self.db = database
        self.connection = database.connection
        if database.undo is not None:
            raise ValueError('Use a disposable story without legacy Undo enabled.')
        if self.connection.in_transaction:
            raise ValueError('Finish the current transaction before opening profile history.')
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            self.connection.execute('''CREATE TABLE IF NOT EXISTS web_profile_schema (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), version INTEGER NOT NULL)''')
            self.connection.execute('INSERT OR IGNORE INTO web_profile_schema VALUES (1,1)')
            if self.connection.execute('SELECT version FROM web_profile_schema').fetchone()[0] != 1:
                raise ValueError('Unsupported experimental profile schema.')
            allowed = ','.join("'" + field + "'" for field in FIELDS)
            self.connection.execute(f'''CREATE TABLE IF NOT EXISTS web_profile_history (
                character_id INTEGER NOT NULL REFERENCES characters(id),
                event_id INTEGER NOT NULL REFERENCES story_events(id),
                field TEXT NOT NULL CHECK(field IN ({allowed})), value TEXT NOT NULL,
                scope TEXT NOT NULL CHECK(scope IN ('event_only','carry_forward')),
                PRIMARY KEY(character_id,event_id,field))''')

    def _character(self, character_id):
        if type(character_id) is not int:
            raise ValueError('Choose an existing character.')
        row = self.connection.execute(
            'SELECT * FROM characters WHERE id=? AND deleted_at IS NULL', (character_id,)
        ).fetchone()
        if row is None:
            raise ValueError('Choose an existing character.')
        return dict(row)

    def _event(self, event_id):
        if type(event_id) is not int or not any(e['id'] == event_id for e in self.db.events.list()):
            raise ValueError('Choose an existing event.')

    def revision(self):
        # Also detects legacy baseline edits and chronology changes, rather than
        # relying on a counter that only this new service would increment.
        tables = ('characters', 'story_events', 'web_profile_history')
        state = [[dict(r) for r in self.connection.execute(f'SELECT * FROM {t} ORDER BY rowid')]
                 for t in tables]
        return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def _read(self, character_id, event_id):
        base = self._character(character_id)
        self._event(event_id)
        rows = [dict(r) for r in self.connection.execute(
            'SELECT * FROM web_profile_history WHERE character_id=?', (character_id,))]
        return {'character_id': character_id, 'event_id': event_id,
                **resolve_profile(base, rows, self.db.events.list(), event_id),
                'revision': self.revision()}

    def get_profile(self, character_id, event_id):
        if self.connection.in_transaction:
            raise ValueError('Read profiles outside an existing transaction.')
        # Keep values and revision in one SQLite read snapshot.
        with self.connection:
            self.connection.execute('BEGIN')
            return self._read(character_id, event_id)

    def save_profile(self, character_id, event_id, changes, expected_revision):
        """Commit field decisions, activity, and this context's draft atomically.

        changes = [{field, value, scope}]. An empty list is a no-op. This command
        is naturally idempotent by character/event/field, but stale retries are
        rejected; request receipts belong to the later bridge service.
        """
        if self.connection.in_transaction or self.db.undo is not None:
            raise ValueError('Profile saves require their own transaction without legacy Undo.')
        if not isinstance(changes, list):
            raise ValueError('Provide a list of field changes.')
        seen = set()
        for row in changes:
            if not isinstance(row, dict) or set(row) != {'field', 'value', 'scope'}:
                raise ValueError('Each change needs a field, value, and scope.')
            key, value, scope = row['field'], row['value'], row['scope']
            if not isinstance(key, str) or key not in FIELDS or key in seen:
                raise ValueError('Choose each supported profile field at most once.')
            if not isinstance(value, str) or scope not in SCOPES:
                raise ValueError('Use a text value and a valid change scope.')
            if key == 'name' and not value.strip():
                raise ValueError('Please enter a character name.')
            seen.add(key)
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            self._character(character_id)
            self._event(event_id)
            if not isinstance(expected_revision, str) or expected_revision != self.revision():
                raise ProfileConflict('The story changed. Reload this profile before saving.')
            for row in changes:
                self.connection.execute('''INSERT INTO web_profile_history VALUES (?,?,?,?,?)
                    ON CONFLICT(character_id,event_id,field)
                    DO UPDATE SET value=excluded.value,scope=excluded.scope''',
                    (character_id, event_id, row['field'], row['value'], row['scope']))
            if changes:
                self.connection.execute('DELETE FROM drafts WHERE key=?',
                                        (f'web-profile:{character_id}:{event_id}',))
                self.db._log('Event profile saved',
                             f'Character #{character_id}, event #{event_id}: {", ".join(sorted(seen))}')
            result = self._read(character_id, event_id)
        return result
