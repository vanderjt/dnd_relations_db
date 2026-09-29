"""Guided connection creation: starting character, others, details, review."""
import sqlite3
import tkinter as tk
from tkinter import ttk
from .models import RELATIONSHIP_TYPES
from .chapters import event_label
from .scroll_frame import ScrollFrame
from .widgets import ActionBar, wrapping_label, text_area, read_only_text_area, set_read_only_text
from .searchable_combo import SearchableCombobox
from .connection_picker import CharacterPicker, CharacterCard
from .graph_legend import EDGE_STYLES


class BatchPane(ttk.Frame):
    def __init__(self, parent, workspace, recovered=None):
        super().__init__(parent)
        self.workspace, self.database = workspace, workspace.database
        self.names = self.character_names()
        self.events = {'Before first event': None}
        self.events.update({event_label(self.database, row): row['id'] for row in self.database.events.list()})
        self.variables = {key: tk.StringVar(self) for key in ('source', 'target', 'kind', 'semantics', 'inverse_label', 'event')}
        self.category = tk.StringVar(self, 'Other')
        self.nested = None
        self.targets = []
        self.reviewed = None
        self.step = 0
        self.focus_job = None
        self.error = tk.StringVar(self)
        self.heading = tk.StringVar(self)
        self.summary = tk.StringVar(self)
        self.heading_label = wrapping_label(self, textvariable=self.heading, style='Heading.TLabel')
        self.heading_label.pack(fill='x', pady=(4, 6))
        self.summary_label = wrapping_label(self, textvariable=self.summary, style='Context.TLabel')
        self.source_header = ttk.Frame(self)
        self.source_header.columnconfigure(0, weight=1)
        self.source_card = CharacterCard(self.source_header)
        self.source_card.grid(row=0, column=0, sticky='ew')
        self.change_button = ttk.Button(self.source_header, text='Change character', command=lambda: self.show_step(0))
        self.change_button.grid(row=0, column=1, sticky='ne', padx=(6, 0))
        wrapping_label(self.source_header, text='Connect to…', style='Heading.TLabel').grid(row=1, column=0, columnspan=2, sticky='ew', pady=(8, 4))
        self.bar = bar = ActionBar(self)
        bar.pack(side='bottom', fill='x')
        self.save_button = bar.add(ttk.Button(bar, text='Continue', style='Primary.TButton', command=self.advance))
        self.back_button = bar.add(ttk.Button(bar, text='Back', command=self.back))
        bar.add(ttk.Button(bar, text='Cancel', command=workspace.close_task))
        self.navigation = bar.items.copy()
        wrapping_label(self, textvariable=self.error, style='Validation.TLabel').pack(side='bottom', fill='x')
        self.scroller = ScrollFrame(self)
        self.scroller.pack(fill='both', expand=True)
        self.pages = [ttk.Frame(self), ttk.Frame(self), ttk.Frame(self.scroller.content)]
        self.boxes = {}
        for index, key in enumerate(('source', 'target')):
            body = self.pages[index]
            if index == 0:
                wrapping_label(body, text='Choose a character to pick their connections.').pack(fill='x', pady=(0, 8))
            ttk.Button(body, text='Create a character…', command=lambda key=key: self.create_character(key)).pack(side='bottom', anchor='w', pady=6)
            picker = CharacterPicker(body, self, source=index == 0)
            picker.pack(fill='both', expand=True)
            self.boxes[key] = picker
            if index == 1:
                self.selected_bar = ttk.Frame(picker.list.content)
        body = self.pages[2]
        wrapping_label(body, text='Describe the connection. These details apply to every selected character.').pack(fill='x', pady=(0, 8))
        kinds = sorted(set(RELATIONSHIP_TYPES) | {row['kind'] for row in self.database.relationships()})
        for key, label, choices in (
            ('kind', 'Relationship label · e.g. Friend, Mentor, Rival', kinds),
            ('semantics', 'Direction', ('Mutual', 'Directional')),
            ('category', 'Legend color', tuple(EDGE_STYLES)),
            ('event', 'Begins at', tuple(self.events))):
            wrapping_label(body, text=label).pack(fill='x', pady=(6, 2))
            variable = self.category if key == 'category' else self.variables[key]
            box = SearchableCombobox(body, variable, choices) if key == 'kind' else ttk.Combobox(body, textvariable=variable, values=choices, state='readonly')
            box.pack(fill='x')
            self.boxes[key] = box
            if key == 'semantics':
                wrapping_label(body, text='Mutual: shared both ways. Directional: starting character → each selected character.', style='Muted.TLabel').pack(fill='x')
                self.inverse_frame = ttk.Frame(body)
                wrapping_label(self.inverse_frame, text='Reverse label · optional (Mentor → Student)').pack(fill='x')
                self.boxes['inverse_label'] = ttk.Entry(self.inverse_frame, textvariable=self.variables['inverse_label'])
                self.boxes['inverse_label'].pack(fill='x')
                self.inverse_frame.pack(fill='x')
        self.detail_hint = tk.StringVar(self)
        wrapping_label(body, textvariable=self.detail_hint, style='Validation.TLabel').pack(fill='x', pady=4)
        self.checked_details = None
        self.detail_problem = ''
        self.timing_help = tk.StringVar(self)
        wrapping_label(body, textvariable=self.timing_help, style='Muted.TLabel').pack(fill='x')
        ttk.Button(body, text='Create an event…', command=self.create_event).pack(anchor='w', pady=4)
        ttk.Label(body, text='Notes · optional').pack(anchor='w', pady=(8, 2))
        self.notes = text_area(body, height=3)
        self.notes.pack(fill='x')
        self.notes.bind('<Control-Return>', lambda _: self.advance())
        self.notes.bind('<Tab>', lambda _: self.focus_save())
        self.review_text = read_only_text_area(self, height=12)
        self.use_selection()
        self.set_defaults()
        self.original = self.values()
        from .task_draft import TaskDraft
        self.draft = TaskDraft(self, 'task:relationship')
        if recovered:
            self.restore_draft(recovered)
        for var in (*self.variables.values(), self.category):
            var.trace_add('write', lambda *_: self.update_save())
        self.show_step(1 if self.names.get(self.variables['source'].get()) is not None else 0)
        if recovered:
            self.error.set('Draft recovered. Confirm the characters, then continue.')

    def character_names(self):
        rows = self.database.characters()
        counts = {}
        for row in rows:
            counts[row['name']] = counts.get(row['name'], 0) + 1
        return {(row['name'] if counts[row['name']] == 1 else f"{row['name']} (#{row['id']})"): row['id'] for row in rows}

    def set_defaults(self):
        self.variables['semantics'].set('Mutual')
        self.use_event()
        if not self.variables['event'].get():
            events = self.database.events.list()
            ident = events[-1]['id'] if events else None
            self.variables['event'].set(next(label for label, value in self.events.items() if value == ident))

    def show_step(self, step):
        self.step = step
        for page in self.pages:
            page.pack_forget()
        self.review_text.pack_forget()
        self.scroller.pack_forget()
        self.source_header.pack_forget()
        self.summary_label.pack_forget()
        self.heading_label.pack_forget()
        if step != 1:
            self.heading_label.pack(fill='x', pady=(4, 6), before=self.bar)
        if step == 1:
            self.source_header.pack(fill='x', pady=(0, 6))
        elif step >= 2:
            self.summary_label.pack(fill='x', pady=(0, 6))
        if step < 3:
            self.pages[step].pack(fill='both', expand=True)
            if step == 2:
                self.scroller.pack(fill='both', expand=True)
                self.scroller.canvas.yview_moveto(0)
        else:
            self.review_text.pack(fill='both', expand=True)
        self.heading.set(('Who are you connecting?', '2 of 4 · Choose connections', '3 of 4 · Relationship', '4 of 4 · Review connections')[step])
        for widget in self.navigation:
            widget.grid_forget()
        self.bar.items = self.navigation[2:] if step == 0 else self.navigation
        self.bar.reflow()
        self.back_button.configure(state='disabled' if step == 0 else 'normal')
        self.save_button.configure(text=('Continue to characters', 'Continue to relationship', 'Review connections', f'Create {len(self.targets)} connection' + ('s' if len(self.targets) != 1 else ''))[step])
        self.error.set('')
        if self.nested:
            for page in self.pages:
                page.pack_forget()
            self.source_header.pack_forget()
            self.scroller.pack_forget()
            self.review_text.pack_forget()
            self.back_button.configure(state='disabled')
            self.update_save()
            return
        self.refresh_pickers()
        self.update_save()
        if self.focus_job is not None:
            self.after_cancel(self.focus_job)
        def focus_step():
            self.focus_job = None
            target = self.boxes[('source', 'target', 'kind')[step]] if step < 3 else self.save_button
            target.focus_set()
        self.focus_job = self.after_idle(focus_step)

    def refresh_pickers(self):
        source = self.names.get(self.variables['source'].get())
        row = next((row for row in self.database.characters() if row['id'] == source), None)
        if row:
            self.source_card.display(row)
        for key in ('source', 'target'):
            self.boxes[key].refresh()
        self.show_targets()

    def source_chosen(self):
        source = self.names.get(self.variables['source'].get())
        self.targets = [ident for ident in self.targets if ident != source]
        self.reviewed = None
        self.sync_source()
        self.show_step(1)

    def toggle_target(self, ident):
        if ident == self.names.get(self.variables['source'].get()):
            return
        if ident in self.targets:
            self.targets.remove(ident)
        else:
            self.targets.append(ident)
        self.reviewed = None
        self.refresh_pickers()
        self.sync_source()
        self.update_save()

    def pick_graph_node(self, ident):
        if ident not in self.names.values():
            return
        if self.step == 0:
            self.variables['source'].set(self.label(ident))
            self.source_chosen()
        elif self.step == 1:
            self.toggle_target(ident)
        else:
            self.error.set('Use Back to change the selected characters.')

    def selection_problem(self):
        active = {row['id'] for row in self.database.characters()}
        source = self.names.get(self.variables['source'].get())
        if source not in active:
            return 'Choose a starting character.'
        if not self.targets:
            return 'Select at least one other character.'
        if source in self.targets or any(ident not in active for ident in self.targets):
            return 'Remove unavailable characters or choose a different starting character.'
        return ''

    def update_save(self):
        if not hasattr(self, 'notes'):
            return
        source = self.variables['source'].get()
        selected = ', '.join(self.label(ident) or 'Unavailable character' for ident in self.targets[:3])
        if len(self.targets) > 3:
            selected += f' and {len(self.targets) - 3} more'
        self.summary.set(f"From: {source or 'Choose below'}" + (f"\nTo: {selected or 'Choose next'}" if self.step else ''))
        valid = False if self.step == 0 else not self.selection_problem()
        if self.step >= 2:
            valid = valid and bool(self.variables['kind'].get().strip()) and self.variables['event'].get() in self.events
        if self.step == 2 and not self.nested:
            signature = repr(self.values())
            if signature != self.checked_details:
                self.checked_details = signature
                self.detail_problem = ''
                if not self.variables['kind'].get().strip():
                    self.detail_problem = 'Enter a relationship label to continue.'
                else:
                    try:
                        self.database.relationship_store.batch(*self.payload(), preview=True, category=self.category.get())
                    except (ValueError, sqlite3.Error) as error:
                        self.detail_problem = str(error)
            self.detail_hint.set(self.detail_problem)
            self.boxes['event'].state(['invalid' if 'introduced' in self.detail_problem or 'event' in self.detail_problem else '!invalid'])
            self.boxes['kind'].state(['invalid' if 'already exists' in self.detail_problem else '!invalid'])
            valid = valid and not self.detail_problem
        self.save_button.configure(state='normal' if valid and not self.nested else 'disabled')
        if self.variables['semantics'].get() == 'Directional':
            if not self.inverse_frame.winfo_manager():
                self.inverse_frame.pack(fill='x', after=self.boxes['semantics'])
        else:
            self.inverse_frame.pack_forget()
        self.timing_help.set('The connection is present from this point onward. Choose a later event for characters introduced later.')

    def advance(self):
        if self.step == 0:
            if self.names.get(self.variables['source'].get()) is None:
                self.error.set('Choose a starting character below.')
                return False
            self.show_step(1)
            return False
        if self.step == 1:
            problem = self.selection_problem()
            if problem:
                self.error.set(problem)
                return False
            self.show_step(2)
            return False
        return self.save()

    def back(self):
        if self.step:
            self.reviewed = None
            self.show_step(self.step - 1)

    def sync_source(self, *_):
        ident = self.names.get(self.variables['source'].get())
        if ident is not None and self.workspace.connecting:
            self.workspace.ordered.ids = [ident, *[target for target in self.targets if target != ident]]
            self.workspace.update_selection()

    def create_character(self, key):
        from .quick_character import QuickCharacterDialog
        def created(ident):
            source = self.names.get(self.variables['source'].get())
            self.names = self.character_names()
            if source:
                self.variables['source'].set(self.label(source))
            if key == 'source':
                self.variables['source'].set(self.label(ident))
                self.source_chosen()
            elif ident not in self.targets:
                self.targets.append(ident)
            self.refresh_pickers()
            self.sync_source()
            self.workspace.app.refresh('Character saved')
        if self.nested:
            return self.nested
        def closed():
            self.nested = None
            self.show_step(self.step)
        dialog = QuickCharacterDialog(self, self.database, created, closed, guarded=True)
        self.nested = dialog
        self.nested_key = key
        if self.focus_job is not None:
            self.after_cancel(self.focus_job)
            self.focus_job = None
        self.back_button.configure(state='disabled')
        for page in self.pages:
            page.pack_forget()
        self.source_header.pack_forget()
        self.scroller.pack_forget()
        dialog.pack(fill='both', expand=True)
        self.update_save()
        return dialog

    def create_event(self):
        from .quick_event import QuickEventDialog
        def created(ident):
            self.events.update({event_label(self.database, row): row['id'] for row in self.database.events.list()})
            self.boxes['event'].configure(values=tuple(self.events))
            self.variables['event'].set(next(label for label, value in self.events.items() if value == ident))
            self.workspace.app.refresh('Event saved')
        return QuickEventDialog(self, self.database, created)

    def draft_payload(self):
        return dict(task='relationship', values=self.values(), source_id=self.names.get(self.variables['source'].get()), event_id=self.events.get(self.variables['event'].get()), ordered=self.workspace.ordered.ids.copy(), pending_target_id=self.names.get(self.variables['target'].get()), pending_creation_field=getattr(self, 'nested_key', 'target'))

    def restore_draft(self, payload):
        values = payload['values']
        self.notes.delete('1.0', 'end')
        self.category.set(values.get('category', 'Other'))
        for key, var in self.variables.items():
            var.set(values.get(key, ''))
        source = payload.get('source_id')
        if source is not None:
            self.variables['source'].set(self.label(source) or f'Missing character #{source} · choose replacement')
        event = payload.get('event_id')
        if event is not None:
            self.variables['event'].set(next((label for label, ident in self.events.items() if ident == event), f'Missing event #{event} · choose replacement'))
        target = payload.get('pending_target_id')
        if target is not None:
            self.variables['target'].set(self.label(target) or f'Missing character #{target} · choose replacement')
        self.targets = list(dict.fromkeys(values.get('targets', [])))
        if type(target) is int and target not in self.targets and target != source:
            self.targets.append(target)
        self.variables['target'].set('')
        self.notes.insert('1.0', values.get('notes', ''))
        self.workspace.ordered.ids = [ident for ident in payload.get('ordered', []) if ident in self.names.values()]
        self.show_targets()
        if values.get('pending_creation'):
            self.create_character(payload.get('pending_creation_field', 'target')).name.set(values['pending_creation'])
        if not self.variables['semantics'].get():
            self.variables['semantics'].set('Mutual')
        self.refresh_pickers()
        self.error.set('Recovered draft · review references before saving. Missing targets must be excluded or restored.')

    def destroy(self):
        if self.focus_job is not None:
            self.after_cancel(self.focus_job)
            self.focus_job = None
        if hasattr(self, 'draft'):
            self.draft.close()
        super().destroy()

    def focus_save(self):
        self.save_button.focus_set()
        return 'break'

    def values(self):
        return {**{key: var.get() for key, var in self.variables.items()}, 'category': self.category.get(), 'targets': tuple(self.targets), 'notes': self.notes.get('1.0', 'end-1c'), 'pending_creation': self.nested.name.get() if self.nested else ''}

    def label(self, ident):
        return next((label for label, value in self.names.items() if value == ident), '')

    def show_targets(self):
        for child in self.selected_bar.winfo_children():
            child.destroy()
        if self.targets:
            self.selected_bar.pack(fill='x', pady=6)
            wrapping_label(self.selected_bar, text=f'Selected: {len(self.targets)}').pack(fill='x')
        else:
            self.selected_bar.pack_forget()
        for ident in self.targets:
            ttk.Button(self.selected_bar, text=f"{self.label(ident) or 'Unavailable character'} ×",
                       command=lambda ident=ident: self.toggle_target(ident)).pack(fill='x')

    def use_selection(self):
        ids = self.workspace.ordered.ids
        if ids:
            self.targets = list(ids[1:])
            self.variables['source'].set(self.label(ids[0]))
            self.show_targets()
        else:
            self.targets = []
            self.variables['source'].set('')
            self.show_targets()
        self.update_save()

    def use_event(self):
        ident = self.workspace.graph.as_of_id
        if ident == 0:
            self.variables['event'].set('Before first event')
        elif ident is not None:
            self.variables['event'].set(next(label for label, value in self.events.items() if value == ident))
        self.update_save()

    def payload(self):
        values = self.values()
        if self.nested:
            raise ValueError('Complete character creation or choose Back before reviewing connections.')
        source = self.names.get(values['source'])
        if source is None or not self.targets:
            raise ValueError('Choose a starting character and at least one other character.')
        if any(ident not in self.names.values() for ident in self.targets):
            raise ValueError('A selected character is missing. Remove it from the selection or restore it from Trash.')
        if values['event'] not in self.events:
            raise ValueError('Choose an effective event or explicitly choose Before first event.')
        return ([(source, target) for target in self.targets], values['kind'], values['notes'], values['semantics'].lower(),
                values['inverse_label'] if values['semantics'] == 'Directional' else '', self.events[values['event']])

    def edit(self):
        self.reviewed = None
        self.show_step(2)

    def save(self):
        try:
            payload = self.payload()
            if self.reviewed != self.values():
                self.database.relationship_store.batch(*payload, preview=True, category=self.category.get())
                values = self.values()
                arrow = '↔' if values['semantics'] == 'Mutual' else '→'
                connections = '\n'.join(f"{self.label(source)} {arrow} {self.label(target)}: {values['kind']}" for source, target in payload[0])
                text = (f"{len(self.targets)} connection{'s' if len(self.targets) != 1 else ''} to create\n\n{connections}\n\n"
                        f"{'Shared both ways' if values['semantics'] == 'Mutual' else 'From the starting character to each selected character'}\n"
                        + (f"Reverse label: {values['inverse_label']}\n" if values['semantics'] == 'Directional' and values['inverse_label'] else '')
                        + f"Category: {values['category']}\nBegins: {values['event']}"
                        + (f"\n\nNotes: {values['notes']}" if values['notes'] else ''))
                set_read_only_text(self.review_text, text)
                self.reviewed = values
                self.show_step(3)
                return False
            rows = self.database.relationship_store.batch(*payload, draft_key=self.draft.key, category=self.category.get())
        except (ValueError, sqlite3.Error) as error:
            self.show_step(1 if self.selection_problem() else 2)
            self.error.set(f'Not saved: {error}')
            return False
        self.draft.discard()
        self.category.set('Other')
        self.workspace.connecting = True
        for variable in self.variables.values():
            variable.set('')
        self.targets.clear()
        self.show_targets()
        self.notes.delete('1.0', 'end')
        self.notes.edit_reset()
        for key in ('source', 'target'):
            self.boxes[key].query.set('')
        self.workspace.clear_selection()
        self.set_defaults()
        self.show_step(0)
        self.original = self.values()
        self.draft.discarded = False
        self.draft.last = self.values()
        self.draft.tick()
        self.workspace.app.refresh(f'Saved all {len(rows)} connections.')
        self.error.set(f'{len(rows)} connections added')
        self.boxes['source'].focus_set()
        return True
