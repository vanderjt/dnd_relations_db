"""Searchable cast list used by the relationship workspace."""
import tkinter as tk
from tkinter import ttk
from .widgets import table, wrapping_label


class RelationshipRoster(ttk.Frame):
    def __init__(self, parent, selected):
        super().__init__(parent, padding=8, style="Content.TFrame")
        self.selected = selected
        self.query = tk.StringVar(self)
        self.rows = []
        self.character_id = None
        ttk.Label(self, text="Cast", style="Content.Heading.TLabel").pack(anchor='w')
        wrapping_label(self, text="Search cast by name or choose All relationships.",
                       style="Content.Muted.TLabel").pack(fill="x", pady=(0, 6))
        ttk.Label(self, text="Filter cast", style="Content.Muted.TLabel").pack(anchor="w")
        ttk.Entry(self, textvariable=self.query).pack(fill='x', pady=4)
        self.tree = table(self, {'name': 'Character / ID'})
        self.query.trace_add('write', lambda *_: self.populate())
        self.tree.bind('<<TreeviewSelect>>', self.choose)

    def refresh(self, rows, character_id):
        self.rows, self.character_id = rows, character_id
        self.populate()

    def populate(self):
        self.tree.delete(*self.tree.get_children())
        self.tree.insert('', 'end', iid='all', values=('All relationships',))
        query = self.query.get().casefold().strip()
        for row in self.rows:
            if query in row['name'].casefold():
                self.tree.insert('', 'end', iid=str(row['id']), values=(f"{row['name']} (#{row['id']})",))
        key = str(self.character_id) if self.character_id is not None else 'all'
        if self.tree.exists(key):
            self.tree.selection_set(key)

    def choose(self, _event=None):
        selection = self.tree.selection()
        if selection:
            ident = None if selection[0] == 'all' else int(selection[0])
            if ident != self.character_id:
                self.character_id = ident
                self.selected(ident)
