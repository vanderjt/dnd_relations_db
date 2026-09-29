"""Small, reusable character creation step for in-progress workflows."""
import sqlite3
import tkinter as tk
from tkinter import ttk

from .widgets import ActionBar, wrapping_label


class QuickCharacterDialog(ttk.Frame):
    """Name-only step embedded in its caller, rather than another modal window."""

    def __init__(self, parent, database, created, closed, guarded=False):
        super().__init__(parent)
        self.database, self.created, self.closed = database, created, closed
        self.guarded = guarded
        self.name = tk.StringVar(self)
        self.status = tk.StringVar(self)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Create character", style="Heading.TLabel").pack(anchor="w")
        wrapping_label(body, text="This saves the character now. Your relationship is not saved yet.",
                       style="Muted.TLabel").pack(fill="x", pady=(4, 12))
        ttk.Label(body, text="Name").pack(anchor="w")
        self.name_entry = ttk.Entry(body, textvariable=self.name, width=42)
        self.name_entry.pack(fill="x", pady=(4, 0))
        wrapping_label(body, textvariable=self.status, style="Validation.TLabel").pack(fill="x", pady=(4, 0))
        bar = ActionBar(body)
        bar.pack(fill="x", pady=(16, 0))
        bar.add(ttk.Button(bar, text="Create character", style="Primary.TButton", command=self.save))
        bar.add(ttk.Button(bar, text="Back", style="Navigation.TButton", command=self.cancel))
        self.focus_job = self.after_idle(self.name_entry.focus_set)

    def destroy(self):
        if getattr(self, 'focus_job', None):
            self.after_cancel(self.focus_job)
            self.focus_job = None
        super().destroy()

    def save(self):
        try:
            character_id = self.database.save_character({"name": self.name.get()})
        except (ValueError, sqlite3.Error) as error:
            self.status.set(str(error))
            self.name_entry.focus_set()
            return False
        self.created(character_id)
        self.closed()
        self.destroy()
        return True

    def cancel(self):
        if self.guarded and self.name.get().strip():
            from .task_prompt import save_discard_stay
            answer = save_discard_stay(self)
            if answer is None:
                return
            if answer:
                self.save()
                return
        self.closed()
        self.destroy()
