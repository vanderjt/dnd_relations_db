"""Chapter organization; event IDs stay stable when chronology is reordered."""
import hashlib
import json


class Chapters:
    def __init__(self, database):
        self.db = database

    def list(self):
        return [dict(row) for row in self.db.connection.execute('SELECT * FROM chapters ORDER BY sequence,id')]

    def save(self, title, summary='', ident=None):
        if not isinstance(title, str) or not title.strip() or not isinstance(summary, str):
            raise ValueError('A chapter needs a title and text summary.')
        with self.db.connection:
            if ident is None:
                order = max((row['sequence'] for row in self.list()), default=0) + 1
                ident = self.db.connection.execute('INSERT INTO chapters(title,summary,sequence) VALUES (?,?,?)',
                                                  (title.strip(), summary, order)).lastrowid
            elif not self.db.connection.execute('UPDATE chapters SET title=?,summary=? WHERE id=?',
                                                (title.strip(), summary, ident)).rowcount:
                raise ValueError('This chapter no longer exists.')
            self.db._log('Chapter saved', f'#{ident}: {title}')
        return ident

    def ordered_events(self):
        ranks = {row['id']: i for i, row in enumerate(self.list())}
        return sorted(self.db.events.list(), key=lambda row: (ranks.get(row['chapter_id'], len(ranks)), row['sequence']))

    def resequence(self, rows):
        """Called inside a transaction; validate every relationship boundary."""
        # First move all rows clear of both their current and final unique values.
        ceiling = max((row['sequence'] for row in self.db.events.list()), default=0) + len(rows) + 1
        for i, row in enumerate(rows):
            self.db.connection.execute('UPDATE story_events SET sequence=? WHERE id=?', (ceiling + i, row['id']))
        for i, row in enumerate(rows, 1):
            self.db.connection.execute('UPDATE story_events SET sequence=? WHERE id=?', (i, row['id']))
        self.db.history.validate()

    def preview_move(self, ident, offset):
        """Describe a hypothetical move without changing rows or the activity log."""
        chapters = self.list()
        index = next((i for i, row in enumerate(chapters) if row['id'] == ident), None)
        if index is None or not 0 <= index + offset < len(chapters):
            raise ValueError('This chapter has no neighbor in that direction.')
        events = self.db.events.list()
        history = self.db.history.rows()
        relationships = self.db.relationship_records()
        def order(rows):
            ranks = {row['id']: i for i, row in enumerate(rows)}
            return sorted(events, key=lambda row: (ranks.get(row['chapter_id'], len(ranks)), row['sequence']))
        before, after_chapters = order(chapters), chapters.copy()
        after_chapters[index], after_chapters[index + offset] = after_chapters[index + offset], after_chapters[index]
        after = order(after_chapters)
        stamp = hashlib.sha256(json.dumps([chapters, events, history, relationships], sort_keys=True,
                                           default=str).encode('utf-8')).hexdigest()
        return {'chapter_id': ident, 'offset': offset, 'stamp': stamp,
                'old_chapters': [(row['id'], row['title']) for row in chapters],
                'new_chapters': [(row['id'], row['title']) for row in after_chapters],
                'old_events': [(row['id'], row['title'], row['chapter_id']) for row in before],
                'new_events': [(row['id'], row['title'], row['chapter_id']) for row in after]}

    def move(self, ident, offset, expected=None):
        rows = self.list()
        index = next((i for i, row in enumerate(rows) if row['id'] == ident), None)
        if index is None:
            raise ValueError('Choose a chapter.')
        other = index + offset
        if not 0 <= other < len(rows):
            return
        a, b = rows[index], rows[other]
        with self.db.connection:
            if expected is not None and self.preview_move(ident, offset) != expected:
                raise ValueError('Chronology changed since the preview. Review the new order and confirm again.')
            temporary = max(row['sequence'] for row in rows) + 1
            for order, key in ((temporary, a['id']), (a['sequence'], b['id']), (b['sequence'], a['id'])):
                self.db.connection.execute('UPDATE chapters SET sequence=? WHERE id=?', (order, key))
            self.resequence(self.ordered_events())
            self.db._log('Chapters reordered', f"#{a['id']} and #{b['id']}")

    def save_event(self, title, summary, position, participants=(), ident=None, chapter_id=None, draft_key=None):
        """Place an event within its chapter and commit the whole move atomically."""
        if chapter_id is not None and chapter_id not in {row['id'] for row in self.list()}:
            raise ValueError('Choose an existing chapter.')
        siblings = [row for row in self.db.events.list() if row['chapter_id'] == chapter_id and row['id'] != ident]
        if type(position) is not int or not 1 <= position <= len(siblings) + 1:
            raise ValueError(f'Position must be between 1 and {len(siblings) + 1}.')
        # Events.save normally owns its transaction. A savepoint alone cannot
        # protect against its commit, so use its transaction-free write helper.
        with self.db.connection:
            sequence = max((row['sequence'] for row in self.db.events.list()), default=0) + 1
            ident = self.db.events.write(title, summary, sequence, participants, ident)
            self.db.connection.execute('UPDATE story_events SET chapter_id=? WHERE id=?', (chapter_id, ident))
            rows = [row for row in self.ordered_events() if row['id'] != ident]
            item = next(row for row in self.db.events.list() if row['id'] == ident)
            siblings.insert(position - 1, item)
            groups = [row['id'] for row in self.list()] + [None]
            ordered = []
            for group in groups:
                ordered.extend(siblings if group == chapter_id else [row for row in rows if row['chapter_id'] == group])
            self.resequence(ordered)
            if draft_key:
                self.db.connection.execute('DELETE FROM drafts WHERE key=?', (draft_key,))
            self.db._log('Story event saved', f'Event #{ident}: {title}')
        return ident


def event_label(database, row):
    chapter = next((item for item in database.chapters.list() if item['id'] == row.get('chapter_id')), None)
    prefix = f"{chapter['title']} / " if chapter else ''
    return f"{prefix}{row['title']} (#{row['id']})"


def event_scope(database, row):
    prefix = 'Unassigned / ' if row.get('chapter_id') is None else ''
    return 'After: ' + prefix + event_label(database, row)
