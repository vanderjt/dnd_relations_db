"""One event task: choose a connection, describe, review, and commit."""
import tkinter as tk
from tkinter import ttk
from .widgets import wrapping_label, ActionBar
from .relationship_semantics import connection_label
from .searchable_combo import SearchableCombobox
from .state_editor import StateEditor
from .chapters import event_scope
from .theme import style_tree


class EventRelationshipChangeDialog(tk.Toplevel):
    def __init__(self, parent, database, changed, event, completed):
        super().__init__(parent)
        self.database, self.changed, self.event, self.completed = database, changed, event, completed
        self.app = parent.winfo_toplevel()
        self.title('Relationship change')
        self.geometry('720x700')
        self.transient(self.app)
        self.grab_set()
        self.editor = None
        self.saved_messages = []
        wrapping_label(self, text=event_scope(database, event), style='Heading.TLabel').pack(fill='x', padx=16, pady=8)
        self.body = body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        wrapping_label(body, text='Choose a connection, then record a story change or correct an entry saved at this event.').pack(fill='x')
        self.participant_ids = {row['character_id'] for row in database.events.participants() if row['event_id'] == event['id']}
        records = database.relationship_records()
        records.sort(key=lambda row: (not bool({row['source_id'], row['target_id']} & self.participant_ids), row['id']))
        self.choices = {}
        for row in records:
            prefix = 'Participant connection' if {row['source_id'], row['target_id']} & self.participant_ids else 'Other connection'
            self.choices[f"{prefix} · #{row['id']}: {connection_label(row)}"] = row
        self.only_participants = tk.BooleanVar(self, False)
        ttk.Checkbutton(body, text='Event-participant connections only', variable=self.only_participants, command=self.filter_choices).pack(anchor='w', pady=6)
        self.choice = tk.StringVar(self)
        self.selector = SearchableCombobox(body, self.choice, self.choices)
        self.selector.pack(fill='x', pady=8)
        self.status = tk.StringVar(self)
        self.status_label = wrapping_label(body, textvariable=self.status, style='Muted.TLabel')
        self.status_label.pack(fill='x')
        bar = ActionBar(body)
        bar.pack(fill='x', pady=12)
        self.continue_button = bar.add(ttk.Button(bar, text='Record story change', style='Primary.TButton', command=self.describe))
        self.review_button = bar.add(ttk.Button(bar, text='Correct entry', command=self.review, state='disabled'))
        self.graph_button = bar.add(ttk.Button(bar, text='Graph at event', command=self.show_graph))
        self.done_button = bar.add(ttk.Button(bar, text='Close / Return', command=self.close))
        self.choice.trace_add('write', lambda *_: self.selection_changed())
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', self.escape)
        self.bind('<Control-Return>', self.shortcut)
        style_tree(self)

    def selected(self):
        return self.choices.get(self.choice.get())

    def filter_choices(self):
        self.selector.set_choices([label for label, row in self.choices.items()
            if not self.only_participants.get() or {row['source_id'], row['target_id']} & self.participant_ids])

    def selected_state(self):
        row = self.selected()
        return next((state for state in self.database.history.rows(row['id']) if state['event_id'] == self.event['id']), None) if row else None

    def selection_changed(self):
        exists = self.selected_state()
        self.review_button.state(['!disabled' if exists else 'disabled'])
        self.continue_button.state(['disabled' if exists else '!disabled'])
        self.review_button.configure(style='Primary.TButton' if exists else 'Secondary.TButton')
        self.continue_button.configure(style='Secondary.TButton' if exists else 'Primary.TButton')
        self.status.set('A state is already recorded here. Correct entry rewrites that state only.' if exists else '')

    def describe(self):
        return self.start(False)

    def review(self):
        return self.start(True)

    def start(self, correction):
        row = self.selected()
        if row is None:
            self.status.set('Choose a connection from the search results.')
            self.selector.focus_set()
            return None
        existing = self.selected_state()
        if bool(existing) != correction:
            self.selection_changed()
            return None
        state = existing if correction else self.database.history.state_before(row['id'], self.event['id'])
        self.body.pack_forget()
        self.editor = StateEditor(self, self.database, self.recorded, row['id'], state, correction,
                                  self.event['id'], closed=self.return_to_choices)
        self.editor.pack(fill='both', expand=True)
        return self.editor

    def return_to_choices(self):
        if self.editor:
            self.editor.destroy()
            self.editor = None
        self.body.pack(fill='both', expand=True)
        self.selection_changed()
        self.selector.focus_set()

    def recorded(self, message):
        relationship_id = self.editor.relationship_id
        self.completed(message)
        if hasattr(self.master, 'highlight_change'):
            self.master.highlight_change(relationship_id)
        self.saved_messages.append(message)
        self.return_to_choices()
        self.choice.set('')
        self.continue_button.configure(text='Add another change')
        self.status.set(f"✓ Change recorded at {self.event['title']} · {len(self.saved_messages)} committed saves")
        self.status_label.configure(style='Success.TLabel')

    def shortcut(self, _event=None):
        if self.editor:
            self.editor.save()
        elif self.selected_state():
            self.review()
        else:
            self.describe()
        return 'break'

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

    def show_graph(self):
        self.app.navigation.open_graph_from_event(self.event['id'])
        self.destroy()
