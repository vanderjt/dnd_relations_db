"""Timeline browsing plus explicit story-change versus correction editing."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .widgets import table, wrapping_label, text_area, ActionBar
from .theme import style_tree
from .scroll_frame import ScrollFrame
from .relationship_semantics import connection_label, perspectives
from .quick_event import QuickEventDialog
from .chapters import event_label, event_scope


class HistoryDialog(tk.Toplevel):
    def __init__(self, parent, database, changed, ident=None, as_of_id=None):
        super().__init__(parent)
        self.database, self.changed = database, changed
        self.as_of_id = as_of_id
        self.title("Relationship history")
        self.geometry("780x560")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.editor = None
        self.body = body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        self.context = tk.StringVar(self)
        wrapping_label(body, textvariable=self.context, style='Context.TLabel').pack(fill='x', pady=4)
        wrapping_label(body, text="Record a story change to add a state at an event. Correct entry fixes a mistake in that state only. Later states remain independent.").pack(fill="x")
        self.choices = {f"#{row['id']}: {connection_label(row)}": row for row in database.relationship_records()}
        self.choice = tk.StringVar(self, next((key for key, row in self.choices.items() if row["id"] == ident), ""))
        box = ttk.Combobox(body, textvariable=self.choice, values=tuple(self.choices), state="readonly")
        box.pack(fill="x", pady=8)
        box.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        bar = ActionBar(body)
        bar.pack(side="bottom", fill="x")
        for label, command, style in (("Record story change", lambda: self.edit(False), "Primary.TButton"),
                                      ("Correct entry", lambda: self.edit(True), "Secondary.TButton"),
                                      ("Close", self.close, "Secondary.TButton")):
            bar.add(ttk.Button(bar, text=label, style=style, command=command))
        self.tree = table(body, {"event": "Effective from", "active": "Connection status", "state": "Connection", "notes": "Notes"})
        self.tree.bind("<<TreeviewSelect>>", self.update_context)
        self.refresh()
        style_tree(self)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', self.escape)
        self.bind('<Control-Return>', lambda _: self.editor.save() if self.editor else None)

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.states = {}
        chosen = self.choices.get(self.choice.get())
        if not chosen:
            return
        base = next((row for row in self.database.relationship_records() if row["id"] == chosen["id"]), None)
        if base is None:
            return
        self.states["baseline"] = dict(base, active=base["baseline_active"], event_id=None)
        events = {row["id"]: row for row in self.database.events.list()}
        for row in self.database.history.rows(base["id"]):
            self.states[str(row["id"])] = row
        for key, row in self.states.items():
            event = events.get(row["event_id"])
            label = event_label(self.database, event) if event else "Before first event (undated)"
            self.tree.insert("", "end", iid=key, values=(label, "Present" if row["active"] else "Absent / ended", connection_label(row), row["notes"]))
        try:
            effective = self.database.history.editing_state(base['id'], self.as_of_id)
        except ValueError as error:
            self.context.set(str(error))
            return
        key = str(effective['id']) if effective['event_id'] is not None else 'baseline'
        self.tree.selection_set(key)
        self.tree.focus(key)
        self.tree.see(key)
        self.update_context()

    def update_context(self, _event=None):
        events = {row['id']: row for row in self.database.events.list()}
        scope = 'Current' if self.as_of_id is None else 'Before first event' if self.as_of_id == 0 else event_scope(self.database, events[self.as_of_id]) if self.as_of_id in events else 'Unavailable event'
        selection = self.tree.selection()
        if not selection or selection[0] not in self.states:
            self.context.set(f'Inspecting {scope}. Select an entry to correct.')
            return
        key = selection[0]
        row = self.states[key]
        entry = 'baseline (undated)' if key == 'baseline' else f"state #{row['id']} at {event_label(self.database, events[row['event_id']])}"
        presence = 'Present' if row['active'] else 'Not yet begun' if key == 'baseline' else 'Ended'
        self.context.set(f'Inspecting {scope}: {presence}. Correct entry updates {entry}.')

    def edit(self, correction):
        base = self.choices.get(self.choice.get())
        if base is None:
            return
        selection = self.tree.selection()
        if correction and not selection:
            messagebox.showinfo("Choose a state", "Select the starting state or a dated state to correct.", parent=self)
            return
        row = self.states[selection[0]] if selection else list(self.states.values())[-1]
        self.body.pack_forget()
        self.editor = StateEditor(self, self.database, self.completed, base['id'], row, correction, closed=self.return_to_history)
        self.editor.pack(fill='both', expand=True)
        if correction:
            wrapping_label(self.editor, textvariable=self.context, style='Context.TLabel').pack(
                before=self.editor.heading, fill='x', padx=12, pady=4)
        self.editor.back_button.configure(text='Back to history')
        return self.editor

    def return_to_history(self):
        if self.editor:
            self.editor.destroy()
            self.editor = None
        self.body.pack(fill='both', expand=True)
        self.refresh()

    def escape(self, _event=None):
        if self.editor and self.editor.step == 'review':
            self.editor.back_to_edit()
        elif self.editor:
            self.editor.close()
        else:
            self.close()
        return 'break'

    def close(self):
        if self.editor and not self.editor.close():
            return
        self.destroy()

    def completed(self, message):
        self.return_to_history()
        self.changed(message)
        self.refresh()
        self.grab_set()


from .state_editor import StateDialog, StateEditor

# Legacy import name; review now lives inside StateEditor.
StoryChangeReviewDialog = StateEditor
