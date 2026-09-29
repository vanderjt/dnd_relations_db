"""Graph-centered presentation; all writes use the shared domain services."""
import tkinter as tk
import sqlite3
from tkinter import ttk, messagebox
from .selection import OrderedSelection
from .simple_graph import SimpleGraph
from .simple_timeline import Timeline
from .simple_profile import SimpleProfile
from .simple_summary import CharacterSummary
from .task_prompt import save_discard_stay
from .simple_batch import BatchPane
from .simple_event import EventPane
from .state_editor import StateEditor
from .widgets import ActionBar, wrapping_label
from .theme import style_tree


class SimpleWorkspace(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.database = app, app.database
        self.database_path = self.database.path
        self.ordered = OrderedSelection()
        self.provisional = False
        self.connecting = False
        self.task = None
        self.recent_creation = None
        self.context = tk.StringVar(self)
        wrapping_label(self, textvariable=self.context, style='Context.TLabel').pack(fill='x', padx=12)
        self.ribbon = ribbon = ActionBar(self)
        ribbon.pack(fill='x', padx=12)
        ribbon.add(ttk.Button(ribbon, text='New character', command=self.new_character))
        self.add_button = ribbon.add(ttk.Button(ribbon, text='Add relationship', command=self.new_relationship))
        ribbon.add(ttk.Button(ribbon, text='New event', command=self.new_event))
        ribbon.add(ttk.Button(ribbon, text='Next event', command=self.continue_event))
        self.graph = SimpleGraph(self, self)
        menu_button = ttk.Menubutton(ribbon, text='More')
        menu = tk.Menu(menu_button, tearoff=False)
        menu.add_command(label='New chapter', command=lambda: self.new_event(True))
        menu.add_command(label='Fit view', command=self.graph.fit_graph)
        menu.add_checkbutton(label='Show planned cast', variable=self.graph.show_planned, command=lambda: self.graph.refresh(force=True))
        menu.add_cascade(label='Graph filters', menu=self.graph.filter_menu)
        menu.add_command(label='Undo recent character creation', command=self.undo_creation)
        menu.add_command(label='Edit selected event', command=self.edit_event)
        menu.add_command(label='Collapse / show information pane', command=self.toggle_pane)
        menu.add_command(label='Zoom rectangle', command=lambda: self.graph.controls.toggle('zoom'))
        menu.add_command(label='Pan tool', command=lambda: self.graph.controls.toggle('pan'))
        menu.add_command(label='Export displayed graph…', command=self.graph.export)
        menu.add_command(label='Saved graph views…', command=self.graph.saved_views)
        menu.add_command(label='Remove event and reassign references…', command=self.remove_event)
        menu_button.configure(menu=menu)
        ribbon.add(menu_button)
        from .character_type import TYPE_COLORS as COLORS
        self.classification_legend = legend = ttk.Menubutton(ribbon, text='Legend · dots & links ▾')
        legend_menu = tk.Menu(legend, tearoff=False)
        def filter_classification(value):
            self.graph.classification_filter = value
            legend.configure(text=f'Legend · {value or "dots & links"} ▾')
            self.graph.refresh(force=True)
        legend_menu.add_command(label='Show all character types', command=lambda: filter_classification(None))
        legend_menu.add_command(label='DOTS · current character type (click to filter)', state='disabled')
        for label, color in COLORS.items():
            legend_menu.add_command(label='● ' + label, foreground=color, command=lambda label=label: filter_classification(label))
        from .graph_legend import add_menu_explanations
        add_menu_explanations(legend_menu)
        legend.configure(menu=legend_menu)
        ribbon.add(legend)
        self.ribbon_full = ribbon.items.copy()
        self.ribbon_compact = self.ribbon_full
        self.compact = None
        self.bind('<Configure>', self.adapt_layout)
        self.timeline = Timeline(self, self)
        self.timeline.pack(side='bottom', fill='x', padx=12)
        self.graph.pack(fill='both', expand=True)
        self.graph.body.forget(self.graph.inspector)
        self.side = ttk.Frame(self.graph.body)
        self.graph.body.add(self.side, weight=1)
        self.selection_controls = ttk.Frame(self.side)
        self.selection_toggle = ttk.Button(self.side, text='Character selection controls ▸', command=self.toggle_selection_controls)
        self.selection_toggle.pack(fill='x')
        self.cast = tk.StringVar(self)
        self.cast_box = ttk.Combobox(self.selection_controls, textvariable=self.cast, state='readonly')
        self.cast_box.pack(fill='x')
        actions = ActionBar(self.selection_controls)
        actions.pack(fill='x')
        actions.add(ttk.Button(actions, text='Inspect', command=self.inspect_chosen))
        actions.add(ttk.Button(actions, text='Select / remove', command=self.select_chosen))
        actions.add(ttk.Button(actions, text='Make source', command=self.make_source))
        actions.add(ttk.Button(actions, text='Clear selection', command=self.clear_selection))
        self.connection_choice = tk.StringVar(self)
        self.connection_box = ttk.Combobox(self.selection_controls, textvariable=self.connection_choice, state='readonly')
        self.connection_box.pack(fill='x')
        ttk.Button(self.selection_controls, text='Inspect saved connection (including ended)', command=self.inspect_saved_connection).pack(fill='x')
        self.selection_text = tk.StringVar(self)
        self.selection_label = wrapping_label(self.side, textvariable=self.selection_text, style='Context.TLabel')
        from .scroll_frame import ScrollFrame
        self.selection_scroll = ScrollFrame(self.side)
        self.selection_scroll.canvas.configure(height=80)
        self.selection_chips = ActionBar(self.selection_scroll.content)
        self.selection_chips.pack(fill='x')
        self.host = ttk.Frame(self.side)
        self.host.pack(fill='both', expand=True)
        self.graph.inspector.destroy()
        from .graph_inspector import GraphInspector
        graph = self.graph
        graph.inspector = GraphInspector(self.host, graph.select_edge, graph.open_profile, graph.toggle_pin, graph.focus_node,
                                         graph.edit_relationship, graph.record_story_change, graph.view_relationship_history)
        graph.inspector.pack(fill='both', expand=True)
        graph.inspector.record_button.configure(text='Change at this event')
        graph.inspector.relationship_bar.add(ttk.Button(graph.inspector.relationship_bar, text='Move connection to Trash', command=self.trash_connection))
        self.refresh()

    def adapt_layout(self, _event=None):
        if not hasattr(self, 'host'):
            return
        import tkinter.font as font
        compact = self.winfo_width() < 1050 or font.nametofont('TkDefaultFont').metrics('linespace') > 24
        if compact == self.compact:
            return
        self.compact = compact
        for widget in self.ribbon_full:
            widget.grid_forget()
        self.ribbon.items = self.ribbon_compact if compact else self.ribbon_full
        self.ribbon.reflow()
        self.selection_toggle.pack_forget()
        self.selection_toggle.pack(fill='x', before=self.host)
        self.timeline.compact_layout(compact)
        self.refresh()

    def toggle_selection_controls(self):
        if self.selection_controls.winfo_manager():
            self.selection_controls.pack_forget()
        else:
            self.selection_controls.pack(fill='x', before=self.host)

    def refresh(self):
        if self.database.path != self.database_path:
            self.remove_task()
            self.ordered.clear()
            self.cast.set('')
            self.connection_choice.set('')
            self.provisional = False
            self.database_path = self.database.path
            self.graph.database = self.database
            self.graph.classification_filter = None
        self.classification_legend.configure(text=f'Legend · {self.graph.classification_filter or "dots & links"} ▾')
        self.graph.invalidate()
        self.cast_choices = {f"{row['name']} (#{row['id']})": row['id'] for row in self.database.characters()}
        self.cast_box.configure(values=tuple(self.cast_choices))
        self.connection_choices = {f"#{row['id']} · {row['source_name']} / {row['target_name']}": row['id'] for row in self.database.relationship_records()}
        self.connection_box.configure(values=tuple(self.connection_choices))
        if self.cast.get() not in self.cast_choices:
            self.cast.set('Choose character · keyboard selection' if self.cast_choices else 'No characters yet · use New character')
        self.ordered.ids = [ident for ident in self.ordered.ids if ident in self.cast_choices.values()]
        self.timeline.refresh()
        title = self.database.connection.execute("SELECT value FROM story_metadata WHERE key='title'").fetchone()
        title = title[0] if title else self.database.path.stem
        self.context.set(title[:32] if self.compact else f"{title} · {self.timeline.chapter.get()} · {self.timeline.event.get()}")
        self.update_selection()

    def update_selection(self):
        names = {row['id']: row['name'] for row in self.database.characters()}
        self.selection_label.pack_forget()
        if self.connecting:
            self.selection_label.pack(fill='x', before=self.host)
        self.selection_text.set('\n'.join(f"{'Source' if i == 0 else 'Target'}: {names.get(ident, '')} (#{ident})" for i, ident in enumerate(self.ordered.ids)))
        self.graph.renderer.ordered_selection = self.ordered.ids.copy()
        self.graph.renderer.highlight(self.graph.selection)
        self.graph.canvas.draw_idle()
        for child in self.selection_chips.winfo_children():
            child.destroy()
        self.selection_chips.items.clear()
        if isinstance(self.task, BatchPane):
            self.selection_scroll.pack_forget()
            self.selection_label.pack_forget()
            self.selection_controls.pack_forget()
            self.selection_toggle.pack_forget()
            return
        if not self.selection_toggle.winfo_manager():
            self.selection_toggle.pack(fill='x', before=self.host)
        if self.connecting:
            if self.compact and isinstance(self.task, BatchPane):
                body = self.task.scroller.content
                self.selection_scroll.pack(in_=body, fill='x')
            else:
                self.selection_scroll.pack(in_=self.side, fill='x', before=self.host)
            source = names.get(self.ordered.ids[0], '') if self.ordered.ids else ''
            self.selection_text.set(f'Connect {source or "a character"} to…')
            for ident in self.ordered.ids:
                self.selection_chips.add(ttk.Button(self.selection_chips, text=f'{names.get(ident)} ×', command=lambda ident=ident: self.choose_node(ident, True)))
                self.selection_chips.add(ttk.Button(self.selection_chips, text='Make source', command=lambda ident=ident: self.set_source(ident)))
            self.selection_chips.add(ttk.Button(self.selection_chips, text='Exit selection', command=self.exit_connect))
        else:
            self.selection_scroll.pack_forget()

    def can_leave(self):
        task = self.task
        if task is None or task.values() == task.original:
            return True
        answer = save_discard_stay(self)
        if answer is None:
            return False
        if answer:
            # Review tasks deliberately remain until their reviewed Save succeeds.
            return task.save()
        if hasattr(task, 'draft'):
            task.draft.discard()
        return True

    def remove_task(self):
        self.selection_scroll.pack_forget()
        self.selection_label.pack_forget()
        self.connecting = False
        if self.task is not None:
            self.task.destroy()
            self.task = None
        if self.provisional:
            self.provisional = False
            self.graph.positions.pop(-1, None)
            self.graph.pins.discard(-1)
        self.graph.inspector.pack(in_=self.host, fill='both', expand=True)
        self.update_selection()

    def close_task(self):
        if self.can_leave():
            self.remove_task()
            self.graph.refresh(force=True)
            return True
        return False

    def cancel_task(self):
        if self.task and self.task.values() != self.task.original:
            if not messagebox.askyesno('Discard edits', 'Discard this task’s uncommitted input? Saved records remain saved.', parent=self):
                return False
        if self.task and hasattr(self.task, 'draft'):
            self.task.draft.discard()
        self.remove_task()
        self.graph.refresh(force=True)
        return True

    def mount(self, factory):
        if not self.close_task():
            return None
        self.show_pane()
        self.graph.inspector.pack_forget()
        self.task = factory()
        self.task.pack(fill='both', expand=True)
        style_tree(self.side)
        return self.task

    def new_character(self):
        recovered = next((row['values'] for row in self.database.drafts.list() if row['key'] == 'new'), None)
        if recovered and not messagebox.askyesno('Recover character draft', 'Resume the existing unsaved new-character draft?', parent=self):
            return
        task = self.mount(lambda: SimpleProfile(self.host, self, recovered=recovered))
        if task:
            self.provisional = True
            axes = self.graph.renderer.axes
            from .node_placement import free_position, reveal_position
            self.graph.positions[-1] = free_position(self.graph.positions, axes.get_xlim(), axes.get_ylim(), (axes.bbox.width, axes.bbox.height))
            reveal_position(axes, self.graph.positions[-1])
            self.graph.refresh(force=True)

    def character_saved(self, ident, creating):
        if creating:
            from .recent_undo import RecentCreation
            self.recent_creation = RecentCreation(self.database, ident)
            point = self.graph.positions.pop(-1, None)
            if point is not None:
                self.graph.positions[ident] = point
            if -1 in self.graph.pins:
                self.graph.pins.remove(-1)
                self.graph.pins.add(ident)
            self.provisional = False
        self.graph.selection = ('node', ident)
        self.app.refresh('Character and introduction saved.')

    def undo_creation(self):
        if not self.recent_creation or self.recent_creation.database.path != self.database.path:
            self.app.status.set('No recent character creation to undo.')
            return False
        if not self.close_task():
            return False
        try:
            self.recent_creation.undo()
        except ValueError as error:
            self.app.status.set(str(error))
            return False
        self.recent_creation = None
        self.app.refresh('Creation undone · character is in Trash and can be restored.')
        return True

    def inspect_character(self, ident, origin=None):
        row = next((row for row in self.database.characters() if row['id'] == ident), None)
        if row is None:
            return False
        if isinstance(self.task, SimpleProfile) and self.task.character_id == ident:
            return True
        return self.mount(lambda: CharacterSummary(self.host, self, row)) is not None

    def edit_character(self, ident):
        row = next((row for row in self.database.characters() if row['id'] == ident), None)
        return self.mount(lambda: SimpleProfile(self.host, self, row)) if row else None

    def trash_character(self, ident):
        if not isinstance(self.task, CharacterSummary) or self.task.character_id != ident:
            return False
        row = next((row for row in self.database.characters() if row['id'] == ident), None)
        if row is None:
            return False
        connections = sum(ident in (r['source_id'], r['target_id']) for r in self.database.relationship_records())
        if not messagebox.askyesno('Move character to Trash',
                f"Move {row['name']} and all {connections} attached connections to Trash? "
                'They will disappear from the graph and can be restored from Maintenance → Recovery.', parent=self):
            return False
        try:
            self.database.delete_character(ident)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror('Cannot move character to Trash', str(error), parent=self)
            return False
        self.remove_task()
        self.clear_selection()
        self.cast.set('')
        self.connection_choice.set('')
        self.recent_creation = None
        self.app.refresh(f"{row['name']} and {connections} connections moved to Trash. Restore them from Maintenance → Recovery.")
        return True

    def connect(self, ident):
        if not self.close_task():
            return
        self.ordered.select(ident, False)
        task = self.new_relationship()
        if task:
            task.variables['source'].set(task.label(ident))
            task.source_chosen()
        self.connecting = True
        self.update_selection()

    def exit_connect(self):
        self.connecting = False
        self.update_selection()

    def set_source(self, ident):
        self.ordered.source(ident)
        if isinstance(self.task, BatchPane):
            self.task.use_selection()
        self.update_selection()

    def choose_node(self, ident, extend=False):
        if self.connecting and isinstance(self.task, BatchPane):
            self.task.pick_graph_node(ident)
            self.update_selection()
            return True
        if not extend and not self.inspect_character(ident):
            return False
        self.ordered.select(ident, extend)
        self.update_selection()
        return True

    def inspect_chosen(self):
        ident = self.cast_choices.get(self.cast.get())
        if ident:
            self.graph.select_node(ident)

    def select_chosen(self):
        ident = self.cast_choices.get(self.cast.get())
        if ident:
            self.choose_node(ident, True)

    def make_source(self):
        ident = self.cast_choices.get(self.cast.get())
        if ident is None and self.graph.selection and self.graph.selection[0] == 'node':
            ident = self.graph.selection[1]
        self.set_source(ident)

    def clear_selection(self):
        self.ordered.clear()
        self.graph.selection = None
        self.update_selection()

    def new_relationship(self):
        if not self.close_task():
            return None
        recovered = next((r['values'] for r in self.database.drafts.list() if r['key'] == 'task:relationship'), None)
        task = self.mount(lambda: BatchPane(self.host, self, recovered))
        if task:
            self.connecting = True
            self.update_selection()
        return task

    def inspect_saved_connection(self):
        ident = self.connection_choices.get(self.connection_choice.get())
        if ident:
            self.graph.select_edge(ident)

    def trash_connection(self):
        selection = self.graph.selection
        if selection and selection[0] == 'edge' and messagebox.askyesno('Move connection to Trash', 'Move this entire connection and its history to Trash? Ending a relationship instead records a story change.', parent=self):
            self.database.delete_relationship(selection[1])
            self.app.refresh('Connection moved to Trash. Restore it from Recovery.')

    def inspect_edge(self, ident):
        if not self.close_task():
            return False
        self.show_pane()
        return True

    def state_task(self, ident, correction):
        event = self.graph.as_of_id
        if not correction and event in (None, 0):
            messagebox.showinfo('Choose effective event', 'Select a dated event in the timeline before recording a change.', parent=self)
            return
        row = self.database.history.editing_state(ident, event)
        if not correction and any(state['event_id'] == event for state in self.database.history.rows(ident)):
            if not messagebox.askyesno('State already exists', 'This connection already has a state here. Correct that exact entry?', parent=self):
                return
            correction = True
        if not correction:
            row = self.database.history.state_before(ident, event)
        from .simple_state import SimpleStateEditor
        fixed = row.get('event_id') if correction else event
        key = f'task:state:{ident}:{fixed}:{correction}'
        recovered = next((item['values'] for item in self.database.drafts.list() if item['key'] == key), None)
        return self.mount(lambda: SimpleStateEditor(self.host, self, ident, recovered['row'] if recovered else row, correction, fixed, recovered))

    def new_event(self, chapter=False):
        if not self.close_task():
            return None
        key = 'task:event:chapter' if chapter else 'task:event:new'
        recovered = next((r['values'] for r in self.database.drafts.list() if r['key'] == key), None)
        return self.mount(lambda: EventPane(self.host, self, chapter, recovered=recovered))

    def edit_event(self):
        row = next((row for row in self.database.events.list() if row['id'] == self.graph.as_of_id), None)
        if row:
            return self.mount(lambda: EventPane(self.host, self, row=row))

    def remove_event(self):
        if self.graph.as_of_id not in (None, 0):
            from .event_reassignment import EventReassignment
            return self.mount(lambda: EventReassignment(self.host, self))

    def event_saved(self, ident):
        self.graph.as_of_id = ident
        self.app.refresh('Event committed. Introduce characters or record changes; this event remains editable.')
        self.remove_task()

    def continue_event(self):
        if not self.close_task():
            return
        ids = self.timeline.ids
        index = ids.index(self.graph.as_of_id)
        if index + 1 < len(ids) and ids[index + 1] is not None:
            self.navigate(ids[index + 1])
        else:
            self.new_event()

    def navigate(self, ident):
        if not self.close_task():
            self.timeline.preview_index = None
            self.timeline.refresh()
            return False
        self.graph.as_of_id = ident
        self.graph.refresh(force=True)
        self.refresh()
        return True

    def show_pane(self):
        if str(self.side) not in self.graph.body.panes():
            self.graph.body.add(self.side, weight=1)

    def toggle_pane(self):
        if str(self.side) in self.graph.body.panes():
            if self.close_task():
                self.graph.body.forget(self.side)
        else:
            self.show_pane()

    def escape(self):
        if self.task is not None:
            self.close_task()
        else:
            self.clear_selection()

    def destroy(self):
        if self.task and hasattr(self.task, 'draft'):
            self.task.draft.cancel()
        super().destroy()
