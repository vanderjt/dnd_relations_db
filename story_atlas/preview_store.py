"""Isolated preview format. No production migrations or legacy transaction owners.

Only PreviewWorker may own this connection in the desktop application. Domain
commands each commit facts, revision, receipt, audit, and draft cleanup together.
"""
from pathlib import Path
import hashlib
import json
import sqlite3
import uuid
import base64
import binascii

from .profile_history import FIELDS, SCOPES, resolve_profile
from .relationship_semantics import normalize, check_duplicate

APPLICATION_ID = 0x53415056  # SAPV
FORMAT_VERSION = 10002  # Also rejected by older Tkinter migration code.
WORLD_FIELDS = ('species', 'role', 'faction', 'location', 'language', 'belief', 'title')


class Conflict(ValueError):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def text(value, label, required=False):
    if not isinstance(value, str) or len(value) > 200000 or (required and not value.strip()):
        raise ValueError(f'Enter {label}{" (required)" if required else " as text"}.')
    return value


class PreviewStore:
    def __init__(self, path):
        self.path = Path(path).resolve()
        # mode=rw must never create a missing path on Open.
        self.connection = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=10)
        self.connection.row_factory = sqlite3.Row
        try:
            if (self.connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                    or self.connection.execute('PRAGMA user_version').fetchone()[0] != FORMAT_VERSION):
                raise ValueError('This is not a supported Story Atlas Preview story. Open a .atlas-preview file; legacy import is not available.')
            if self.connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('This story failed its database integrity check. Restore a backup.')
            self.connection.execute('PRAGMA foreign_keys=ON')
            self.connection.execute('PRAGMA synchronous=FULL')
        except Exception:
            self.connection.close()
            raise

    @classmethod
    def create(cls, path, title, sample=None):
        text(title, 'a story title', True)
        path = Path(path)
        # Exclusive reservation: never overwrite a user's story.
        with path.open('xb'):
            pass
        connection = sqlite3.connect(path)
        try:
            connection.executescript('''
                PRAGMA foreign_keys=ON;
                CREATE TABLE metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    title TEXT NOT NULL, revision INTEGER NOT NULL, story_id TEXT NOT NULL);
                CREATE TABLE chapters(id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '', sequence INTEGER NOT NULL UNIQUE);
                CREATE TABLE world_entries(id INTEGER PRIMARY KEY, category TEXT NOT NULL,
                    name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', UNIQUE(category,name));
                CREATE TABLE story_events(id INTEGER PRIMARY KEY, chapter_id INTEGER NOT NULL REFERENCES chapters(id),
                    title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', sequence INTEGER NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT '' CHECK(status IN ('','Planned','Happened')),
                    purpose TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
                    location_id INTEGER REFERENCES world_entries(id));
                CREATE TABLE characters(id INTEGER PRIMARY KEY, baseline TEXT NOT NULL);
                CREATE TABLE profile_history(character_id INTEGER REFERENCES characters(id),
                    event_id INTEGER REFERENCES story_events(id), field TEXT NOT NULL, value TEXT NOT NULL,
                    scope TEXT NOT NULL CHECK(scope IN ('event_only','carry_forward')),
                    PRIMARY KEY(character_id,event_id,field));
                CREATE TABLE event_participants(event_id INTEGER REFERENCES story_events(id),
                    character_id INTEGER REFERENCES characters(id), PRIMARY KEY(event_id,character_id));
                CREATE TABLE drafts(key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE receipts(request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL);
                CREATE TABLE activity(id INTEGER PRIMARY KEY, action TEXT NOT NULL, details TEXT NOT NULL,
                    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
                CREATE TABLE preferences(key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE connections(id INTEGER PRIMARY KEY, source_id INTEGER REFERENCES characters(id),
                    target_id INTEGER REFERENCES characters(id), baseline TEXT, CHECK(source_id!=target_id));
                CREATE TABLE connection_history(connection_id INTEGER REFERENCES connections(id),
                    event_id INTEGER REFERENCES story_events(id), state TEXT NOT NULL,
                    scope TEXT NOT NULL CHECK(scope IN ('event_only','carry_forward')),
                    PRIMARY KEY(connection_id,event_id));
            ''')
            with connection:
                connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
                connection.execute(f'PRAGMA user_version={FORMAT_VERSION}')
                connection.execute('INSERT INTO metadata VALUES(1,?,0,?)', (title, str(uuid.uuid4())))
                chapters = sample['chapters'] if sample else [{'id': 1, 'title': 'Chapter 1', 'summary': '', 'sequence': 1}]
                events = sample['events'] if sample else [{'id': 1, 'title': 'Opening scene', 'summary': '', 'sequence': 1, 'chapter_id': 1}]
                for row in chapters:
                    connection.execute('INSERT INTO chapters VALUES(?,?,?,?)', (row['id'], row['title'], row['summary'], row['sequence']))
                for row in events:
                    connection.execute('INSERT INTO story_events(id,chapter_id,title,summary,sequence,status) VALUES(?,?,?,?,?,?)',
                                       (row['id'], row['chapter_id'], row['title'], row['summary'], row['sequence'], '' if sample else 'Planned'))
                for row in (sample or {}).get('characters', []):
                    base = {key: str(row.get(key, '') or '') for key in FIELDS}
                    for key in WORLD_FIELDS:
                        if base[key]:
                            connection.execute('INSERT OR IGNORE INTO world_entries(category,name) VALUES(?,?)', (key, base[key]))
                            ident = connection.execute('SELECT id FROM world_entries WHERE category=? AND name=?', (key, base[key])).fetchone()[0]
                            base[key] = f'@world:{ident}'
                    connection.execute('INSERT INTO characters VALUES(?,?)', (row['id'], encoded(base)))
                if sample:
                    # Preserve every source record and only author real snapshot transitions.
                    state_keys = ('source_id', 'target_id', 'kind', 'notes', 'semantics', 'inverse_label', 'category')
                    def state(row):
                        return {key: row.get(key, '') for key in state_keys}
                    previous = {row['id']: state(row) for row in sample['opening_relationships']}
                    all_rows = {row['id']: row for rows in sample['relationships'].values() for row in rows}
                    all_rows.update({row['id']: row for row in sample['opening_relationships']})
                    for ident, row in all_rows.items():
                        connection.execute('INSERT INTO connections VALUES(?,?,?,?)',
                            (ident, row['source_id'], row['target_id'], encoded(previous.get(ident))))
                    for event in events:
                        current = {row['id']: state(row) for row in sample['relationships'][str(event['id'])]}
                        for ident in previous.keys() | current.keys():
                            if previous.get(ident) != current.get(ident):
                                connection.execute('INSERT INTO connection_history VALUES(?,?,?,?)',
                                    (ident, event['id'], encoded(current.get(ident)), 'carry_forward'))
                        previous = current
            connection.close()
            return cls(path)
        except Exception:
            connection.close()
            # This path was exclusively created above, never an existing file.
            path.unlink(missing_ok=True)
            raise

    def close(self):
        self.connection.close()

    def rows(self, query, args=()):
        return [dict(row) for row in self.connection.execute(query, args)]

    def revision(self):
        return self.connection.execute('SELECT revision FROM metadata').fetchone()[0]

    def exists(self, table, ident):
        if type(ident) is not int or not self.connection.execute(f'SELECT 1 FROM {table} WHERE id=?', (ident,)).fetchone():
            raise ValueError(f'Choose an existing {table.replace("story_", "").rstrip("s")}.')

    def events(self):
        return self.rows('SELECT * FROM story_events ORDER BY sequence,id')

    def profile(self, character_id, event_id):
        self.exists('characters', character_id)
        self.exists('story_events', event_id)
        base = json.loads(self.connection.execute('SELECT baseline FROM characters WHERE id=?', (character_id,)).fetchone()[0])
        history = self.rows('SELECT * FROM profile_history WHERE character_id=?', (character_id,))
        resolved = resolve_profile(base, history, self.events(), event_id)
        raw = dict(resolved['values'])
        for key in WORLD_FIELDS:
            value = raw[key]
            if value.startswith('@world:'):
                ident = int(value.split(':')[1])
                entry = self.connection.execute('SELECT name FROM world_entries WHERE id=? AND category=?', (ident, key)).fetchone()
                if not entry:
                    raise ValueError('A World assignment is missing. Restore a complete backup.')
                resolved['values'][key] = entry[0]
        return dict(character_id=character_id, event_id=event_id, raw_values=raw, **resolved)

    def workspace(self, event_id=None):
        if self.connection.in_transaction:
            return self._workspace(event_id)
        with self.connection:
            self.connection.execute('BEGIN')
            return self._workspace(event_id)

    def _workspace(self, event_id=None):
        events = self.events()
        context = self.preference('context') or {}
        event_id = event_id or context.get('event_id') or events[0]['id']
        self.exists('story_events', event_id)
        cast = [dict(id=row['id'], portrait=self.preference(f"portrait:{row['id']}") or '', **self.profile(row['id'], event_id)['values'])
                for row in self.rows('SELECT id FROM characters ORDER BY id')]
        return dict(**dict(self.connection.execute('SELECT * FROM metadata').fetchone()), path=str(self.path),
                    chapters=self.rows('SELECT * FROM chapters ORDER BY sequence'), events=events,
                    participants=self.rows('SELECT * FROM event_participants'), characters=cast, event_id=event_id,
                    context=context, drafts=self.rows('SELECT key,payload FROM drafts'),
                    theme=self.preference('theme') or 'storybook',
                    connections=self.connections(event_id), world=self.rows('SELECT * FROM world_entries ORDER BY category,name,id'),
                    graph=self.preference('graph') or {},
                    capabilities={'relationships': True, 'world': True})

    def preference(self, key):
        row = self.connection.execute('SELECT payload FROM preferences WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_preference(self, key, payload):
        if key not in ('context', 'theme', 'graph') or not isinstance(payload, (dict, str)):
            raise ValueError('Invalid view preference.')
        with self.connection:
            self.connection.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload', (key, encoded(payload)))

    def save_draft(self, key, payload):
        if not isinstance(key, str) or len(key) > 150 or not isinstance(payload, dict) or payload.get('version') != 1:
            raise ValueError('Unsupported draft format.')
        if len(encoded(payload)) > 5000000:
            raise ValueError('Draft is too large.')
        with self.connection:
            self.connection.execute('INSERT INTO drafts VALUES(?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload', (key, encoded(payload)))
        return {'durable': True}

    def discard_draft(self, key):
        with self.connection:
            self.connection.execute('DELETE FROM drafts WHERE key=?', (key,))

    def get_draft(self, key):
        row = self.connection.execute('SELECT payload FROM drafts WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def write(self, command, payload, expected_revision, request_id, draft_key=None, draft_id=None):
        if not isinstance(request_id, str) or not 8 <= len(request_id) <= 120:
            raise ValueError('A unique request ID is required.')
        fingerprint = hashlib.sha256(encoded([command, payload, expected_revision, draft_key, draft_id]).encode()).hexdigest()
        with self.connection:
            self.connection.execute('BEGIN IMMEDIATE')
            receipt = self.connection.execute('SELECT * FROM receipts WHERE request_id=?', (request_id,)).fetchone()
            if receipt:
                if receipt['fingerprint'] != fingerprint:
                    raise ValueError('This request ID was already used for different content.')
                return json.loads(receipt['result'])
            if type(expected_revision) is not int or expected_revision != self.revision():
                raise Conflict('The story changed since this editor opened. Your draft is kept. Reload saved values, then review your pending edits before retrying.')
            handlers = {'create_character': self._create_character, 'save_profile': self._save_profile,
                        'save_event': self._save_event, 'save_chapter': self._save_chapter, 'save_title': self._save_title,
                        'save_connection': self._save_connection, 'save_world': self._save_world,
                        'save_portrait': self._save_portrait}
            if command not in handlers:
                raise ValueError('This preview command is unavailable.')
            data = handlers[command](payload)
            self.connection.execute('UPDATE metadata SET revision=revision+1')
            audit = {'character_id': payload['character_id'], 'has_portrait': bool(payload['image'])} if command == 'save_portrait' else payload
            self.connection.execute('INSERT INTO activity(action,details) VALUES(?,?)', (command, encoded(audit)))
            if draft_key:
                # Only the matching editor can clear its own draft.
                expected_key = self.draft_key(command, payload)
                if draft_key != expected_key:
                    raise ValueError('The draft does not belong to this save.')
                current = self.get_draft(draft_key)
                if current and current.get('editor', {}).get('draft_id') != draft_id:
                    raise Conflict('Another editor replaced this draft. Pending work is kept. Reopen and review the recovered draft before saving.')
                self.connection.execute('DELETE FROM drafts WHERE key=?', (draft_key,))
            result = {'revision': self.revision(), 'data': data}
            self.connection.execute('INSERT INTO receipts VALUES(?,?,?)', (request_id, fingerprint, encoded(result)))
        return result

    @staticmethod
    def draft_key(command, payload):
        if command == 'save_profile':
            return f"profile:{payload['character_id']}:{payload['event_id']}"
        if command == 'save_connection':
            return f"connection:{payload.get('id', 'new')}:{payload['event_id']}"
        return f"{command}:{payload.get('id', 'new')}"

    def _save_portrait(self, p):
        self.exists('characters', p.get('character_id'))
        image = p.get('image')
        if not isinstance(image, str) or len(image) > 2800000:
            raise ValueError('Choose a portrait image under 2 MB after resizing.')
        if image:
            prefix = 'data:image/jpeg;base64,'
            if not image.startswith(prefix):
                raise ValueError('Portraits must be converted to JPEG before saving.')
            try:
                raw = base64.b64decode(image[len(prefix):], validate=True)
            except (ValueError, binascii.Error):
                raise ValueError('Invalid portrait image.') from None
            if len(raw) > 2000000 or not raw.startswith(b'\xff\xd8\xff') or not raw.endswith(b'\xff\xd9'):
                raise ValueError('Invalid or oversized portrait image.')
        key = f"portrait:{p['character_id']}"
        self.connection.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload', (key, encoded(image)))
        return {'character_id': p['character_id']}

    def _create_character(self, p):
        name = text(p.get('name'), 'a character name', True)
        summary = text(p.get('summary', ''), 'a summary')
        self.exists('story_events', p.get('event_id'))
        baseline = {key: '' for key in FIELDS}
        baseline.update(name=name.strip(), summary=summary)
        ident = self.connection.execute('INSERT INTO characters(baseline) VALUES(?)', (encoded(baseline),)).lastrowid
        return self.profile(ident, p['event_id'])

    def _save_profile(self, p):
        self.exists('characters', p.get('character_id'))
        self.exists('story_events', p.get('event_id'))
        changes = p.get('changes')
        if not isinstance(changes, list) or not changes:
            raise ValueError('Choose at least one profile change.')
        seen = set()
        for row in changes:
            if not isinstance(row, dict) or set(row) != {'field', 'value', 'scope'}:
                raise ValueError('A profile change needs a field, value, and scope.')
            key = row['field']
            if not isinstance(key, str) or key not in FIELDS or key in seen or row['scope'] not in SCOPES:
                raise ValueError('Choose each supported field once and a valid scope.')
            text(row['value'], key, key == 'name')
            value = self._world_value(key, row['value']) if key in WORLD_FIELDS else row['value']
            seen.add(key)
            self.connection.execute('''INSERT INTO profile_history VALUES(?,?,?,?,?)
                ON CONFLICT(character_id,event_id,field) DO UPDATE SET value=excluded.value,scope=excluded.scope''',
                (p['character_id'], p['event_id'], key, value, row['scope']))
        return self.profile(p['character_id'], p['event_id'])

    def _save_title(self, p):
        title = text(p.get('title'), 'a story title', True)
        self.connection.execute('UPDATE metadata SET title=?', (title,))
        return {'title': title}

    def _save_chapter(self, p):
        title = text(p.get('title'), 'a chapter title', True)
        summary = text(p.get('summary', ''), 'a chapter summary')
        ident = p.get('id')
        if ident is None:
            ident = self.connection.execute('INSERT INTO chapters(title,summary,sequence) VALUES(?,?,(SELECT COALESCE(MAX(sequence),0)+1 FROM chapters))', (title, summary)).lastrowid
        else:
            self.exists('chapters', ident)
            self.connection.execute('UPDATE chapters SET title=?,summary=? WHERE id=?', (title, summary, ident))
        return {'id': ident}

    def _save_event(self, p):
        self.exists('chapters', p.get('chapter_id'))
        title = text(p.get('title'), 'an event title', True)
        for field in ('summary', 'purpose', 'notes'):
            text(p.get(field, ''), field)
        status = p.get('status', '')
        location = p.get('location_id')
        if location is not None:
            self.exists('world_entries', location)
            if self.connection.execute('SELECT category FROM world_entries WHERE id=?', (location,)).fetchone()[0] != 'location':
                raise ValueError('Choose a World location.')
        if status not in ('', 'Planned', 'Happened'):
            raise ValueError('Choose Planned, Happened, or Unclassified.')
        participants = p.get('participants', [])
        if not isinstance(participants, list):
            raise ValueError('Choose participating characters.')
        for ident in participants:
            self.exists('characters', ident)
        ident = p.get('id')
        values = (title, p.get('summary', ''), status, p.get('purpose', ''), p.get('notes', ''))
        if ident is None:
            sequence = self.connection.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM story_events').fetchone()[0]
            ident = self.connection.execute('INSERT INTO story_events(title,summary,status,purpose,notes,chapter_id,sequence) VALUES(?,?,?,?,?,?,?)', (*values, p['chapter_id'], sequence)).lastrowid
            # Append within the chosen chapter. Stable event IDs preserve history.
            ordered = self.rows('SELECT e.id FROM story_events e JOIN chapters c ON e.chapter_id=c.id ORDER BY c.sequence,e.sequence')
            for i, row in enumerate(ordered, sequence + 1):
                self.connection.execute('UPDATE story_events SET sequence=? WHERE id=?', (i, row['id']))
            for i, row in enumerate(ordered, 1):
                self.connection.execute('UPDATE story_events SET sequence=? WHERE id=?', (i, row['id']))
        else:
            self.exists('story_events', ident)
            current = self.connection.execute('SELECT chapter_id FROM story_events WHERE id=?', (ident,)).fetchone()[0]
            if current != p['chapter_id']:
                raise ValueError('Moving events is not available in this preview.')
            self.connection.execute('UPDATE story_events SET title=?,summary=?,status=?,purpose=?,notes=? WHERE id=?', (*values, ident))
        self.connection.execute('DELETE FROM event_participants WHERE event_id=?', (ident,))
        self.connection.execute('UPDATE story_events SET location_id=? WHERE id=?', (location, ident))
        self.connection.executemany('INSERT INTO event_participants VALUES(?,?)', [(ident, c) for c in set(participants)])
        return {'id': ident}

    def _world_value(self, category, value):
        if not value:
            return ''
        if value.startswith('@world:'):
            try:
                ident = int(value.split(':')[1])
            except ValueError:
                raise ValueError('Choose a valid World entry.')
            self.exists('world_entries', ident)
            if self.connection.execute('SELECT category FROM world_entries WHERE id=?', (ident,)).fetchone()[0] != category:
                raise ValueError('Choose a World entry from the matching list.')
            return f'@world:{ident}'
        # Deliberate text conversion for the initial service/sample: exact spelling
        # only. Case/space/Unicode normalization collisions remain separate entries.
        self.connection.execute('INSERT OR IGNORE INTO world_entries(category,name) VALUES(?,?)', (category, value))
        ident = self.connection.execute('SELECT id FROM world_entries WHERE category=? AND name=?', (category, value)).fetchone()[0]
        return f'@world:{ident}'

    def _save_world(self, p):
        category = p.get('category')
        if category not in WORLD_FIELDS:
            raise ValueError('Choose a supported World list.')
        name = text(p.get('name'), 'a World entry name', True)
        description = text(p.get('description', ''), 'a description')
        ident = p.get('id')
        if ident is None:
            if self.connection.execute('SELECT 1 FROM world_entries WHERE category=? AND name=?', (category, name)).fetchone():
                raise ValueError('That exact entry already exists. Open it to edit the description.')
            ident = self.connection.execute('INSERT INTO world_entries(category,name,description) VALUES(?,?,?)', (category, name, description)).lastrowid
        else:
            self.exists('world_entries', ident)
            if self.connection.execute('SELECT category FROM world_entries WHERE id=?', (ident,)).fetchone()[0] != category:
                raise ValueError('An entry cannot move between World lists.')
            if self.connection.execute('SELECT 1 FROM world_entries WHERE category=? AND name=? AND id!=?', (category, name, ident)).fetchone():
                raise ValueError('That exact name already belongs to another entry. Entries are not merged.')
            self.connection.execute('UPDATE world_entries SET name=?,description=? WHERE id=?', (name, description, ident))
        return {'id': ident}

    def connections(self, event_id):
        self.exists('story_events', event_id)
        order = {row['id']: row['sequence'] for row in self.events()}
        result = []
        for record in self.rows('SELECT * FROM connections ORDER BY id'):
            state = json.loads(record['baseline']) if record['baseline'] else None
            source = None
            history = self.rows('SELECT * FROM connection_history WHERE connection_id=?', (record['id'],))
            for row in sorted(history, key=lambda r: order[r['event_id']]):
                if order[row['event_id']] <= order[event_id] and (row['scope'] == 'carry_forward' or row['event_id'] == event_id):
                    state = json.loads(row['state'])
                    source = {'event_id': row['event_id'], 'scope': row['scope']}
            if state is not None:
                result.append(dict(state, id=record['id'], origin=source))
        return result

    def _save_connection(self, p):
        self.exists('story_events', p.get('event_id'))
        for key in ('source_id', 'target_id'):
            self.exists('characters', p.get(key))
        scope = p.get('scope')
        if scope not in SCOPES:
            raise ValueError('Choose event-only or carry-forward.')
        for key in ('kind', 'notes', 'inverse_label'):
            text(p.get(key, ''), key, key == 'kind')
        state = normalize(p['source_id'], p['target_id'], p['kind'], p.get('notes', ''),
                          p.get('semantics', 'mutual'), p.get('inverse_label', ''), p.get('category', ''))
        ident = p.get('id')
        if ident is None:
            if self.connection.execute('SELECT 1 FROM connections WHERE (source_id=? AND target_id=?) OR (source_id=? AND target_id=?)',
                (state['source_id'], state['target_id'], state['target_id'], state['source_id'])).fetchone():
                raise ValueError('This pair already has a connection record. Edit it at an event where it is active. Additional new connections for the same pair are unavailable.')
            ident = self.connection.execute('INSERT INTO connections(source_id,target_id,baseline) VALUES(?,?,?)', (state['source_id'], state['target_id'], 'null')).lastrowid
        else:
            self.exists('connections', ident)
            original = self.connection.execute('SELECT source_id,target_id FROM connections WHERE id=?', (ident,)).fetchone()
            if set(original) != {state['source_id'], state['target_id']}:
                raise ValueError('Choose the original two characters for this connection.')
        self.connection.execute('''INSERT INTO connection_history VALUES(?,?,?,?)
            ON CONFLICT(connection_id,event_id) DO UPDATE SET state=excluded.state,scope=excluded.scope''',
            (ident, p['event_id'], encoded(state), scope))
        for event in self.events():
            rows = self.connections(event['id'])
            candidate = next((r for r in rows if r['id'] == ident), None)
            if candidate:
                check_duplicate(candidate, rows, exclude=(ident,))
        return next(row for row in self.connections(p['event_id']) if row['id'] == ident)

    def backup(self, destination):
        destination = Path(destination).resolve()
        with destination.open('xb'):
            pass
        try:
            target = sqlite3.connect(destination)
            try:
                self.connection.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Backup verification failed.')
            finally:
                target.close()
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return {'path': str(destination)}
