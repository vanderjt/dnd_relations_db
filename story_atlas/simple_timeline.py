"""Read-only timeline navigation; marker dragging never changes chronology."""
import tkinter as tk
from tkinter import ttk
from .widgets import ActionBar
from .chapters import event_scope
from .theme import palette


class Timeline(ttk.Frame):
    def __init__(self, parent, workspace):
        super().__init__(parent)
        self.workspace = workspace
        self.pending = None
        self.ids = [0, None]
        self.bar = ActionBar(self)
        self.bar.pack(fill='x')
        self.bar.add(ttk.Button(self.bar, text='‹', width=2, command=lambda: self.step(-1)))
        self.bar.add(ttk.Button(self.bar, text='›', width=2, command=lambda: self.step(1)))
        self.chapter = tk.StringVar(self)
        self.chapter_box = self.bar.add(ttk.Combobox(self.bar, textvariable=self.chapter, state='readonly', width=14))
        self.chapter_box.bind('<<ComboboxSelected>>', self.choose_chapter)
        self.event = tk.StringVar(self)
        self.event_box = self.bar.add(ttk.Combobox(self.bar, textvariable=self.event, state='readonly', width=24))
        self.event_box.bind('<<ComboboxSelected>>', lambda _: workspace.navigate(self.choices[self.event.get()]))
        self.canvas = tk.Canvas(self, height=64, highlightthickness=0, takefocus=True)
        self.canvas.pack(fill='x')
        self.canvas.bind('<Configure>', lambda _: self.draw())
        self.canvas.bind('<Button-1>', self.scrub)
        self.canvas.bind('<B1-Motion>', self.scrub)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        self.canvas.bind('<Left>', lambda _: self.step(-1))
        self.canvas.bind('<Right>', lambda _: self.step(1))
        self.preview_index = None

    def compact_layout(self, compact):
        if not hasattr(self, 'full_items'):
            self.full_items = self.bar.items.copy()
        for item in self.full_items:
            item.grid_forget()
        self.bar.items = [self.full_items[0], self.full_items[1], self.event_box] if compact else self.full_items
        self.event_box.configure(width=20 if compact else 24)
        self.bar.reflow()
        self.canvas.configure(height=40 if compact else 64)

    def refresh(self):
        db = self.workspace.database
        self.rows = db.events.list()
        self.ids = [0, *[row['id'] for row in self.rows], None]
        self.choices = {'Before first event': 0, **{event_scope(db, row): row['id'] for row in self.rows}, 'Current': None}
        self.chapters = {f"{row['title']} (#{row['id']})": row['id'] for row in db.chapters.list()}
        self.chapter_box.configure(values=tuple(self.chapters))
        self.event_box.configure(values=tuple(self.choices))
        current = self.workspace.graph.as_of_id
        self.event.set(next(label for label, ident in self.choices.items() if ident == current))
        row = next((row for row in self.rows if row['id'] == current), {})
        self.chapter.set(next((label for label, ident in self.chapters.items() if ident == row.get('chapter_id')), 'All chapters'))
        self.draw()

    def choose_chapter(self, _event=None):
        ident = self.chapters.get(self.chapter.get())
        event = next((row['id'] for row in self.rows if row['chapter_id'] == ident), None)
        self.workspace.navigate(event)

    def step(self, offset):
        index = self.ids.index(self.workspace.graph.as_of_id)
        self.workspace.navigate(self.ids[max(0, min(len(self.ids) - 1, index + offset))])

    def draw(self):
        if not hasattr(self, 'rows'):
            return
        colors = palette(self)
        self.canvas.configure(bg=colors['panel'])
        self.canvas.delete('all')
        height = max(24, self.canvas.winfo_height())
        compact = height < 60
        width = max(100, self.canvas.winfo_width()) - 32
        spacing = width / max(1, len(self.ids) - 1)
        chapter_names = {row['id']: row['title'] for row in self.workspace.database.chapters.list()}
        groups = []
        for i, row in enumerate(self.rows, 1):
            chapter = row['chapter_id']
            if not groups or groups[-1][0] != chapter:
                groups.append([chapter, i, i])
            else:
                groups[-1][2] = i
        for chapter, start, end in ([] if compact else groups):
            x0, x1 = 16 + (start - .4) * spacing, 16 + (end + .4) * spacing
            self.canvas.create_rectangle(x0, 3, x1, 27, outline=colors['border'])
            self.canvas.create_text((x0 + x1) / 2, 15, text=chapter_names.get(chapter, 'Unassigned')[:30], fill=colors['text'], width=max(20, x1-x0))
        index = self.preview_index if self.preview_index is not None else self.ids.index(self.workspace.graph.as_of_id)
        for i in range(len(self.ids)):
            x = 16 + i * spacing
            dot_y = 10 if compact else 40
            self.canvas.create_oval(x-3, dot_y-3, x+3, dot_y+3, fill=colors['muted'], outline='')
        x = 16 + index * spacing
        self.canvas.create_line(x, 3 if compact else 28, x, height-3, fill=colors['focus'], width=3)
        self.canvas.create_text(16, height-3, text='Before', anchor='sw', fill=colors['muted'])
        self.canvas.create_text(width + 16, height-3, text='Current', anchor='se', fill=colors['muted'])

    def scrub(self, event):
        width = max(100, self.canvas.winfo_width()) - 32
        self.preview_index = max(0, min(len(self.ids) - 1, round((event.x - 16) / width * (len(self.ids) - 1))))
        ident = self.ids[self.preview_index]
        self.event.set('Preview: ' + next(label for label, value in self.choices.items() if value == ident))
        self.draw()
        if self.pending:
            self.after_cancel(self.pending)
        # Only navigate during dragging when no input could trigger a prompt.
        if self.workspace.task is None:
            self.pending = self.after(120, self.commit_scrub)

    def commit_scrub(self):
        self.pending = None
        if self.preview_index is not None:
            ident = self.ids[self.preview_index]
            self.preview_index = None
            self.workspace.navigate(ident)

    def release(self, _event=None):
        if self.pending:
            self.after_cancel(self.pending)
            self.pending = None
        self.commit_scrub()

    def destroy(self):
        if self.pending:
            self.after_cancel(self.pending)
        super().destroy()
