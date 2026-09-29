"""Read-only history of profile changes, relationships, and graph exports."""
from tkinter import ttk
from .widgets import table, text_area, wrapping_label


class ActivityView(ttk.Frame):
    def __init__(self, parent, database):
        super().__init__(parent, padding=16)
        self.database = database
        ttk.Label(self, text="Activity log", style="Heading.TLabel").pack(anchor="w")
        wrapping_label(self, text="Changes and exports are recorded automatically. Timestamps are UTC.").pack(fill="x", pady=6)
        self.empty = wrapping_label(self, style="Muted.TLabel")
        self.empty.pack(fill="x")
        self.tree = table(self, {"time": "Time (UTC)", "action": "Action", "details": "Details"})
        self.details = text_area(self, height=4)
        self.details.pack(fill="x")
        self.details.configure(state="disabled")
        self.tree.bind("<<TreeviewSelect>>", self.select)
        self.refresh()

    def refresh(self):
        self.rows = {str(row["id"]): row for row in self.database.activity()}
        self.empty.configure(text="" if self.rows else "No activity yet. Save a character to begin your story's history.")
        self.tree.delete(*self.tree.get_children())
        for key, row in self.rows.items():
            self.tree.insert("", "end", iid=key, values=(row["timestamp"], row["action"], row["details"]))

    def select(self, _event=None):
        if self.tree.selection():
            row = self.rows[self.tree.selection()[0]]
            self.details.configure(state="normal")
            self.details.delete("1.0", "end")
            self.details.insert("1.0", row["details"])
            self.details.configure(state="disabled")
