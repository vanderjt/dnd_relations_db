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
        self.heading = ttk.Label(self, text="Cast", style="Content.Heading.TLabel")
        self.heading.pack(anchor='w')
        self.hint = wrapping_label(self, text="Search cast by name or choose All relationships.",
                       style="Content.Muted.TLabel")
        self.hint.pack(fill="x", pady=(0, 6))
        self.filter_label = ttk.Label(self, text="Filter cast", style="Content.Muted.TLabel")
        self.filter_label.pack(anchor="w")
        self.search_entry = ttk.Entry(self, textvariable=self.query)
        self.search_entry.pack(fill='x', pady=4)
        self.tree = table(self, {'name': 'Character / ID'})
        from .tree_art import install_tree_art
        self.refresh_art = install_tree_art(self.tree, lambda: {str(row['id']): row for row in self.rows}, lambda: self._root().database)
        self.query.trace_add('write', lambda *_: self.populate())
        self.tree.bind('<<TreeviewSelect>>', self.choose)
        self.bind('<Configure>', self.compact_layout, add='+')

    def compact_layout(self, event=None):
        if event is not None and event.widget is not self:
            return
        compact = self._root().winfo_height() < 620
        if compact == getattr(self, '_compact', None):
            return
        self._compact = compact
        self.heading.pack_forget()
        self.hint.pack_forget()
        self.filter_label.pack_forget()
        self.tree.master.pack_configure(pady=2 if compact else 10)
        if not compact:
            self.filter_label.pack(anchor='w', before=self.search_entry)
            self.heading.pack(anchor='w', before=self.filter_label)
            self.hint.pack(fill='x', before=self.filter_label, pady=(0, 6))

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
        self.refresh_art()

    def choose(self, _event=None):
        selection = self.tree.selection()
        if selection:
            ident = None if selection[0] == 'all' else int(selection[0])
            if ident != self.character_id:
                self.character_id = ident
                self.selected(ident)
