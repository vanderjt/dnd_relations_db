"""Minimal event creation for an in-progress relationship change."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from .widgets import ActionBar, wrapping_label
from .chapter_dialog import ChapterPicker


class QuickEventDialog(tk.Toplevel):
    def __init__(self, parent, database, created):
        super().__init__(parent)
        self.database, self.created = database, created
        self.title("Create event")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _: self.close())
        self.title_value = tk.StringVar(self)
        self.sequence = tk.StringVar(self, str(max((row["sequence"] for row in database.events.list()), default=0) + 1))
        self.status = tk.StringVar(self)
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Create event", style="Heading.TLabel").pack(anchor="w")
        wrapping_label(body, text="This saves an event now. Your relationship change is not recorded yet.", style="Muted.TLabel").pack(fill="x", pady=(4, 10))
        ttk.Label(body, text="Title").pack(anchor="w")
        self.title_entry = ttk.Entry(body, textvariable=self.title_value)
        self.title_entry.pack(fill="x", pady=(3, 8))
        self.chapter = ChapterPicker(body, database, on_change=self.chapter_changed)
        self.chapter.pack(fill='x', pady=6)
        self.chapter_changed()
        self.original = self.values()
        ttk.Label(body, text="Position within chapter").pack(anchor="w")
        ttk.Entry(body, textvariable=self.sequence).pack(fill="x", pady=(3, 8))
        wrapping_label(body, textvariable=self.status, style="Validation.TLabel").pack(fill="x")
        bar = ActionBar(body)
        bar.pack(fill="x", pady=(12, 0))
        bar.add(ttk.Button(bar, text="Save event", style="Primary.TButton", command=self.save))
        bar.add(ttk.Button(bar, text="Back to relationship change", style="Navigation.TButton", command=self.close))
        self.focus_job = self.after_idle(self.title_entry.focus_set)

    def destroy(self):
        # A quick close can happen before Tk delivers the initial focus callback.
        if getattr(self, 'focus_job', None):
            self.after_cancel(self.focus_job)
            self.focus_job = None
        super().destroy()

    def save(self):
        try:
            ident = self.database.chapters.save_event(self.title_value.get(), "", int(self.sequence.get()), chapter_id=self.chapter.get())
        except (ValueError, sqlite3.Error) as error:
            self.status.set(str(error))
            return False
        self.created(ident)
        self.finish()
        return True

    def close(self):
        if self.values() != self.original:
            answer = messagebox.askyesnocancel(
                "Unfinished event",
                "Save this event before returning to the relationship change?\n\n"
                "Yes: save the event. No: discard this event. Cancel: keep editing.",
                parent=self,
            )
            if answer is None:
                self.focus_set()
                return
            if answer:
                self.save()
                return
        self.finish()

    def values(self):
        return self.title_value.get(), self.chapter.get(), self.sequence.get()

    def finish(self):
        self.destroy()
        if self.master.winfo_exists():
            self.master.grab_set()
            self.master.focus_set()

    def chapter_changed(self):
        self.sequence.set(str(1 + sum(row['chapter_id'] == self.chapter.get() for row in self.database.events.list())))
