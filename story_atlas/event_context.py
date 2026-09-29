"""Event workspace reading actions and navigation snapshots."""
from tkinter import ttk
from .event_detail_state import capture, restore
from .widgets import read_only_text_area, set_read_only_text
from .reading_text import use_outer_scroll


class EventContext:
    def setup_reading(self):
        self.navigation_collapsed = False
        self.expand_button = self.actions.add(ttk.Button(self.actions, text='Expand details', command=self.toggle_navigation))
        self.goal_detail = read_only_text_area(self.goals_section, height=5)
        self.goal_detail.pack(fill='x')
        self.edit_goals_button = ttk.Button(self.goals_section, text='Edit current goals', command=self.edit_current_goals)
        self.edit_goals_button.pack(anchor='w', pady=4)
        self.change_detail = read_only_text_area(self.changes_section, height=5)
        self.change_detail.pack(fill='x', pady=4)
        for widget in (self.detail_body, self.cast_body, self.goal_detail, self.change_detail):
            use_outer_scroll(widget)
        self.goals_tree.bind('<<TreeviewSelect>>', self.read_goal)
        self.change_tree.bind('<<TreeviewSelect>>', self.read_change)
        for tree in (self.goals_tree, self.change_tree):
            tree.configure(height=4)
            tree.column('#0', minwidth=40, stretch=True)
            # Full prose is available in the wrapping, copyable detail surface.
            for child in tree.master.grid_slaves(row=1):
                child.grid_remove()
        set_read_only_text(self.goal_detail, 'Select a character to read current saved goals. Goals are not historically versioned.')
        set_read_only_text(self.change_detail, 'Select a change to read its full saved notes.')

    def toggle_navigation(self):
        if self.navigation_collapsed:
            self.workspace.insert(0, self.outline_frame, weight=1)
            self.workspace.insert(1, self.event_frame, weight=2)
            self.expand_button.configure(text='Expand details')
        else:
            self._navigation_sashes = [self.workspace.sashpos(i) for i in (0, 1)]
            self.workspace.forget(self.outline_frame)
            self.workspace.forget(self.event_frame)
            self.expand_button.configure(text='Show chapters and events')
        self.navigation_collapsed = not self.navigation_collapsed
        if not self.navigation_collapsed:
            for i, value in enumerate(getattr(self, '_navigation_sashes', [])):
                self.workspace.sashpos(i, value)

    def selected_goal_id(self):
        selection = self.goals_tree.selection()
        return int(selection[0].split(':')[1]) if selection and selection[0].startswith('character:') else None

    def read_goal(self, _event=None):
        ident = self.selected_goal_id()
        row = self.database.connection.execute('SELECT * FROM characters WHERE id=?', (ident,)).fetchone()
        if row:
            set_read_only_text(self.goal_detail, f"Current goals · {row['name']} (#{ident})" + (' [Trash]' if row['deleted_at'] else '') + f"\n{row['goals'] or 'No saved goals.'}")
        else:
            set_read_only_text(self.goal_detail, 'Select a character to read current saved goals. Goals are not historically versioned.')
        self.edit_goals_button.state(['!disabled' if row and not row['deleted_at'] else 'disabled'])

    def read_change(self, _event=None):
        selection = self.change_tree.selection()
        parts = selection[0].split(':') if selection else []
        ident = int(parts[3]) if len(parts) >= 4 and parts[2] == 'change' else None
        row = next((row for row in self.database.history.rows() if row['id'] == ident), None)
        if row:
            set_read_only_text(self.change_detail, f"{'Active from this event' if row['active'] else 'Ends at this event'} · {row['kind']}\n{row['notes'] or 'No notes.'}")
        else:
            set_read_only_text(self.change_detail, 'Select a change to read its full saved notes.')

    def edit_current_goals(self):
        ident = self.selected_goal_id()
        if ident is not None:
            return self.winfo_toplevel().navigation.open_goals_from_event(ident)
        return False

    def highlight_change(self, relationship_id):
        event_id = int(self.tree.selection()[0]) if self.tree.selection() else None
        row = next((row for row in self.database.history.rows(relationship_id) if row['event_id'] == event_id), None)
        if row:
            key = f"character:{row['source_id']}:change:{row['id']}"
            self.change_tree.selection_set(key)
            self.change_tree.focus(key)
            self.change_tree.see(key)
            self.read_change()

    def capture_context(self):
        trees = (self.outline, self.tree, self.goals_tree, self.change_tree)
        return dict(chapter=self.chapter_id, selection=self.tree.selection(), trees=[capture(tree) for tree in trees],
                    scroll=self.detail_scroller.canvas.yview()[0], collapsed=self.navigation_collapsed,
                    sashes=[] if self.navigation_collapsed else [self.workspace.sashpos(i) for i in (0, 1)],
                    text_scroll=[widget.yview()[0] for widget in (self.detail_body, self.cast_body, self.goal_detail, self.change_detail)])

    def restore_context(self, state):
        self.restore_selection(state['chapter'], state['selection'])
        if self.navigation_collapsed != state['collapsed']:
            self.toggle_navigation()
        for i, value in enumerate(state['sashes']):
            self.workspace.sashpos(i, value)
        for tree, saved in zip((self.outline, self.tree, self.goals_tree, self.change_tree), state['trees']):
            restore(tree, saved)
        self.read_goal()
        self.read_change()
        self.update_idletasks()
        self.detail_scroller.canvas.yview_moveto(state['scroll'])
        for widget, scroll in zip((self.detail_body, self.cast_body, self.goal_detail, self.change_detail), state['text_scroll']):
            widget.yview_moveto(scroll)
