"""Graph-side details and an unambiguous list of individual relationships."""
from tkinter import ttk
from .widgets import wrapping_label, table, ActionBar, read_only_text_area, set_read_only_text
from .relationship_semantics import connection_label, perspectives
from .relationship_display import relationship_details


class GraphInspector(ttk.Frame):
    def __init__(self, parent, select_edge, open_profile, toggle_pin, focus_node, edit_relationship, record_change, view_history):
        super().__init__(parent, padding=(12, 0, 0, 0))
        self.select_edge = select_edge
        self.edit_relationship, self.record_change, self.view_history = edit_relationship, record_change, view_history
        self.node = None
        self.heading = wrapping_label(self, text="Inspector", style="Heading.TLabel")
        self.heading.pack(fill="x")
        self.details = read_only_text_area(self, height=5)
        self.set_details("Select a character or relationship.")
        self.details.pack(fill="x", pady=8)
        bar = ActionBar(self)
        bar.pack(fill="x")
        self.open_button = bar.add(ttk.Button(bar, text="Open profile", command=lambda: open_profile(self.node)))
        self.pin_button = bar.add(ttk.Button(bar, text="Pin", command=toggle_pin))
        self.focus_button = bar.add(ttk.Button(bar, text="Focus here", command=lambda: focus_node(self.node)))
        self.relationship_bar = ActionBar(self)
        self.relationship_bar.pack(fill="x", pady=(8, 0))
        self.edit_button = self.relationship_bar.add(ttk.Button(self.relationship_bar, text="Correct entry", command=self.edit_selected))
        self.record_button = self.relationship_bar.add(ttk.Button(self.relationship_bar, text="Record story change", command=self.record_selected))
        self.history_button = self.relationship_bar.add(ttk.Button(self.relationship_bar, text="View history", command=self.history_selected))
        self.relationship_id = None
        self.tree = table(self, {"id": "ID", "link": "Visible relationships"})
        self.tree.column("id", width=45, minwidth=40, stretch=False)
        self.tree.column("link", width=230)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def set_details(self, text):
        set_read_only_text(self.details, text)

    def on_select(self, _event=None):
        selection = self.tree.selection()
        if selection:
            self.select_edge(int(selection[0]))

    def edit_selected(self):
        if self.relationship_id is not None:
            return self.edit_relationship(self.relationship_id, self.edit_button)

    def record_selected(self):
        if self.relationship_id is not None:
            return self.record_change(self.relationship_id, self.record_button)

    def history_selected(self):
        if self.relationship_id is not None:
            return self.view_history(self.relationship_id, self.history_button)

    def update_details(self, graph, selection, pins, context_label="Current — after the last event"):
        self.node = selection[1] if selection and selection[0] == "node" and selection[1] in graph else None
        self.relationship_id = selection[1] if selection and selection[0] == "edge" else None
        for button in (self.open_button, self.pin_button, self.focus_button):
            button.state(["!disabled" if self.node is not None else "disabled"])
        for button in (self.edit_button, self.record_button, self.history_button):
            button.state(["!disabled" if self.relationship_id is not None else "disabled"])
        if self.node is not None:
            data = graph.nodes[self.node]
            self.heading.configure(text=f"{data['name']} · #{self.node}")
            state = ["Selected in the inspector."]
            state.append(f"Focus: on (scope is {getattr(self, 'focus_scope', 'Full graph')})." if self.node == getattr(self, "focus_id", None)
                         else "Focus: off.")
            state.append("Pinned: on (dragging keeps this position)." if self.node in pins
                         else "Pinned: off (drag to pin this character).")
            self.set_details(f"Current profile · not historically versioned\n{data.get('role') or 'No role'}\n{data.get('summary') or 'No summary'}\nCurrent goals: {data.get('goals') or 'No saved goals.'}\n"
                             + " ".join(state))
            self.pin_button.configure(text="Unpin" if self.node in pins else "Pin")
        elif selection and selection[0] == "edge":
            data = next((data for _, _, key, data in graph.edges(keys=True, data=True) if key == selection[1]), None)
            if data:
                self.heading.configure(text=f"Relationship #{selection[1]} · {context_label}")
                self.set_details(('ENDS AT THIS EVENT\n' if data.get('ended_here') else '') + relationship_details(data)
                                 + f"\n{data['notes'] or 'No notes'}\nViewing: {context_label}")
            else:
                self.heading.configure(text="Selection outside this view")
                self.set_details("Adjust filters to show the selected relationship.")
        else:
            self.heading.configure(text="Inspector")
            self.set_details("Select a node or arrow. Use the list below to choose any individual relationship.")

    def populate(self, graph, selection, pins, context_label="Current — after the last event"):
        self.tree.delete(*self.tree.get_children())
        node = selection[1] if selection and selection[0] == "node" else None
        for source, target, ident, data in graph.edges(keys=True, data=True):
            if node is None or node in (source, target):
                self.tree.insert("", "end", iid=str(ident), values=(ident, connection_label(data)))
        self.update_details(graph, selection, pins, context_label)
