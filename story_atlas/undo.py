"""Bounded, session-local history of committed story transactions."""
import sqlite3

# Dependency order. Drafts, audit entries, immutable portrait bytes, and view
# preferences are deliberately outside a story edit's reversible state.
TABLES = ('chapters', 'story_events', 'characters', 'relationships',
          'event_participants', 'relationship_history', 'story_metadata')


class Connection(sqlite3.Connection):
    recorder = None
    depth = 0

    def __enter__(self):
        self.depth += 1
        return super().__enter__()

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.depth -= 1
            if self.recorder is not None and self.depth == 0 and not self.in_transaction:
                self.recorder.checkpoint()

    def commit(self):
        super().commit()
        if self.recorder is not None and not self.depth:
            self.recorder.checkpoint()


class UndoHistory:
    def __init__(self, database):
        self.db = database
        self.connection = database.connection
        self.columns = {table: tuple(row[1] for row in self.connection.execute(f'PRAGMA table_info({table})')) for table in TABLES}
        self.past, self.future = [], []
        self.busy = False
        self.current = self.capture()
        self.revision = self.connection.execute('PRAGMA data_version').fetchone()[0]
        self.connection.recorder = self

    def capture(self):
        return {table: tuple(tuple(row) for row in self.connection.execute(f'SELECT * FROM {table} ORDER BY rowid')) for table in TABLES}

    def checkpoint(self):
        if self.busy:
            return
        state = self.capture()
        revision = self.connection.execute('PRAGMA data_version').fetchone()[0]
        if revision != self.revision:
            self.past.clear()
            self.future.clear()
        elif state != self.current:
            self.past.append(('story', self.current, state))
            self.future.clear()
            self.trim()
        self.current, self.revision = state, revision

    def trim(self):
        # Keep at most 30 changes and about 32 MiB of text/record snapshots.
        while len(self.past) > 30 or (len(self.past) > 1 and sum(len(repr(x)) for x in self.past) > 32 * 1024 * 1024):
            self.past.pop(0)

    def record_view(self, before, after, restore):
        self.checkpoint()
        if before != after:
            self.past.append(('view', before, after, restore))
            self.future.clear()
            self.trim()

    def apply(self, redo=False):
        if self.connection.in_transaction:
            raise ValueError('Finish the current save before using undo or redo.')
        stack, destination = (self.future, self.past) if redo else (self.past, self.future)
        if not stack:
            return False
        action = stack[-1]
        target = action[2] if redo else action[1]
        self.busy = True
        try:
            with self.connection:
                self.connection.execute('BEGIN IMMEDIATE')
                revision = self.connection.execute('PRAGMA data_version').fetchone()[0]
                if revision != self.revision or self.capture() != self.current:
                    self.past.clear()
                    self.future.clear()
                    self.current, self.revision = self.capture(), revision
                    raise ValueError('This story changed outside the current undo history. History has been reset.')
                if action[0] == 'story':
                    self.connection.execute('PRAGMA defer_foreign_keys=ON')
                    for table in reversed(TABLES):
                        self.connection.execute(f'DELETE FROM {table}')
                    for table in TABLES:
                        columns = ','.join(self.columns[table])
                        marks = ','.join('?' for _ in self.columns[table])
                        self.connection.executemany(f'INSERT INTO {table} ({columns}) VALUES ({marks})', target[table])
                    self.db.history.validate()
                    if self.connection.execute('PRAGMA foreign_key_check').fetchall():
                        raise ValueError('Cannot undo a change with invalid story references.')
                    self.db._log('Redo' if redo else 'Undo', 'Reapplied saved story change' if redo else 'Reverted saved story change')
            if action[0] == 'view':
                action[3](target)
            self.current = self.capture()
            stack.pop()
            destination.append(action)
            return action[0]
        finally:
            self.busy = False
