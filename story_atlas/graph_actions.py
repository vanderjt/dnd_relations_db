"""Saved-view dialogs and exports, separated from graph interaction code."""
import json
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .graph_state import SavedViews
from .theme import palette, style_tree
from .widgets import ActionBar, wrapping_label


class GraphActions:
    def capture_state(self):
        axes = self.renderer.axes
        return dict(version=1, show_planned=self.show_planned.get(), as_of_event=self.as_of_id, focus=self.focus_id(), depth=self.depth.get(), direction=self.direction.get(),
                    highlight_changes=self.highlight_changes.get(), changes_only=self.changes_only.get(), visual_categories=dict(self.visual_categories),
                    kind=self.kind.get(), layout=self.layout.get(), isolates=self.isolates.get(), labels=self.labels.get(),
                    positions={str(node): [float(value) for value in point] for node, point in self.positions.items()}, pins=sorted(self.pins),
                    selection=list(self.selection) if self.selection else None,
                    inspector_scroll=[self.inspector.tree.yview()[0], self.inspector.details.yview()[0]],
                    xlim=[float(value) for value in axes.get_xlim()],
                    ylim=[float(value) for value in axes.get_ylim()])

    def apply_state(self, state):
        self.controls.clear_mode()
        self.positions = {int(node): point for node, point in state["positions"].items()}
        self.pins = set(state["pins"])
        self.selection = tuple(state["selection"]) if state["selection"] else None
        for key in ("depth", "direction", "kind", "layout", "isolates", "labels"):
            getattr(self, key).set(state[key])
        self._focus_id = state["focus"]
        self.show_planned.set(state.get("show_planned", False))
        self.as_of_id = state.get("as_of_event")
        self.highlight_changes.set(state.get('highlight_changes', False))
        self.changes_only.set(state.get('changes_only', False))
        self.visual_categories = dict(state.get('visual_categories', {}))
        self.refresh(force=True, limits=(state["xlim"], state["ylim"]))
        scroll = state.get('inspector_scroll', [0, 0])
        self.inspector.tree.yview_moveto(scroll[0])
        self.inspector.details.yview_moveto(scroll[1])
        self.controls.reset_history()

    def saved_views(self):
        dialog = tk.Toplevel(self)
        dialog.title("Saved graph views")
        dialog.geometry("520x240")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        store = SavedViews(self.database)
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)
        wrapping_label(frame, text="Save filters, positions, pins, selection, and zoom for this story.").pack(fill="x")
        name = tk.StringVar(dialog)
        choices = ttk.Combobox(frame, textvariable=name, values=store.names())
        choices.pack(fill="x", pady=12)
        status = tk.StringVar(dialog)
        bar = ActionBar(frame)
        bar.pack(fill="x")

        def action(operation):
            try:
                value = name.get().strip()
                if operation == "Save":
                    if value in store.names() and not messagebox.askyesno("Replace view", f"Replace '{value}'?", parent=dialog):
                        return
                    store.save(value, self.capture_state())
                elif operation == "Load":
                    self.apply_state(store.load(value))
                elif value in store.names() and messagebox.askyesno("Delete view", f"Delete '{value}'?", parent=dialog):
                    store.delete(value)
                choices.configure(values=store.names())
                status.set(f"{operation} completed.")
            except (ValueError, sqlite3.Error) as error:
                status.set(str(error))

        for operation in ("Save", "Load", "Delete"):
            bar.add(ttk.Button(bar, text=operation, command=lambda operation=operation: action(operation)))
        bar.add(ttk.Button(bar, text="Close", command=dialog.destroy))
        wrapping_label(frame, textvariable=status).pack(fill="x", pady=8)
        style_tree(dialog)

    def export(self):
        self.ensure_current()
        filename = filedialog.asksaveasfilename(parent=self, title="Export displayed graph",
                                               defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if not filename:
            return
        image_path = Path(filename)
        data_path = image_path.with_suffix(".json")
        if data_path.exists() and not messagebox.askyesno("Replace snapshot data?", f"Replace {data_path.name} as well?", parent=self):
            return
        snapshot = dict(format_version=9, snapshot_kind="graph", as_of_event=self.event_metadata(), view=self.capture_state(),
                        time_scope=self.as_of.get(), display_scope=self.displayed_scope(), profile_scope='Current profile, classification and goals; not historically versioned',
                        characters=[data for _, data in self.graph.nodes(data=True)],
                        relationships=[dict(data, baseline_active=0 if data.get('ended_here') else 1) for _, _, data in self.graph.edges(data=True)])
        original_size = self.figure.get_size_inches().copy()
        try:
            self.figure.set_size_inches(max(9, original_size[0]), max(6, original_size[1]), forward=False)
            self.renderer.layout_legend()
            self.canvas.draw()
            self.figure.savefig(image_path, dpi=180, facecolor=palette(self)["bg"])
            data_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
            self.database.log("Graph snapshot exported", f"{image_path}; {data_path}; {self.as_of.get()}; {self.depth.get()}; {self.direction.get()}; {self.kind.get()}")
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self)
            return
        finally:
            self.figure.set_size_inches(original_size, forward=False)
            self.renderer.layout_legend()
            self.canvas.draw_idle()
        self.changed(f"Graph snapshot saved to {image_path}")
