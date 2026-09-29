"""Inspection reads saved records without mounting an editable draft."""
from tkinter import ttk
from .widgets import ActionBar, wrapping_label
from .scroll_frame import ScrollFrame
from .relationship_semantics import perspectives


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
        scroll = ScrollFrame(self)
        scroll.pack(fill='both', expand=True)
        body = scroll.content
        wrapping_label(body, text=row['name'], style='Heading.TLabel').pack(fill='x')
        wrapping_label(body, text=f"{row['character_type']} · current character type", style='Context.TLabel').pack(fill='x')
        wrapping_label(body, text='Profile and goals describe Current, including when viewing earlier events.', style='Muted.TLabel').pack(fill='x')
        for key in ('role', 'species', 'status', 'faction', 'location', 'tags', 'summary', 'goals'):
            if row.get(key):
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
