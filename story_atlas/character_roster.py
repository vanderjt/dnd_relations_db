"""Search and selection widgets for the character list."""
import tkinter as tk
from tkinter import ttk
from .widgets import table, wrapping_label


class CharacterRoster(ttk.Frame):
    def __init__(self, parent, new_character):
        super().__init__(parent, width=300)
        self.heading = ttk.Label(self, text="Your cast", style="Muted.TLabel")
        self.heading.pack(anchor="w")
        self.empty = wrapping_label(self, style="Muted.TLabel")
        self.empty.pack(fill="x")
        self.search = tk.StringVar(self)
        self.filters = {}
        self.search_entry = ttk.Entry(self, textvariable=self.search)
        self.search_entry.pack(fill="x", pady=(10, 0))
        self.search_caption = wrapping_label(self, text="Search all profile fields", style="Muted.TLabel")
        self.search_caption.pack(fill="x")
        self.filter_button = ttk.Button(self, text="Filters / saved filters…")
        self.filter_button.pack(fill="x", pady=4)
        self.filter_summary = wrapping_label(self, style="Muted.TLabel")
        self.filter_summary.pack(fill="x")
        self.tree = table(self, {"name": "Name", "role": "Role"})
        self.art_rows = {}
        from .tree_art import install_tree_art
        self.refresh_art = install_tree_art(self.tree, lambda: self.art_rows, lambda: self._root().database)
        self.new_button = ttk.Button(self, text="+ New character", style="Accent.TButton", command=new_character)
        self.new_button.pack(side='bottom', fill='x', before=self.tree.master)

    def compact_layout(self, compact):
        self.heading.pack_forget()
        if not compact:
            self.heading.pack(anchor='w', before=self.search_entry)
        self.search_entry.pack_configure(pady=(2 if compact else 10, 0))
        self.search_caption.configure(text='Search cast' if compact else 'Search all profile fields')
        self.filter_button.configure(text='Filters…' if compact else 'Filters / saved filters…')
        self.tree.master.pack_configure(pady=2 if compact else 10)

    def populate(self, rows, selected_id):
        self.art_rows = rows
        self.filter_summary.configure(text=" · ".join(f"{key.title()}: {value}" for key, value in self.filters.items() if value))
        self.empty.configure(text="" if rows else (
            "No matches. Try another search or filter." if self.search.get() or any(self.filters.values()) else "No characters yet. Choose New character to start."))
        self.tree.delete(*self.tree.get_children())
        for key, row in rows.items():
            self.tree.insert("", "end", iid=key, values=(row["name"], row["role"]))
        self.refresh_art()
        self.empty.pack_forget()
        if not rows:
            self.empty.pack(fill='x', before=self.tree.master)
        self.filter_summary.pack_forget()
        if any(self.filters.values()):
            self.filter_summary.pack(fill='x', before=self.tree.master)
        if str(selected_id) in rows:
            self.tree.selection_set(str(selected_id))
