"""Search and selection widgets for the character list."""
import tkinter as tk
from tkinter import ttk
from .widgets import table, wrapping_label


class CharacterRoster(ttk.Frame):
    def __init__(self, parent, new_character):
        super().__init__(parent, width=300)
        ttk.Label(self, text="Your cast", style="Muted.TLabel").pack(anchor="w")
        self.empty = wrapping_label(self, style="Muted.TLabel")
        self.empty.pack(fill="x")
        self.search = tk.StringVar(self)
        self.filters = {}
        ttk.Entry(self, textvariable=self.search).pack(fill="x", pady=(10, 0))
        wrapping_label(self, text="Search all profile fields", style="Muted.TLabel").pack(fill="x")
        self.filter_button = ttk.Button(self, text="Filters / saved filters…")
        self.filter_button.pack(fill="x", pady=4)
        self.filter_summary = wrapping_label(self, style="Muted.TLabel")
        self.filter_summary.pack(fill="x")
        self.tree = table(self, {"name": "Name", "role": "Role"})
        ttk.Button(self, text="+ New character", style="Accent.TButton", command=new_character).pack(fill="x")

    def populate(self, rows, selected_id):
        self.filter_summary.configure(text=" · ".join(f"{key.title()}: {value}" for key, value in self.filters.items() if value))
        self.empty.configure(text="" if rows else (
            "No matches. Try another search or filter." if self.search.get() or any(self.filters.values()) else "No characters yet. Choose New character to start."))
        self.tree.delete(*self.tree.get_children())
        for key, row in rows.items():
            self.tree.insert("", "end", iid=key, values=(row["name"], row["role"]))
        if str(selected_id) in rows:
            self.tree.selection_set(str(selected_id))
