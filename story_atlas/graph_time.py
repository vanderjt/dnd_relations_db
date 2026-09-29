"""Time navigation is independent of focus, filters, and presentation."""
import tkinter as tk
from tkinter import ttk
from .graph_render import EDGE_STYLES


CURRENT_SCOPE = 'Current — after the last event'


class GraphTime:
    def setup_time(self):
        self.highlight_changes = tk.BooleanVar(self, False)
        self.changes_only = tk.BooleanVar(self, False)
        self.visual_categories = {}
        self.previous_button = self.filters.add(ttk.Button(self.filters, text='← Previous', command=lambda: self.step_event(-1)))
        self.next_button = self.filters.add(ttk.Button(self.filters, text='Next →', command=lambda: self.step_event(1)))

    def step_event(self, offset):
        timeline = [0, *[row['id'] for row in self.database.events.list()], None]
        index = timeline.index(self.as_of_id)
        destination = index + offset
        if 0 <= destination < len(timeline):
            self.as_of_id = timeline[destination]
            self.refresh(force=True)

    def clear_filters(self):
        self.kind.set('All types')
        self.direction.set('Both')
        self.isolates.set(True)
        self.changes_only.set(False)
        self.refresh(force=True)

    def event_changes(self):
        names = {row['id']: row['name'] for row in self.database.characters()}
        records = {row['id'] for row in self.database.relationship_records()}
        return [dict(row, id=row['relationship_id'], history_state_id=row['id'],
                     source_name=names[row['source_id']], target_name=names[row['target_id']],
                     ended_here=not row['active'])
                for row in self.database.history.rows() if row['event_id'] == self.as_of_id
                and row['relationship_id'] in records and row['source_id'] in names and row['target_id'] in names]

    def displayed_scope(self):
        prefix = 'Planned cast shown (dashed; no future connections) · ' if self.show_planned.get() else ''
        return prefix + ('Changes only at event (including endings)' if self.changes_only.get() else 'Full historical graph' if self.as_of_id is not None else 'Current graph')

    def add_time_menu(self, kinds):
        self.filter_menu.add_checkbutton(label='Highlight changes at selected event', variable=self.highlight_changes,
                                         command=lambda: self.refresh(force=True))
        self.filter_menu.add_command(label='Clear filters · keep time and focus', command=self.clear_filters)
        self.filter_menu.add_checkbutton(label='Changes only at selected event (includes endings)', variable=self.changes_only,
                                         command=lambda: self.refresh(force=True))
        categories = tk.Menu(self.filter_menu, tearoff=False)
        for kind in kinds:
            if kind == 'All types':
                continue
            submenu = tk.Menu(categories, tearoff=False)
            for category in EDGE_STYLES:
                submenu.add_command(label=f"{'✓ ' if self.visual_categories.get(kind, 'Other') == category else ''}{category}",
                    command=lambda kind=kind, category=category: self.set_visual_category(kind, category))
            categories.add_cascade(label=kind, menu=submenu)
        self.filter_menu.add_cascade(label='Legacy category defaults · uncategorized connections', menu=categories)

    def set_visual_category(self, kind, category):
        self.visual_categories[kind] = category
        self.refresh(force=True)
