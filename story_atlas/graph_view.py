"""Graph exploration controller: incremental refresh, selection, drag, and pins."""
import time
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .graph import build_graph
from .graph_state import filter_graph, layout_positions, drawing_signature
from .graph_render import GraphRenderer
from .graph_inspector import GraphInspector
from .graph_actions import GraphActions
from .graph_controls import GraphControls
from .relationship_dialog import RelationshipDialog
from .history_dialog import HistoryDialog
from .chapters import event_label, event_scope
from .theme import palette
from .widgets import ActionBar, wrapping_label
from .graph_time import GraphTime, CURRENT_SCOPE


class GraphView(GraphTime, GraphActions, ttk.Frame):
    def __init__(self, parent, database, changed, open_character):
        super().__init__(parent, padding=12)
        self.database, self.changed, self.open_character = database, changed, open_character
        self.database_path = database.path
        self.positions, self.pins, self.selection = {}, set(), None
        self._focus_id, self.drag = None, None
        self.dirty, self.appearance_dirty = True, False
        self.signature, self.options_signature = None, None
        self.focus_choices = {}
        self.show_planned = tk.BooleanVar(self, False)
        self.as_of_id = None
        self.as_of = tk.StringVar(self, CURRENT_SCOPE)
        self.event_choices = {}
        ttk.Label(self, text="Relationship graph", style="Heading.TLabel").pack(anchor="w")
        scope_panel = ttk.Frame(self, style="Content.TFrame", padding=(0, 2))
        scope_panel.pack(fill="x", pady=(4, 0))
        self.filters = ActionBar(scope_panel)
        self.filters.pack(fill="x")
        self.event_box = self.filters.add(ttk.Combobox(self.filters, textvariable=self.as_of, state="readonly", width=24))
        self.event_box.bind("<<ComboboxSelected>>", self.event_changed)
        self.setup_time()
        self.focus = tk.StringVar(self, "Choose focus…")
        self.depth = tk.StringVar(self, "Full graph")
        self.direction = tk.StringVar(self, "Both")
        self.kind = tk.StringVar(self, "All types")
        self.layout = tk.StringVar(self, "Circle")
        self.labels = tk.BooleanVar(self, True)
        self.isolates = tk.BooleanVar(self, True)
        for variable, choices, width in ((self.focus, (), 18), (self.depth, ("Full graph", "Direct", "Two steps"), 11)):
            box = self.filters.add(ttk.Combobox(self.filters, textvariable=variable, values=choices, state="readonly", width=width))
            box.bind("<<ComboboxSelected>>", self.filter_changed)
            if variable is self.focus:
                self.focus_box = box
                box.bind('<<ComboboxSelected>>', self.focus_changed)
        self.filters.add(ttk.Checkbutton(self.filters, text="Labels", variable=self.labels, command=self.filter_changed))
        self.filter_menu_button = ttk.Menubutton(self.filters, text="Filters", style="Secondary.TMenubutton")
        self.filter_menu = tk.Menu(self.filter_menu_button, tearoff=False)
        self.filter_menu_button.configure(menu=self.filter_menu)
        self.filters.add(self.filter_menu_button)
        self.rebuild_filter_menu(("All types",))
        self.figure = Figure(figsize=(9, 6), facecolor=palette(self)["bg"])
        self.renderer = GraphRenderer(self.figure)
        self.body = ttk.Panedwindow(self, orient="horizontal")
        plot = ttk.Frame(self.body)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot)
        navigation_panel = ttk.Frame(self, style="Content.TFrame", padding=(0, 2))
        navigation_panel.pack(fill="x", pady=(4, 0))
        self.controls = GraphControls(navigation_panel, self.canvas, self.reset_layout, self.export, self.saved_views,
                                      self.layout, self.filter_changed)
        self.controls.pack(fill="x")
        self.toolbar = self.controls.navigation
        self.summary = wrapping_label(self, style="Muted.TLabel")
        self.summary.pack(fill="x", pady=(4, 0))
        self.body.pack(fill="both", expand=True)
        self.inspector = GraphInspector(self.body, self.select_edge, self.open_profile, self.toggle_pin, self.focus_node,
                                        self.edit_relationship, self.record_story_change, self.view_relationship_history)
        self.body.add(plot, weight=3)
        self.body.add(self.inspector, weight=1)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._inspector_restored = False
        self._inspector_body_width = None
        self._inspector_width = None
        self.body.bind("<Configure>", self.size_inspector)
        self.body.bind('<ButtonRelease-1>', self.remember_inspector_width, add='+')
        for name, callback in (("button_press_event", self.on_click), ("motion_notify_event", self.on_motion),
                               ("button_release_event", self.on_release)):
            self.canvas.mpl_connect(name, callback)
        self.graph = build_graph([], [])
        self.renderer.draw(self.graph, {}, set(), colors=palette(self))
        self.controls.fit_callback = self.fit_graph
        self.last_motion = 0

    def graph_characters(self):
        from .introductions import visible_cast
        return visible_cast(self.database, self.as_of_id, self.show_planned.get())

    def size_inspector(self, _event=None):
        width = self.body.winfo_width()
        if len(self.body.panes()) < 2 or width <= 400:
            return
        minimum = min(250, width // 2)
        maximum = max(minimum, width - 160)
        if not self._inspector_restored:
            settings = getattr(self.winfo_toplevel(), 'settings', None)
            self._inspector_width = settings.values['graph_inspector_width'] if settings else 300
            self._inspector_restored = True
        if width != self._inspector_body_width:
            self.body.sashpos(0, max(minimum, min(maximum, width - self._inspector_width)))
            self._inspector_body_width = width

    def remember_inspector_width(self, _event=None):
        if self._inspector_restored and self.body.winfo_width() > 400:
            self._inspector_width = self.body.winfo_width() - self.body.sashpos(0)

    def is_visible(self):
        return bool(self.winfo_ismapped())

    def invalidate(self, appearance=False):
        self.dirty = True
        self.appearance_dirty |= appearance
        self.figure.set_facecolor(palette(self)["bg"])
        if self.is_visible():
            self.ensure_current()

    def ensure_current(self):
        if self.dirty or self.database.path != self.database_path:
            self.refresh()

    def focus_id(self):
        return self._focus_id

    def event_changed(self, _event=None):
        self.as_of_id = self.event_choices.get(self.as_of.get())
        self.refresh(force=True)

    def event_metadata(self):
        if self.as_of_id is None:
            return None
        if self.as_of_id == 0:
            return dict(id=0, sequence=0, title="Before first event (undated starting state)")
        row = next(row for row in self.database.events.list() if row["id"] == self.as_of_id)
        chapter = next((chapter for chapter in self.database.chapters.list() if chapter['id'] == row['chapter_id']), None)
        return dict(row, chapter=chapter)

    def filter_changed(self, _event=None):
        self._focus_id = self.focus_choices.get(self.focus.get())
        if self.options_signature and self.options_signature[1] != self.layout.get():
            self.reset_layout()
            return
        self.refresh(force=True)

    def focus_changed(self, _event=None):
        self._focus_id = self.focus_choices.get(self.focus.get())
        if self._focus_id is not None:
            self.depth.set('Direct')
        self.refresh(force=True)
        self.fit_graph()

    def rebuild_filter_menu(self, kinds):
        self.filter_menu.delete(0, "end")
        self.filter_menu.add_checkbutton(label="Show planned cast (future; no active connections)", variable=self.show_planned, command=lambda: self.refresh(force=True))
        direction = tk.Menu(self.filter_menu, tearoff=False)
        for value in ("Both", "Incoming", "Outgoing"):
            direction.add_radiobutton(label=value, variable=self.direction, value=value, command=self.filter_changed)
        self.filter_menu.add_cascade(label="Direction", menu=direction)
        types = tk.Menu(self.filter_menu, tearoff=False)
        for value in kinds:
            types.add_radiobutton(label=value, variable=self.kind, value=value, command=self.filter_changed)
        self.filter_menu.add_cascade(label="Relationship type", menu=types)
        self.filter_menu.add_checkbutton(label="Show isolates", variable=self.isolates, command=self.filter_changed)
        self.add_time_menu(kinds)

    def refresh(self, force=False, limits=None):
        started = time.perf_counter()
        if self.database.path != self.database_path:
            self.database_path = self.database.path
            self.positions, self.pins, self.selection = {}, set(), None
            self._focus_id = None
            self.depth.set("Full graph")
            self.signature = None
            self.as_of_id = None
            self.visual_categories = {}
            self.highlight_changes.set(False)
            self.changes_only.set(False)
            self.kind.set('All types')
            self.direction.set('Both')
            self.isolates.set(True)
        if getattr(self, '_presentation_path', None) != self.database.path:
            self._presentation_path = self.database.path
            from .example_views import opening_view
            preset = opening_view(self.database)
            if preset:
                self.visual_categories = dict(preset.get('visual_categories', {}))
                self.positions = {int(node): point for node, point in preset['positions'].items()}
                self.layout.set(preset['layout'])
                self.labels.set(preset['labels'])
        self.event_choices = {CURRENT_SCOPE: None, "Before first event": 0}
        self.event_choices.update({event_scope(self.database, row): row["id"] for row in self.database.events.list()})
        if self.as_of_id not in self.event_choices.values():
            self.as_of_id = None
        self.event_box.configure(values=tuple(self.event_choices))
        self.as_of.set(next(label for label, ident in self.event_choices.items() if ident == self.as_of_id))
        characters, relationships = self.graph_characters(), self.database.relationships(self.as_of_id)
        changes = self.event_changes()
        if self.changes_only.get():
            relationships = changes
        self.previous_button.state(['disabled' if self.as_of_id == 0 else '!disabled'])
        self.next_button.state(['disabled' if self.as_of_id is None else '!disabled'])
        visible_ids = {row['id'] for row in characters if not row.get('planned')}
        relationships = [row for row in relationships if row['source_id'] in visible_ids and row['target_id'] in visible_ids]
        all_graph = build_graph(characters, relationships)
        self.focus_choices = {f"{row['name']} (#{row['id']})": row["id"] for row in characters}
        self.focus_box.configure(values=tuple(self.focus_choices))
        if self._focus_id not in all_graph:
            self._focus_id = None
        self.focus.set(next((name for name, ident in self.focus_choices.items() if ident == self._focus_id), "Choose focus…"))
        kinds = ["All types"] + sorted({value for row in relationships for value in (row["kind"], row.get("inverse_label", "")) if value} | ({self.kind.get()} if self.kind.get() != 'All types' else set()))
        self.rebuild_filter_menu(kinds)
        existing_ids = {row['id'] for row in self.database.characters()} | {row['id'] for row in characters}
        self.pins.intersection_update(existing_ids)
        self.positions = {node: point for node, point in self.positions.items() if node in existing_ids}
        if self.positions:
            from .node_placement import free_position
            axes = self.renderer.axes
            for node in all_graph:
                if node not in self.positions:
                    self.positions[node] = free_position(self.positions, axes.get_xlim(), axes.get_ylim(), (axes.bbox.width, axes.bbox.height))
        self.positions.update(layout_positions(all_graph, self.positions, self.pins, self.layout.get()))
        if self.selection and ((self.selection[0] == "node" and self.selection[1] not in all_graph) or
                               (self.selection[0] == "edge" and self.selection[1] not in {row['id'] for row in self.database.relationship_records()})):
            self.selection = None
        self.graph = filter_graph(build_graph(characters, relationships, self.kind.get()), self._focus_id,
                                  self.depth.get(), self.direction.get(), self.isolates.get())
        signature = drawing_signature(self.graph)
        options = (self.labels.get(), self.layout.get(), self.as_of.get())
        self.renderer.changed_ids = {row['id'] for row in changes} if self.highlight_changes.get() or self.changes_only.get() else set()
        self.renderer.visual_categories = self.visual_categories
        if force or self.appearance_dirty or signature != self.signature or options != self.options_signature:
            current_limits = limits
            if current_limits is None and self.signature is not None and self.signature[0]:
                current_limits = (self.renderer.axes.get_xlim(), self.renderer.axes.get_ylim())
            self.renderer.focus = self._focus_id
            self.renderer.draw(self.graph, self.positions, self.pins, self.labels.get(), palette(self),
                               getattr(self._root(), "atlas_text_size", 10), current_limits, self.selection)
            self.figure.suptitle(self.as_of.get()[:100] + '\n' + self.displayed_scope(), color=palette(self)["text"], fontsize=10)
            self.renderer.layout_legend()
            if self.signature is None:
                self.controls.reset_history()
            self.canvas.draw_idle()
        self.signature, self.options_signature = signature, options
        self.renderer.positions, self.renderer.graph, self.renderer.pins = self.positions, self.graph, self.pins
        self.renderer.focus = self._focus_id
        self.renderer.highlight(self.selection)
        self.dirty, self.appearance_dirty = False, False
        self.inspector.focus_id = self._focus_id
        self.inspector.focus_scope = self.depth.get()
        self.inspector.populate(self.graph, self.selection, self.pins, self.as_of.get())
        scope = [self.as_of.get(), self.focus.get() if self._focus_id is not None else "All characters",
                 self.depth.get(), self.direction.get()]
        if self.kind.get() != "All types":
            scope.append(self.kind.get())
        if not self.isolates.get():
            scope.append("isolates hidden")
        self.summary.configure(style="Context.TLabel" if self.as_of_id is not None else "Muted.TLabel",
                               text=f"{self.displayed_scope()}: " + " · ".join(scope)
                                    + (f" · Event changes: {len(changes)} ({sum(row['ended_here'] for row in changes)} endings; use Changes only to inspect endings)" if self.highlight_changes.get() else '')
                                    + f"  —  {len(self.graph)} characters, {self.graph.number_of_edges()} relationships")
        self.last_refresh_seconds = time.perf_counter() - started

    def fit_graph(self):
        if self.graph:
            self.renderer.fit_limits = self.renderer.bounds()
        self.renderer.axes.set_xlim(*self.renderer.fit_limits[0])
        self.renderer.axes.set_ylim(*self.renderer.fit_limits[1])
        self.toolbar.push_current()
        self.canvas.draw_idle()

    def reset_layout(self):
        before = self.capture_state()
        if self.options_signature:
            before['layout'] = self.options_signature[1]
        self.controls.clear_mode()
        graph = build_graph(self.database.characters(), self.database.relationships(self.as_of_id))
        self.positions = layout_positions(graph, self.positions, self.pins, self.layout.get(), reset=True)
        self.refresh(force=True)
        self.fit_graph()
        self.controls.reset_history()
        self.record_graph_change(before)

    def select_node(self, node):
        self.selection = ("node", node)
        self.renderer.highlight(self.selection)
        self.inspector.focus_id = self._focus_id
        self.inspector.populate(self.graph, self.selection, self.pins, self.as_of.get())
        self.canvas.draw_idle()

    def select_edge(self, ident):
        self.selection = ("edge", ident)
        self.renderer.highlight(self.selection)
        self.inspector.focus_id = self._focus_id
        self.inspector.update_details(self.graph, self.selection, self.pins, self.as_of.get())
        self.canvas.draw_idle()

    def open_profile(self, node):
        if node is not None:
            self.open_character(node, origin="graph")

    def focus_node(self, node):
        self._focus_id = node
        self.depth.set("Direct")
        self.refresh(force=True)
        self.fit_graph()

    def toggle_pin(self):
        if self.selection and self.selection[0] == "node":
            before = self.capture_state()
            node = self.selection[1]
            self.pins.symmetric_difference_update({node})
            self.renderer.highlight(self.selection)
            self.inspector.focus_id = self._focus_id
            self.inspector.update_details(self.graph, self.selection, self.pins, self.as_of.get())
            self.canvas.draw_idle()
            self.record_graph_change(before)

    def record_graph_change(self, before):
        controls = getattr(self.winfo_toplevel(), 'undo_controls', None)
        if controls is not None:
            controls.record_graph(before, self.capture_state())

    def on_click(self, event):
        if event.inaxes is not self.renderer.axes or event.button != 1 or self.toolbar.mode:
            return
        node = self.renderer.pick_node(event)
        if node is not None:
            self.select_node(node)
            self.drag = dict(node=node, start=(event.x, event.y), moved=False, before=self.capture_state())
        else:
            ident = self.renderer.pick_edge(event)
            if ident is not None:
                self.select_edge(ident)
            else:
                self.selection = None
                self.renderer.highlight(None)
                self.inspector.populate(self.graph, None, self.pins, self.as_of.get())
                self.canvas.draw_idle()

    def on_motion(self, event):
        if not self.drag or event.inaxes is not self.renderer.axes or self.toolbar.mode:
            return
        if time.perf_counter() - self.last_motion < .03:
            return
        if abs(event.x-self.drag['start'][0]) + abs(event.y-self.drag['start'][1]) < 4:
            return
        self.last_motion = time.perf_counter()
        self.drag["moved"] = True
        self.renderer.move_node(self.drag["node"], (event.xdata, event.ydata))
        self.canvas.draw_idle()

    def on_release(self, event):
        if self.drag and self.drag["moved"]:
            if event.inaxes is self.renderer.axes:
                self.renderer.move_node(self.drag["node"], (event.xdata, event.ydata))
            self.pins.add(self.drag["node"])
            self.renderer.highlight(self.selection)
            self.inspector.focus_id = self._focus_id
            self.inspector.update_details(self.graph, self.selection, self.pins, self.as_of.get())
            self.canvas.draw_idle()
            if 'before' in self.drag:
                self.record_graph_change(self.drag['before'])
        self.drag = None

    def relationship_row(self, ident):
        """Return the current record for the editor, retaining the exact stable ID."""
        try:
            state = self.database.history.editing_state(ident)
        except ValueError:
            return None
        return dict(state, id=ident)

    def edit_relationship(self, ident, launch_control):
        row = self.relationship_row(ident)
        if row is None:
            return
        if self.as_of_id is not None and not messagebox.askyesno(
                "Editing current relationship",
                f"This graph is viewing {self.as_of.get()}. Correct entry updates the latest saved state. Use History to correct an earlier state.\n\nCorrect Current relationship #{ident}?",
                parent=self):
            return
        dialog = RelationshipDialog(self, self.database, self.relationship_action_changed, row)
        self.restore_graph_after_close(dialog, launch_control)
        return dialog

    def record_story_change(self, ident, launch_control):
        dialog = HistoryDialog(self, self.database, self.relationship_action_changed, ident)
        self.restore_graph_after_close(dialog, launch_control)
        return dialog

    def view_relationship_history(self, ident, launch_control):
        dialog = HistoryDialog(self, self.database, self.relationship_action_changed, ident, self.as_of_id)
        self.restore_graph_after_close(dialog, launch_control)
        return dialog

    def relationship_action_changed(self, message):
        self.changed(message)

    def restore_graph_after_close(self, dialog, launch_control):
        state = self.capture_state()

        def closed(event):
            if event.widget is not dialog:
                return
            self.apply_state(state)
            if launch_control.winfo_exists():
                launch_control.focus_set()

        dialog.bind("<Destroy>", closed, add="+")

    def destroy(self):
        for attribute in ("_idle_draw_id", "_event_loop_id"):
            pending = getattr(self.canvas, attribute, None)
            if pending:
                self.canvas.get_tk_widget().after_cancel(pending)
                setattr(self.canvas, attribute, None)
        super().destroy()
