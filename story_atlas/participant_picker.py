"""Searchable native checkboxes; filtering never owns the selected ID set."""
import tkinter as tk
from tkinter import ttk
from .scroll_frame import ScrollFrame
from .widgets import wrapping_label, read_only_text_area, set_read_only_text


class ParticipantPicker(ttk.Frame):
    def __init__(self, parent, database, selected=()):
        super().__init__(parent)
        self.selected = set(selected)
        self.rows = {row['id']: dict(row) for row in database.connection.execute(
            'SELECT id,name,role,faction,goals,deleted_at FROM characters ORDER BY name,id')
            if not row['deleted_at'] or row['id'] in self.selected}
        self.query = tk.StringVar(self)
        self.summary = tk.StringVar(self)
        ttk.Label(self, text='Participants · search, then Tab and Space to check').pack(anchor='w')
        ttk.Entry(self, textvariable=self.query).pack(fill='x')
        wrapping_label(self, textvariable=self.summary, style='Context.TLabel').pack(fill='x', pady=4)
        self.list = ScrollFrame(self)
        self.list.pack(fill='x')
        self.list.canvas.configure(height=145)
        self.preview = read_only_text_area(self, height=4)
        self.preview.pack(fill='x', pady=4)
        set_read_only_text(self.preview, 'Current goals · focus a participant to preview saved goals. Profiles and goals are not historically versioned.')
        self.variables, self.buttons = {}, {}
        for ident, row in self.rows.items():
            variable = tk.BooleanVar(self, ident in self.selected)
            self.variables[ident] = variable
            button = ttk.Checkbutton(self.list.content, text=self.label(row), variable=variable,
                                     command=lambda ident=ident: self.toggle(ident))
            if row['deleted_at']:
                button.state(['disabled'])
            button.bind('<FocusIn>', lambda _, ident=ident: self.inspect(ident))
            button.bind('<Enter>', lambda _, ident=ident: self.inspect(ident))
            self.buttons[ident] = button
        self.empty = wrapping_label(self.list.content, style='Muted.TLabel')
        self.query.trace_add('write', self.filter)
        self.filter()
        self.update_summary()

    @staticmethod
    def label(row):
        context = ' · '.join(value for value in (row['role'], row['faction']) if value)
        return f"{row['name']} (#{row['id']})" + (f' · {context}' if context else '') + (' [Trash · historical participant]' if row['deleted_at'] else '')

    def filter(self, *_):
        query = self.query.get().casefold()
        for ident, button in self.buttons.items():
            button.pack_forget()
            if query in self.label(self.rows[ident]).casefold():
                button.pack(anchor='w', fill='x', pady=2)
        matched = any(query in self.label(row).casefold() for row in self.rows.values())
        self.empty.pack_forget()
        if not matched:
            self.empty.configure(text='No characters yet' if not self.rows else 'No matching characters · change the search or create a character')
            self.empty.pack(fill='x')
        self.list.canvas.yview_moveto(0)

    def toggle(self, ident):
        if self.variables[ident].get():
            self.selected.add(ident)
        else:
            self.selected.discard(ident)
        self.update_summary()
        self.inspect(ident)

    def update_summary(self):
        names = [f"{self.rows[ident]['name']} (#{ident})" for ident in sorted(self.selected)]
        self.summary.set(f"Selected ({len(names)}): " + (', '.join(names) or 'None'))

    def inspect(self, ident):
        row = self.rows[ident]
        set_read_only_text(self.preview, f"Current goals · {self.label(row)}\n{row['goals'] or 'No saved goals.'}")
