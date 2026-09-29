"""Reusable relationship-state task with internal edit/review steps."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .widgets import ActionBar, wrapping_label, text_area, read_only_text_area, set_read_only_text, field_error
from .scroll_frame import ScrollFrame
from .graph_legend import category_for
from .relationship_semantics import perspectives
from .chapters import event_label, event_scope
from .quick_event import QuickEventDialog
from .theme import style_tree


class StateEditor(ttk.Frame):
    def __init__(self, parent, database, changed, relationship_id, row, correction,
                 event_id=None, review=True, closed=None):
        super().__init__(parent)
        self.database, self.changed, self.relationship_id = database, changed, relationship_id
        self.row, self.correction, self.fixed_event_id = row, correction, event_id
        self.closed = closed or self.destroy
        self.step = 'edit'
        self.review_before_save = True
        self.heading = wrapping_label(self, text='Correct entry · rewrites this state only' if correction else 'Record story change · adds a dated state', style='Heading.TLabel', font='AtlasHeading')
        self.heading.pack(fill='x', padx=12, pady=6)
        self.context = wrapping_label(self, style='Context.TLabel')
        self.context.pack(fill='x', padx=12)
        self.footer = ActionBar(self)
        self.footer.pack(side='bottom', fill='x', padx=12, pady=8)
        self.save_button = self.footer.add(ttk.Button(self.footer, text='Review correction' if correction else 'Review change', style='Primary.TButton', command=self.save))
        self.back_button = self.footer.add(ttk.Button(self.footer, text='Back to connections', command=self.close))
        self.error = tk.StringVar(self)
        wrapping_label(self, textvariable=self.error, style='Validation.TLabel').pack(side='bottom', fill='x', padx=12)
        self.scroller = ScrollFrame(self)
        self.scroller.pack(fill='both', expand=True, padx=12)
        body = self.scroller.content
        self.event_choices = {event_label(database, event): event['id'] for event in database.events.list()}
        names = {item['id']: item['name'] for item in database.characters()}
        self.sources = {f"{names[node]} (#{node})": node for node in (row['source_id'], row['target_id'])}
        chosen_event = event_id if event_id is not None else row.get('event_id') if correction else None
        self.variables = {key: tk.StringVar(self, value) for key, value in dict(
            event=next((name for name, ident in self.event_choices.items() if ident == chosen_event), 'Undated starting state' if correction and row.get('event_id') is None else ''),
            source=next(name for name, ident in self.sources.items() if ident == row['source_id']),
            presence='Present' if row['active'] else 'Ended', kind=row['kind'],
            semantics=row['semantics'].title(), inverse_label=row['inverse_label'], category=category_for(row, self)).items()}
        self.original_category = row.get('category', '')
        self.category_changed = False
        self.variables['category'].trace_add('write', lambda *_: setattr(self, 'category_changed', True))
        self.boxes, self.errors = {}, {}
        for key, label, choices in (
            ('event', 'Effective event', tuple(self.event_choices)),
            ('source', 'From character · other character is To', tuple(self.sources)),
            ('presence', 'Present = active from this event · Ended = ends at this event', ('Present', 'Ended')),
            ('kind', 'Relationship type', ()),
            ('category', 'Link category · legend color', ('Support', 'Conflict', 'Personal', 'Other')),
            ('semantics', 'Directional → one-way · Mutual ↔ shared', ('Directional', 'Mutual')),
            ('inverse_label', 'Inverse label · optional, directional only', ())):
            wrapping_label(body, text=label).pack(fill='x', pady=(6, 2))
            state = 'disabled' if key == 'event' and (event_id is not None or correction and row.get('event_id') is None) else 'readonly' if choices or key == 'event' else 'normal'
            if key == 'kind':
                from .searchable_combo import SearchableCombobox
                from .models import RELATIONSHIP_TYPES
                kinds = tuple(dict.fromkeys((*RELATIONSHIP_TYPES, *(item['kind'] for item in database.relationships()))))
                box = SearchableCombobox(body, self.variables[key], kinds)
            elif key == 'inverse_label':
                box = ttk.Entry(body, textvariable=self.variables[key])
            else:
                box = ttk.Combobox(body, textvariable=self.variables[key], values=choices, state=state)
            box.pack(fill='x')
            self.boxes[key] = box
            self.errors[key] = tk.StringVar(self)
            field_error(body, self.errors[key], box)
        self.event_box = self.boxes['event']
        if not correction and event_id is None:
            ttk.Button(body, text='Create event…', command=self.create_event).pack(anchor='w')
        self.creation_status = tk.StringVar(self)
        wrapping_label(body, textvariable=self.creation_status, style='Muted.TLabel').pack(fill='x')
        self.preview = tk.StringVar(self)
        wrapping_label(body, textvariable=self.preview, style='Detail.TLabel').pack(fill='x', pady=8)
        ttk.Label(body, text='Notes · optional').pack(anchor='w')
        self.notes = text_area(body, height=5)
        self.notes.pack(fill='x')
        self.notes.insert('1.0', row['notes'])
        self.notes.bind('<Tab>', lambda _: self.traverse())
        self.notes.bind('<Control-Return>', self.shortcut)
        self.notes.bind('<Control-KP_Enter>', self.shortcut)
        self.review_content = read_only_text_area(self, height=12)
        for variable in self.variables.values():
            variable.trace_add('write', self.update_preview)
        self.original = self.values()
        self.update_preview()
        style_tree(self)

    def traverse(self):
        self.save_button.focus_set()
        return 'break'

    def shortcut(self, _event=None):
        self.save()
        return 'break'

    def values(self):
        return {**{key: value.get() for key, value in self.variables.items()}, 'notes': self.notes.get('1.0', 'end-1c')}

    def create_event(self):
        return QuickEventDialog(self.winfo_toplevel(), self.database, self.event_created)

    def event_created(self, ident):
        row = next(row for row in self.database.events.list() if row['id'] == ident)
        label = event_label(self.database, row)
        self.event_choices[label] = ident
        self.event_box.configure(values=tuple(self.event_choices))
        self.variables['event'].set(label)
        self.creation_status.set('Event saved. Relationship change not recorded yet.')

    def update_preview(self, *_):
        values = self.values()
        source = values['source']
        target = next((name for name in self.sources if name != source), 'To character')
        self.preview.set(perspectives(source, target, values['kind'], values['semantics'].lower(), values['inverse_label']) + f"\nCategory: {values['category']}")
        event = next((row for row in self.database.events.list() if row['id'] == self.event_choices.get(values['event'])), None)
        scope = event_scope(self.database, event) if event else 'Before first event · undated starting state' if self.correction and self.row.get('event_id') is None else 'Choose an effective event'
        entry = (f"Correcting state #{self.row['id']}" if self.row.get('event_id') is not None else 'Correcting baseline') if self.correction else 'Recording a new state'
        self.context.configure(text=f"{scope} · {entry}\nConnection #{self.relationship_id} · {' / '.join(self.sources)}")

    def payload(self):
        values = self.values()
        source = self.sources.get(values['source'])
        target = next((ident for ident in self.sources.values() if ident != source), None)
        return dict(source_id=source, target_id=target, kind=values['kind'], notes=values['notes'],
                    semantics=values['semantics'].lower(), inverse_label=values['inverse_label'], category=values['category'] if self.category_changed else self.original_category)

    def validate(self):
        for error in self.errors.values():
            error.set('')
        values = self.values()
        invalid = {}
        if not (self.correction and self.row.get('event_id') is None) and values['event'] not in self.event_choices:
            invalid['event'] = 'Choose an existing event.'
        if values['source'] not in self.sources:
            invalid['source'] = 'Choose a character in this pair.'
        if not values['kind'].strip():
            invalid['kind'] = 'Enter a relationship type.'
        if values['semantics'] not in ('Directional', 'Mutual'):
            invalid['semantics'] = 'Choose Directional or Mutual.'
        if values['semantics'] == 'Mutual' and values['inverse_label'].strip():
            invalid['inverse_label'] = 'Clear the inverse label or choose Directional. Your input has been kept.'
        if values['presence'] not in ('Present', 'Ended'):
            invalid['presence'] = 'Choose Present or Ended.'
        for key, message in invalid.items():
            self.errors[key].set(message)
        if invalid:
            self.boxes[next(iter(invalid))].focus_set()
            return False
        return True

    def save(self):
        if self.step == 'review':
            return self.commit()
        self.review_change()
        return False

    def review_change(self):
        if not self.validate():
            return None
        if not self.correction:
            try:
                self.row = self.database.history.state_before(self.relationship_id, self.event_choices[self.variables['event'].get()])
            except ValueError as error:
                self.error.set(f'Not saved: {error}')
                return None
        self.reviewed = self.values()
        before = self.row
        source = next(name for name, ident in self.sources.items() if ident == before['source_id'])
        target = next(name for name in self.sources if name != source)
        before_text = perspectives(source, target, before['kind'], before['semantics'], before['inverse_label'])
        text = (('Existing entry' if self.correction else 'Immediately before') +
                f": {'Present' if before['active'] else 'Ended'}\n{before_text}\n{before['notes']}\n\n" +
                f"Proposed entry: {self.reviewed['presence']}\n{self.preview.get()}\n{self.reviewed['notes']}\n\n" +
                'Later recorded states remain independent. ' + ('This corrects the existing entry; no new story change is added.' if self.correction else 'This state lasts until the next recorded change.'))
        set_read_only_text(self.review_content, text)
        self.scroller.pack_forget()
        self.review_content.pack(fill='both', expand=True, padx=12, pady=8)
        self.step = 'review'
        self.save_button.configure(text='Save correction' if self.correction else 'Record story change')
        self.back_button.configure(text='Back to edit', command=self.back_to_edit)
        self.save_button.focus_set()
        return self

    def back_to_edit(self):
        self.review_content.pack_forget()
        self.scroller.pack(fill='both', expand=True, padx=12)
        self.step = 'edit'
        self.save_button.configure(text='Review correction' if self.correction else 'Review change')
        self.back_button.configure(text='Back to connections', command=self.close)
        self.boxes['kind'].focus_set()

    def record(self):
        return self.commit()

    def commit(self):
        if self.step != 'review' or self.values() != self.reviewed:
            self.review_change()
            return False
        try:
            if self.correction:
                current = (next((row for row in self.database.relationship_records() if row['id'] == self.relationship_id), None)
                           if self.row.get('event_id') is None else
                           next((row for row in self.database.history.rows(self.relationship_id) if row['id'] == self.row['id']), None))
                if current and self.row.get('event_id') is None:
                    current = dict(current, active=current['baseline_active'], event_id=None)
            else:
                current = self.database.history.state_before(self.relationship_id, self.fixed_event_id or self.event_choices[self.reviewed['event']])
            compared = ('source_id', 'target_id', 'kind', 'notes', 'semantics', 'inverse_label', 'category', 'active')
            if current is None or any(current.get(key) != self.row.get(key) for key in compared):
                if current:
                    self.row = current
                self.back_to_edit()
                self.error.set('The saved state changed. Review the updated before/after again; your input has been kept.')
                return False
            data = self.payload()
            active = self.reviewed['presence'] == 'Present'
            if self.correction and self.row.get('event_id') is None:
                self.database.history.correct_baseline(self.relationship_id, data, active, draft_key=getattr(self, 'draft_key', None))
            else:
                self.database.history.write(self.relationship_id, self.event_choices[self.reviewed['event']], data, active,
                                            self.row['id'] if self.correction else None, draft_key=getattr(self, 'draft_key', None))
        except (ValueError, sqlite3.Error) as error:
            self.error.set(f'Not saved: {error}')
            return False
        self.changed('Relationship entry corrected' if self.correction else 'Story relationship change recorded')
        return True

    def close(self):
        if self.values() != self.original:
            answer = messagebox.askyesnocancel('Unfinished relationship state', 'Save this state before leaving?', parent=self.winfo_toplevel())
            if answer is None or (answer and not self.save()):
                return False
            if answer:
                return True
        self.closed()
        return True


class StateDialog(tk.Toplevel):
    """Standalone host for the same state task used inside event workflows."""
    def __init__(self, parent, database, changed, relationship_id, row, correction, event_id=None, review=False):
        super().__init__(parent)
        self.title('Correct entry' if correction else 'Record story change')
        self.geometry('650x680')
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        def completed(message):
            self.destroy()
            if isinstance(parent, tk.Toplevel) and parent.winfo_exists():
                parent.grab_set()
            changed(message)
        self.editor = StateEditor(self, database, completed, relationship_id, row, correction, event_id, review, self.destroy)
        self.editor.pack(fill='both', expand=True)
        self.editor.back_button.configure(text='Cancel')
        self.protocol('WM_DELETE_WINDOW', self.editor.close)
        self.bind('<Escape>', lambda _: self.editor.back_to_edit() if self.editor.step == 'review' else self.editor.close())
        self.bind('<Control-Return>', lambda _: self.editor.save())

    def __getattr__(self, name):
        editor = self.__dict__.get('editor')
        if editor is not None and hasattr(editor, name):
            return getattr(editor, name)
        raise AttributeError(name)
