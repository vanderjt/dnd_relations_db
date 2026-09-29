"""Explicit review before replacing two directional records with one mutual link."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .relationship_semantics import mutual, connection_label
from .widgets import text_area, wrapping_label, ActionBar
from .theme import style_tree


class ConsolidationDialog(tk.Toplevel):
    def __init__(self, parent, database, changed, first):
        super().__init__(parent)
        self.database, self.changed, self.first = database, changed, first
        self.preview = None
        self.title("Review reciprocal consolidation")
        self.geometry("720x620")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        wrapping_label(body, text=f"Selected #{first['id']}: {connection_label(first)}").pack(fill="x")
        wrapping_label(body, text="Choose the reverse record and the resulting mutual type. Both originals will stay in Trash; both notes and original labels will be preserved below.").pack(fill="x", pady=8)
        self.choices = {f"#{row['id']}: {connection_label(row)}": row["id"] for row in database.relationships()
                        if not mutual(first) and not mutual(row) and row["source_id"] == first["target_id"] and row["target_id"] == first["source_id"]}
        self.reverse = tk.StringVar(self)
        ttk.Combobox(body, values=tuple(self.choices), textvariable=self.reverse, state="readonly").pack(fill="x")
        ttk.Label(body, text="Resulting mutual type (choose deliberately)").pack(anchor="w", pady=(8, 0))
        self.kind = tk.StringVar(self)
        ttk.Entry(body, textvariable=self.kind).pack(fill="x", pady=4)
        for variable in (self.kind, self.reverse):
            variable.trace_add("write", self.invalidate)
        bar = ActionBar(body)
        bar.pack(side="bottom", fill="x")
        bar.add(ttk.Button(bar, text="Preview", command=self.review))
        self.confirm = bar.add(ttk.Button(bar, text="Confirm consolidation", command=self.commit, state="disabled"))
        bar.add(ttk.Button(bar, text="Cancel", command=self.destroy))
        self.details = text_area(body, height=14)
        self.details.pack(fill="both", expand=True, pady=12)
        self.show("Choose a reverse record and resulting type, then Preview." if self.choices else
                  "No active directional reciprocal records are available for this selection.")
        self.bind("<Escape>", lambda _: self.destroy())
        style_tree(self)

    def show(self, text):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def invalidate(self, *_):
        self.preview = None
        self.confirm.state(["disabled"])
        self.show("Selection changed. Preview again before confirming.")

    def review(self):
        try:
            self.preview = self.database.relationship_store.preview_consolidation(
                self.first["id"], self.choices.get(self.reverse.get()), self.kind.get())
            data = self.preview["result"]
            self.show(f"NEW MUTUAL CONNECTION: {connection_label(data)}\n\n"
                      "Both original records will be moved to Trash unchanged. Conflicting labels are retained as provenance. "
                      "No notes are deduplicated or discarded. The resulting notes are:\n\n" + data["notes"])
            self.confirm.state(["!disabled"])
        except (ValueError, sqlite3.Error) as error:
            self.preview = None
            self.confirm.state(["disabled"])
            self.show(str(error))

    def commit(self):
        if self.preview is None:
            return
        try:
            self.database.relationship_store.consolidate(self.preview)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Consolidation not completed", str(error), parent=self)
            self.invalidate()
            return
        self.changed("Reciprocal records consolidated; originals retained in Trash")
        self.destroy()
