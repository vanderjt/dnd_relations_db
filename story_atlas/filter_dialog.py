"""Roster filter editing and story-local named presets."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .retrieval import FILTER_FIELDS, suggestions, SavedFilters
from .theme import style_tree
from .widgets import ActionBar, wrapping_label
from .scroll_frame import ScrollFrame


class FilterDialog(tk.Toplevel):
    def __init__(self, roster, database, apply):
        super().__init__(roster)
        self.title("Character filters")
        self.geometry("560x570")
        self.transient(roster.winfo_toplevel())
        self.grab_set()
        self.store = SavedFilters(database)
        self.apply = apply
        bottom = ttk.Frame(self, padding=12)
        bottom.pack(side="bottom", fill="x")
        scroller = ScrollFrame(self)
        scroller.pack(fill="both", expand=True, padx=16)
        body = scroller.content
        wrapping_label(body, text="Combine exact values. Blank means any. Tags require every comma-separated tag.").pack(fill="x")
        self.fields = {}
        for field in ("query", *FILTER_FIELDS):
            ttk.Label(body, text="Search text" if field == "query" else field.title()).pack(anchor="w", pady=(8, 2))
            variable = tk.StringVar(self, roster.search.get() if field == "query" else roster.filters.get(field, ""))
            self.fields[field] = variable
            ttk.Combobox(body, textvariable=variable, values=() if field == "query" else suggestions(database, field), width=42).pack(fill="x")
        ttk.Label(body, text="Saved filter name").pack(anchor="w", pady=(12, 2))
        self.name = tk.StringVar(self)
        self.names = ttk.Combobox(body, textvariable=self.name, values=self.store.names())
        self.names.pack(fill="x")
        bar = ActionBar(bottom)
        bar.pack(fill="x", pady=12)
        for label, action in (("Apply", self.commit), ("Clear", self.clear), ("Save preset", self.save),
                              ("Load preset", self.load), ("Delete preset", self.delete), ("Close", self.destroy)):
            bar.add(ttk.Button(bar, text=label, command=lambda action=action: self.run(action)))
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<Control-Return>", lambda _: self.commit())
        style_tree(self)

    def run(self, action):
        try:
            action()
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Filter not saved", str(error), parent=self)

    def commit(self):
        self.apply({key: value.get() for key, value in self.fields.items()})
        self.destroy()

    def clear(self):
        for value in self.fields.values():
            value.set("")

    def save(self):
        name = self.name.get().strip()
        if name in self.store.names() and not messagebox.askyesno("Replace filter", f"Replace '{name}'?", parent=self):
            return
        self.store.save(name, {key: value.get() for key, value in self.fields.items()})
        self.names.configure(values=self.store.names())

    def load(self):
        for key, value in self.store.load(self.name.get()).items():
            self.fields[key].set(value)

    def delete(self):
        name = self.name.get()
        if name not in self.store.names():
            raise ValueError("Choose an existing saved filter.")
        if messagebox.askyesno("Delete filter", f"Delete '{name}'?", parent=self):
            self.store.delete(name)
            self.names.configure(values=self.store.names())
            self.name.set("")
