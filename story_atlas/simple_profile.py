"""Full shared profile editor hosted in the graph task pane."""
import sqlite3
import tkinter as tk
from tkinter import ttk
from .profile_editor import ProfileEditor
from .draft_controller import DraftController
from .models import LONG_FIELDS
from .chapters import event_label
from .widgets import ActionBar, wrapping_label


class SimpleProfile(ttk.Frame):
    def __init__(self, parent, workspace, row=None, recovered=None):
        super().__init__(parent)
        self.workspace, self.database = workspace, workspace.database
        self.character_id = row['id'] if row else None
        self.events = {'Before first event': None}
        self.events.update({event_label(self.database, event): event['id'] for event in self.database.events.list()})
        current_event = workspace.graph.as_of_id
        if current_event is None and self.database.events.list():
            current_event = self.database.events.list()[-1]['id']
        intro = row.get('introduction_event_id') if row else current_event or None
        self.intro = tk.StringVar(self, next((label for label, ident in self.events.items() if ident == intro), 'Before first event'))
        bar = ActionBar(self)
        bar.pack(side='bottom', fill='x')
        self.save_button = bar.add(ttk.Button(bar, text='Save character', width=0, command=self.save))
        bar.add(ttk.Button(bar, text='Close / Return', width=0, command=workspace.close_task))
        self.error = tk.StringVar(self)
        error_label = wrapping_label(self, textvariable=self.error, style='Validation.TLabel')
        self.error.trace_add('write', lambda *_: error_label.pack(side='bottom', fill='x') if self.error.get() else error_label.pack_forget())
        self.editor = ProfileEditor(self, lambda: self.database, simple=True)
        self.editor.pack(fill='both', expand=True)
        body = self.editor.scroller.content
        first = body.winfo_children()[0]
        context = ttk.Frame(body)
        context.pack(fill='x', after=self.editor.field_widgets['character_type'])
        self.timing = ttk.Frame(context)
        self.timing_summary = tk.StringVar(self)
        def timing_caption(*_):
            label = next((row['title'] for row in self.database.events.list() if row['id'] == self.events.get(self.intro.get())), self.intro.get())
            self.timing_summary.set(f'Introduced in {label}')
        timing_caption()
        self.intro.trace_add('write', timing_caption)
        wrapping_label(context, textvariable=self.timing_summary, style='Muted.TLabel').pack(fill='x')
        ttk.Button(context, text='Change introduction…', command=lambda: self.timing.pack(fill='x')).pack(anchor='w')
        wrapping_label(self.timing, text='Changing introduction reassigns chronology. Connections cannot begin before either character.').pack(fill='x')
        ttk.Combobox(self.timing, textvariable=self.intro, values=tuple(self.events), state='readonly').pack(fill='x')
        self.fields = self.editor.fields
        for key, field in self.fields.items():
            value = (row or {}).get(key, 'neutral' if key == 'narrative_role' else 'Neutral NPC' if key == 'character_type' else 'Neutral' if key == 'classification' else '')
            if key in LONG_FIELDS:
                field.insert('1.0', value)
            else:
                field.set(value)
        self.original = self.values()
        self.draft = DraftController(self)
        self.draft.status.set('Unsaved character' if self.character_id is None else 'Saved profile')
        self.intro.trace_add('write', lambda *_: self.draft.schedule())
        wrapping_label(self, textvariable=self.draft.status, style='Muted.TLabel').pack(side='bottom', fill='x')
        if recovered:
            for key, value in recovered.items():
                if key in self.fields:
                    field = self.fields[key]
                    if key in LONG_FIELDS:
                        field.delete('1.0', 'end')
                        field.insert('1.0', value)
                    else:
                        field.set(value)
            if not recovered.get('character_type'):
                from .character_type import from_legacy
                self.fields['character_type'].set(from_legacy(recovered.get('classification', 'Neutral'), recovered.get('narrative_role', 'neutral')))
            intro = recovered.get('introduction_event_id')
            self.intro.set(next((label for label, ident in self.events.items() if ident == intro), f'Missing event #{intro} · choose replacement'))
        self.editor.refresh_indicators()
        self.update_save()
        self.editor.field_widgets['name'].focus_set()

    def update_save(self):
        self.save_button.state(['!disabled' if self.character_id is None or self.values() != self.original else 'disabled'])
        self.editor.refresh_indicators()

    def values(self):
        values = {key: widget.get('1.0', 'end-1c') if key in LONG_FIELDS else self.editor.field_widgets['tags'].value() if key == 'tags' else widget.get() for key, widget in self.fields.items()}
        return dict(values, introduction_event_id=self.events.get(self.intro.get(), -1))

    def save(self):
        if self.character_id is not None and self.values() == self.original:
            return True
        try:
            creating = self.character_id is None
            self.character_id = self.database.save_character(self.values(), self.character_id)
        except (ValueError, sqlite3.Error) as error:
            self.error.set(str(error))
            return False
        saved = next(row for row in self.database.characters() if row['id'] == self.character_id)
        self.fields['character_type'].set(saved['character_type'])
        self.editor.field_widgets['tags'].add()
        self.original = self.values()
        self.draft.cancel()
        self.error.set('')
        self.draft.status.set('Character saved')
        self.update_save()
        self.workspace.character_saved(self.character_id, creating)
        return True

    def destroy(self):
        self.draft.cancel()
        super().destroy()
