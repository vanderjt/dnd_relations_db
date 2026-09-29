"""Modal story-event editor with read-only participant inspection."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .widgets import text_area, wrapping_label, ActionBar, field_error
from .scroll_frame import ScrollFrame
from .chapter_dialog import ChapterPicker
from .participant_picker import ParticipantPicker
from .theme import style_tree

class EventDialog(tk.Toplevel):
    def __init__(self, parent, database, changed, row=None, chapter_id=None, moved=None):
        super().__init__(parent)
        self.database, self.changed, self.ident = database, changed, row["id"] if row else None
        self.moved = moved
        self.original_chapter_id = row['chapter_id'] if row else None
        self.title("Correct story event" if row else "New story event")
        self.geometry("650x650")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        footer = ActionBar(self)
        footer.pack(side="bottom", fill="x", padx=16, pady=8)
        footer.add(ttk.Button(footer, text="Save and close", command=self.save, style="Primary.TButton"))
        footer.add(ttk.Button(footer, text="Cancel", style="Secondary.TButton", command=self.close))
        scroller = ScrollFrame(self)
        scroller.pack(fill="both", expand=True, padx=16)
        body = scroller.content
        self.title_value = tk.StringVar(self, row["title"] if row else "")
        self.chapter = ChapterPicker(body, database, row['chapter_id'] if row else chapter_id, self.chapter_changed)
        self.chapter.pack(fill='x', pady=8)
        self.sequence = tk.StringVar(self)
        self.chapter_changed()
        self.entries, self.errors = {}, {}
        for key, label, variable in (("title", "Event title (for example: The pact)", self.title_value), ("position", "Position within chapter (1 = first)", self.sequence)):
            ttk.Label(body, text=label).pack(anchor="w", pady=(10, 4))
            self.entries[key] = ttk.Entry(body, textvariable=variable)
            self.entries[key].pack(fill="x")
            self.errors[key] = tk.StringVar(self)
            field_error(body, self.errors[key], self.entries[key])
        wrapping_label(body, text='Position is within this chapter. Moving an existing event changes relationship chronology.', style='Muted.TLabel').pack(fill='x', pady=6)
        self.summary_toggle = ttk.Button(body, text='Summary · optional ▸', command=self.toggle_summary)
        self.summary_toggle.pack(anchor='w', pady=4)
        self.summary_frame = ttk.Frame(body)
        self.summary_open = False
        self.summary = text_area(self.summary_frame, height=3)
        self.summary.pack(fill="x")
        self.summary.insert("1.0", row["summary"] if row else "")
        if row and row['summary']:
            self.toggle_summary()
        self.summary.bind('<Control-Return>', self.save_shortcut)
        selected = [item['character_id'] for item in database.events.participants() if item['event_id'] == self.ident]
        self.participants = ParticipantPicker(body, database, selected)
        self.participants.pack(fill='x', pady=8)
        self.error = tk.StringVar(self)
        wrapping_label(footer, textvariable=self.error, style='Validation.TLabel').grid(row=2, column=0, sticky='w')
        self.original = self.values()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _: self.close())
        self.bind("<Control-Return>", lambda _: self.save())
        style_tree(self)

    def values(self):
        return self.title_value.get(), self.summary.get("1.0", "end-1c"), self.sequence.get(), tuple(sorted(self.participants.selected)), self.chapter.get()

    def save_shortcut(self, _event=None):
        self.save()
        return 'break'

    def toggle_summary(self):
        if self.summary_open:
            self.summary_frame.pack_forget()
        else:
            self.summary_frame.pack(fill='x', after=self.summary_toggle)
        self.summary_open = not self.summary_open
        self.summary_toggle.configure(text='Summary · optional ▾' if self.summary_open else 'Summary · optional ▸')

    def chapter_changed(self):
        siblings = [row for row in self.database.events.list() if row['chapter_id'] == self.chapter.get()]
        position = next((i for i, row in enumerate(siblings, 1) if row['id'] == self.ident), len(siblings) + 1)
        self.sequence.set(str(position))

    def save(self):
        for error in self.errors.values():
            error.set('')
        invalid = None
        if not self.title_value.get().strip():
            self.errors['title'].set('Enter an event title.')
            invalid = 'title'
        try:
            if int(self.sequence.get()) < 1:
                raise ValueError()
        except ValueError:
            self.errors['position'].set('Enter a whole number of 1 or greater.')
            invalid = invalid or 'position'
        if invalid:
            self.entries[invalid].focus_set()
            return False
        try:
            title, summary, sequence, cast, chapter = self.values()
            saved_id = self.database.chapters.save_event(title, summary, int(sequence), [int(value) for value in cast], self.ident, chapter)
        except (ValueError, sqlite3.Error) as error:
            self.error.set(f'Not saved: {error}')
            return False
        self.changed("Story event saved")
        if self.ident is None and hasattr(self.master, 'reveal_event'):
            self.master.reveal_event(saved_id)
        if self.moved and self.ident is not None and chapter != self.original_chapter_id:
            self.moved(saved_id, chapter)
        self.destroy()
        return True

    def close(self):
        if self.values() != self.original:
            answer = messagebox.askyesnocancel("Unfinished event", "Save this event before closing?", parent=self)
            if answer is None or (answer and not self.save()):
                return
            if answer:
                return
        self.destroy()
