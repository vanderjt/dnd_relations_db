"""Explicit event removal review, with no implicit reference loss."""
import sqlite3
import tkinter as tk
from tkinter import ttk
from .chapters import event_label
from .widgets import ActionBar, wrapping_label, read_only_text_area, set_read_only_text


class EventReassignment(ttk.Frame):
    def __init__(self, parent, workspace):
        super().__init__(parent)
        self.workspace, self.database = workspace, workspace.database
        self.ident = workspace.graph.as_of_id
        self.choices = {event_label(self.database, row): row['id'] for row in self.database.events.list() if row['id'] != self.ident}
        self.replacement = tk.StringVar(self)
        self.original = ''
        self.preview = None
        wrapping_label(self, text='Remove event · explicitly reassign introductions, relationship states and participants. This operation is recoverable from database backups.').pack(fill='x')
        ttk.Combobox(self, textvariable=self.replacement, values=tuple(self.choices), state='readonly').pack(fill='x')
        bar = ActionBar(self)
        bar.pack(side='bottom', fill='x')
        self.button = bar.add(ttk.Button(bar, text='Review reassignment', command=self.save))
        bar.add(ttk.Button(bar, text='Close / Return', command=workspace.close_task))
        self.error = tk.StringVar(self)
        wrapping_label(self, textvariable=self.error, style='Validation.TLabel').pack(side='bottom', fill='x')
        self.details = read_only_text_area(self, height=12)
        self.details.pack(fill='both', expand=True)

    def values(self):
        return self.replacement.get()

    def save(self):
        try:
            replacement = self.choices.get(self.values())
            current = self.database.events.removal_preview(self.ident, replacement)
            if self.preview != current:
                self.preview = current
                introductions = '\n'.join(f"{row['name']} (#{row['id']}){' [Trash]' if row['deleted_at'] else ''}" for row in current['introductions']) or 'None'
                states = '\n'.join(f"State #{row['id']} · connection #{row['relationship_id']}: {row['kind']}" for row in current['states']) or 'None'
                set_read_only_text(self.details, f"Remove: {current['event']['title']}\nMove references to: {current['replacement']['title']}\n\nIntroductions:\n{introductions}\n\nRelationship entries:\n{states}\n\nParticipants: {len(current['participants'])}\nRecovery drafts to reassign: {len(current['drafts'])}\n\nNo states will be merged or discarded. Chronology conflicts reject the entire operation.")
                self.button.configure(text='Confirm removal and reassignment')
                return False
            self.database.events.remove(self.preview)
        except (ValueError, sqlite3.Error) as error:
            self.error.set(str(error))
            return False
        self.original = self.values()
        self.workspace.event_saved(replacement)
        return True
