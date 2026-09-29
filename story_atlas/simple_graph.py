"""Simple graph gestures layered on the existing renderer and graph services."""
from .graph_view import GraphView


class SimpleGraph(GraphView):
    def refresh(self, *args, **kwargs):
        result = super().refresh(*args, **kwargs)
        if hasattr(self.workspace, 'graph'):
            self.workspace.refresh_context()
        return result

    def __init__(self, parent, workspace):
        self.workspace = workspace
        self.classification_filter = None
        super().__init__(parent, workspace.database, workspace.app.refresh, workspace.inspect_character)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.pan_start = None
        # Simple mode time controls live in the context bar and bottom timeline.
        self.filters.master.pack_forget()
        self.controls.master.pack_forget()
        self.summary.pack_forget()
        self.winfo_children()[0].pack_forget()
        self.canvas.get_tk_widget().configure(takefocus=True)
        for key, dx, dy in (('Left', -.05, 0), ('Right', .05, 0), ('Up', 0, .05), ('Down', 0, -.05)):
            self.canvas.get_tk_widget().bind(f'<{key}>', lambda _, dx=dx, dy=dy: self.keyboard_move(dx, dy))

    def keyboard_move(self, dx, dy):
        if self.selection and self.selection[0] == 'node' and self.selection[1] in self.graph:
            before = self.capture_state()
            node = self.selection[1]
            x, y = self.positions[node]
            self.renderer.move_node(node, (x + dx, y + dy))
            self.pins.add(node)
            self.renderer.highlight(self.selection)
            self.canvas.draw_idle()
            self.record_graph_change(before)
        return 'break'

    def displayed_scope(self):
        scope = super().displayed_scope()
        return scope + (f' · Character type: {self.classification_filter} (current)' if self.classification_filter else ' · Character types are current')

    def export(self):
        if self.workspace.close_task():
            return super().export()

    def saved_views(self):
        if self.workspace.close_task():
            return super().saved_views()

    def apply_state(self, state):
        if self.workspace.close_task():
            super().apply_state(state)
            self.workspace.refresh()

    def size_inspector(self, _event=None):
        if not self._inspector_restored:
            self._inspector_width = 380
            self._inspector_restored = True
        super().size_inspector(_event)

    def graph_characters(self):
        rows = super().graph_characters()
        if self.classification_filter:
            rows = [row for row in rows if self.classification_filter in row.get('character_type', row.get('classification', 'Neutral')).split(' · ')]
        if self.workspace.provisional:
            rows.append(dict(id=-1, name='New character', narrative_role='neutral', provisional=True))
        return rows

    def event_changed(self, _event=None):
        self.workspace.navigate(self.event_choices.get(self.as_of.get()))

    def step_event(self, offset):
        self.workspace.timeline.step(offset)

    def select_node(self, node, extend=False):
        if node == -1:
            return
        if not self.workspace.choose_node(node, extend):
            return
        super().select_node(node)

    def select_edge(self, ident):
        if self.workspace.inspect_edge(ident):
            super().select_edge(ident)
            if ident not in self.renderer.edge_artists:
                state = self.database.history.editing_state(ident, self.as_of_id)
                from .relationship_semantics import perspectives
                names = {row['id']: row['name'] for row in self.database.characters()}
                self.inspector.heading.configure(text=f"Connection #{ident} · {self.as_of.get()}")
                self.inspector.set_details(('Present (outside filters)' if state['active'] else 'Not active at this time') + '\n' + perspectives(names[state['source_id']], names[state['target_id']], state['kind'], state['semantics'], state['inverse_label']) + '\n' + state['notes'])

    def edit_relationship(self, ident, launch_control=None):
        return self.workspace.state_task(ident, True)

    def record_story_change(self, ident, launch_control=None):
        return self.workspace.state_task(ident, False)

    def on_click(self, event):
        if event.inaxes is not self.renderer.axes or event.button != 1 or self.toolbar.mode:
            return
        node = self.renderer.pick_node(event)
        if node is not None:
            shift = 'shift' in (event.key or '')
            self.select_node(node, shift)
            if not shift and not self.workspace.connecting:
                self.drag = dict(node=node, start=(event.x, event.y), moved=False, before=self.capture_state())
        else:
            edge = self.renderer.pick_edge(event)
            if edge is not None:
                self.select_edge(edge)
            else:
                self.pan_start = (event.x, event.y, self.renderer.axes.get_xlim(), self.renderer.axes.get_ylim())

    def on_motion(self, event):
        if self.pan_start:
            x, y, xlim, ylim = self.pan_start
            box = self.renderer.axes.bbox
            dx = (event.x - x) * (xlim[1] - xlim[0]) / box.width
            dy = (event.y - y) * (ylim[1] - ylim[0]) / box.height
            self.renderer.axes.set_xlim(xlim[0] - dx, xlim[1] - dx)
            self.renderer.axes.set_ylim(ylim[0] - dy, ylim[1] - dy)
            self.canvas.draw_idle()
        else:
            super().on_motion(event)

    def on_release(self, event):
        self.pan_start = None
        super().on_release(event)

    def on_scroll(self, event):
        if event.inaxes is not self.renderer.axes or event.xdata is None:
            return
        factor = .85 if event.button == 'up' else 1 / .85
        for getter, setter, point in ((self.renderer.axes.get_xlim, self.renderer.axes.set_xlim, event.xdata),
                                      (self.renderer.axes.get_ylim, self.renderer.axes.set_ylim, event.ydata)):
            low, high = getter()
            setter(point + (low - point) * factor, point + (high - point) * factor)
        self.canvas.draw_idle()
