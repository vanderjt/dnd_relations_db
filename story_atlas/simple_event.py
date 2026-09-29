"""Event/chapter task pane. Committed events are distinct from later edits."""
import sqlite3
import tkinter as tk
from tkinter import ttk
from .widgets import ActionBar, wrapping_label, text_area
from .scroll_frame import ScrollFrame
from .participant_picker import ParticipantPicker


class EventPane(ttk.Frame):
    def __init__(self, parent, workspace, new_chapter=False, row=None, recovered=None):
        super().__init__(parent)
        self.workspace, self.database = workspace, workspace.database
        self.new_chapter, self.row = new_chapter, row
        self.nested = None
        bar = ActionBar(self)
        bar.pack(side='bottom', fill='x')
        self.save_button = bar.add(ttk.Button(bar, text='Save event', width=0, command=self.save))
        bar.add(ttk.Button(bar, text='Close', width=0, command=workspace.close_task))
        self.error = tk.StringVar(self)
        wrapping_label(self, textvariable=self.error, style='Context.TLabel').pack(side='bottom', fill='x')
        self.scroller = scroller = ScrollFrame(self)
        scroller.pack(fill='both', expand=True)
        body = scroller.content
        self.chapter = tk.StringVar(self)
        self.title = tk.StringVar(self, row['title'] if row else 'Opening scene' if new_chapter else f'Scene {len(self.database.events.list()) + 1}')
        if new_chapter:
            ttk.Label(body, text='New chapter title').pack(anchor='w')
            ttk.Entry(body, textvariable=self.chapter).pack(fill='x')
        else:
            self.chapters = {'Unassigned': None, **{f"{item['title']} (#{item['id']})": item['id'] for item in self.database.chapters.list()}}
            context = row or next((item for item in self.database.events.list() if item['id'] == workspace.graph.as_of_id), self.database.events.list()[-1] if self.database.events.list() else {})
            self.chapter.set(next((label for label, ident in self.chapters.items() if ident == context.get('chapter_id')), 'Unassigned'))
            ttk.Label(body, text='Chapter').pack(anchor='w')
            ttk.Combobox(body, textvariable=self.chapter, values=tuple(self.chapters), state='readonly').pack(fill='x')
        ttk.Label(body, text='Event title').pack(anchor='w')
        ttk.Entry(body, textvariable=self.title).pack(fill='x')
        ttk.Label(body, text='Summary').pack(anchor='w')
        self.summary = text_area(body, height=4)
        self.summary.pack(fill='x')
        self.summary.insert('1.0', row['summary'] if row else '')
        selected = [item['character_id'] for item in self.database.events.participants() if row and item['event_id'] == row['id']]
        self.participants = ParticipantPicker(body, self.database, selected)
        self.participants.pack(fill='x')
        self.create_character_button = ttk.Button(body, text='Create character…', command=self.create_character)
        self.create_character_button.pack(anchor='w')
        wrapping_label(body, text='The existing story situation carries forward. Saving commits this event; canceling a later character or relationship task does not undo it.').pack(fill='x')
        self.original = self.values()
        from .task_draft import TaskDraft
        self.draft = TaskDraft(self, f'task:event:{row["id"] if row else "chapter" if new_chapter else "new"}')
        if recovered:
            self.restore_draft(recovered)
        self.update_save()

    def create_character(self):
        from .quick_character import QuickCharacterDialog
        if self.nested:
            return self.nested
        def created(ident):
            selected = self.participants.selected | {ident}
            self.participants.destroy()
            self.participants = ParticipantPicker(self.scroller.content, self.database, selected)
            self.participants.pack(fill='x', before=self.create_character_button)
            self.workspace.app.refresh('Character saved')
        def closed():
            self.nested = None
            self.scroller.pack(fill='both', expand=True)
        self.nested = QuickCharacterDialog(self, self.database, created, closed, guarded=True)
        self.nested.name.set(self.participants.query.get())
        self.scroller.pack_forget()
        self.nested.pack(fill='both', expand=True)
        return self.nested

    def update_save(self):
        self.save_button.state(['!disabled' if self.row is None or self.values() != self.original else 'disabled'])

    def draft_payload(self):
        return dict(task='event', event_id=self.row['id'] if self.row else None, new_chapter=self.new_chapter,
                    chapter_id=None if self.new_chapter else self.chapters.get(self.chapter.get()), values=self.values())

    def restore_draft(self, payload):
        chapter, title, summary, participants = payload['values'][:4]
        if self.new_chapter:
            self.chapter.set(chapter)
        else:
            ident = payload.get('chapter_id')
            self.chapter.set(next((label for label, value in self.chapters.items() if value == ident), f'Missing chapter #{ident} · choose replacement'))
        self.title.set(title)
        self.summary.delete('1.0', 'end')
        self.summary.insert('1.0', summary)
        available = set(self.participants.rows)
        self.missing_participants = set(participants) - available
        self.participants.selected = set(participants) & available
        for ident, var in self.participants.variables.items():
            var.set(ident in self.participants.selected)
        self.participants.update_summary()
        if len(payload['values']) > 4 and payload['values'][4]:
            self.create_character().name.set(payload['values'][4])
        if self.missing_participants:
            self.error.set('Missing participants: ' + ', '.join(map(str, self.missing_participants)) + '. Restore them or explicitly exclude them.')
            ttk.Button(self, text='Exclude missing participants', command=self.exclude_missing).pack(side='bottom')
        else:
            self.error.set('Recovered event draft · review before saving')

    def exclude_missing(self):
        self.missing_participants.clear()
        self.error.set('Missing participants excluded from this draft')

    def destroy(self):
        if hasattr(self, 'draft'):
            self.draft.close()
        super().destroy()

    def values(self):
        return (self.chapter.get(), self.title.get(), self.summary.get('1.0', 'end-1c'), tuple(sorted(self.participants.selected | getattr(self, 'missing_participants', set()))), self.nested.name.get() if self.nested else '')

    def save(self):
        if self.row is not None and self.values() == self.original:
            return True
        try:
            chapter, title, summary, participants = self.values()[:4]
            if self.nested:
                raise ValueError('Complete character creation or choose Back before saving the event.')
            if getattr(self, 'missing_participants', set()):
                raise ValueError('Restore or explicitly exclude missing participants.')
            if not self.new_chapter and chapter not in self.chapters:
                raise ValueError('Choose an existing chapter or Unassigned.')
            if not title.strip() or self.new_chapter and not chapter.strip():
                raise ValueError('Enter the event title and chapter title.')
            if self.new_chapter:
                # Both records and their log share one transaction; service helper
                # deliberately avoids nested connection contexts.
                ident = create_chapter_event(self.database, chapter, title, summary, participants, self.draft.key)
            else:
                chapter_id = self.chapters[chapter]
                siblings = [row for row in self.database.events.list() if row['chapter_id'] == chapter_id]
                position = next((i for i, row in enumerate(siblings, 1) if self.row and row['id'] == self.row['id']), len(siblings) + 1)
                ident = self.database.chapters.save_event(title, summary, position, participants, self.row['id'] if self.row else None, chapter_id, draft_key=self.draft.key)
        except (ValueError, sqlite3.Error) as error:
            self.error.set(f'Not saved: {error}')
            return False
        self.draft.discard()
        self.original = self.values()
        self.row = next(row for row in self.database.events.list() if row['id'] == ident)
        self.workspace.event_saved(ident)
        return True


def create_chapter_event(database, chapter, title, summary='', participants=(), draft_key=None):
    if not chapter.strip():
        raise ValueError('Enter a chapter title.')
    with database.connection:
        order = max((row['sequence'] for row in database.chapters.list()), default=0) + 1
        chapter_id = database.connection.execute('INSERT INTO chapters(title,sequence) VALUES (?,?)', (chapter.strip(), order)).lastrowid
        sequence = max((row['sequence'] for row in database.events.list()), default=0) + 1
        ident = database.events.write(title, summary, sequence, participants)
        database.connection.execute('UPDATE story_events SET chapter_id=? WHERE id=?', (chapter_id, ident))
        database.chapters.resequence(database.chapters.ordered_events())
        if draft_key:
            database.connection.execute('DELETE FROM drafts WHERE key=?', (draft_key,))
        database._log('Chapter and first event created', f'{chapter}: {title}')
    return ident
