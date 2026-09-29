"""Inspection reads saved records without mounting an editable draft."""
from tkinter import ttk
from .widgets import ActionBar, wrapping_label
from .scroll_frame import ScrollFrame
from .relationship_semantics import perspectives
from .illustrated_widgets import IdentityHeader, IllustratedLabel


class CharacterSummary(ttk.Frame):
    def __init__(self, parent, workspace, row):
        super().__init__(parent)
        self.character_id = row['id']
        self.original = {}
        bar = ActionBar(self)
        bar.pack(side='bottom', fill='x')
        bar.add(ttk.Button(bar, text='Edit character', command=lambda: workspace.edit_character(row['id'])))
        bar.add(ttk.Button(bar, text='Connect…', command=lambda: workspace.connect(row['id'])))
        self.delete_button = bar.add(ttk.Button(bar, text='Delete', style='Danger.TButton',
                                                command=lambda: workspace.trash_character(row['id'])))
        # A short task pane must reserve height for the saved profile itself.
        import tkinter as tk
        full_actions = list(bar.items)
        actions = ttk.Menubutton(bar, text='Actions')
        menu = tk.Menu(actions, tearoff=False)
        menu.add_command(label='Connect…', command=lambda: workspace.connect(row['id']))
        menu.add_command(label='Delete character…', command=lambda: workspace.trash_character(row['id']))
        actions.configure(menu=menu)
        def adapt(_event=None):
            short = self._root().winfo_height() < 540
            if short == getattr(self, '_short', None):
                return
            self._short = short
            for control in [*full_actions, actions]:
                control.grid_forget()
            full_actions[0].configure(text='Edit' if short else 'Edit character')
            bar.items = [full_actions[0], actions] if short else list(full_actions)
            bar.reflow()
        self.bind('<Configure>', adapt, add='+')
        scroll = ScrollFrame(self)
        scroll.pack(fill='both', expand=True)
        body = scroll.content
        self.identity = IdentityHeader(body)
        self.identity.pack(fill='x')
        self.identity.name.configure(text=row['name'])
        self.identity.details.configure(text=f"{row['character_type']} · current character type")
        self.identity.show_portrait(workspace.database.assets, row.get('portrait', ''))
        wrapping_label(body, text='Profile and goals describe Current, including when viewing earlier events.', style='Muted.TLabel').pack(fill='x')
        for key in ('role', 'species', 'status', 'faction', 'location', 'tags', 'summary', 'goals'):
            if row.get(key):
                if key in ('summary', 'goals'):
                    IllustratedLabel(body, 'section.story' if key == 'summary' else 'section.goals', text=key.title()).pack(fill='x', pady=(8, 2))
                    wrapping_label(body, text=row[key]).pack(fill='x', pady=4)
                else:
                    wrapping_label(body, text=f"{key.title()}: {row[key]}").pack(fill='x', pady=4)
        ttk.Label(body, text='Connections at selected time', style='Heading.TLabel').pack(anchor='w', pady=8)
        records = [r for r in workspace.database.relationship_records() if row['id'] in (r['source_id'], r['target_id'])]
        if not records:
            wrapping_label(body, text='No connections yet. Choose Connect… to add one.').pack(fill='x')
        names = {r['id']: r['name'] for r in workspace.database.characters()}
        for record in records:
            state = workspace.database.history.editing_state(record['id'], workspace.graph.as_of_id)
            label = perspectives(names[state['source_id']], names[state['target_id']], state['kind'], state['semantics'], state['inverse_label'])
            wrapping_label(body, text=label + ('' if state['active'] else ' · Not active at this time')).pack(fill='x', pady=4)
            ttk.Button(body, text=f"Inspect connection #{record['id']}", command=lambda ident=record['id']: workspace.graph.select_edge(ident)).pack(anchor='w')

    def values(self):
        return {}

    def save(self):
        return True
