"""Keyboard-first search palette with story-local session state."""
import tkinter as tk
from tkinter import ttk
from .retrieval import search
from .theme import style_tree
from .widgets import table, wrapping_label, ActionBar
from .relationship_dialog import RelationshipDialog
from .history_dialog import HistoryDialog


class SearchDialog(tk.Toplevel):
    def __init__(self, app, state):
        super().__init__(app)
        self.app, self.state = app, state
        self.story_path = app.database.path
        self.search_job = None
        self.title("Search this story · Ctrl+K")
        self.geometry("800x480")
        self.transient(app)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        self.query = tk.StringVar(self, state.get("query", ""))
        self.entry = ttk.Entry(body, textvariable=self.query)
        self.entry.pack(fill="x")
        wrapping_label(body, text="Search cast, chapters, events, and relationship states. Down selects results; Enter opens; Escape closes.").pack(fill="x", pady=8)
        bar = ActionBar(body)
        bar.pack(side="bottom", fill="x")
        bar.add(ttk.Button(bar, text="Open selected", command=self.open_selected, style="Accent.TButton"))
        self.edit_button = bar.add(ttk.Button(bar, text="Edit details", command=self.edit_selected, state="disabled"))
        self.history_button = bar.add(ttk.Button(bar, text="View history", command=self.history_selected, state="disabled"))
        bar.add(ttk.Button(bar, text="Close", command=self.close))
        self.count = wrapping_label(body)
        self.count.pack(fill="x")
        self.notice = tk.StringVar(self)
        wrapping_label(body, textvariable=self.notice, style="Muted.TLabel").pack(fill="x")
        self.tree = table(body, {"kind": "Match", "title": "Story record", "snippet": "Matching context"})
        self.tree.column("kind", width=145, stretch=False)
        from .tree_art import install_tree_art
        self.refresh_art = install_tree_art(self.tree, lambda: self.results, lambda: self.app.database,
            lambda row: {'character': 'section.identity', 'chapter': 'section.chapter', 'event': 'section.event', 'history': 'section.notes'}.get(row.get('kind')))
        self.tree.bind("<<TreeviewSelect>>", self.remember_selection)
        self.tree.bind("<Double-1>", self.open_selected)
        self.bind("<Return>", self.open_selected)
        self.bind("<Escape>", lambda _: self.close())
        self.entry.bind("<Down>", self.focus_results)
        self.query.trace_add("write", lambda *_: self.schedule_refresh())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        style_tree(self)
        self.entry.focus_set()

    def refresh(self):
        if self.search_job is not None:
            self.after_cancel(self.search_job)
            self.search_job = None
        if self.app.database.path != self.story_path:
            self.close()
            return
        self.state["query"] = self.query.get()
        self.results = {self.result_key(row): row for row in search(self.app.database, self.query.get())}
        self.tree.delete(*self.tree.get_children())
        for key, row in self.results.items():
            self.tree.insert("", "end", iid=key, values=(row["kind"].title(), row["title"], row["snippet"]))
        self.refresh_art()
        selected = self.state.get("selection")
        if selected in self.results:
            self.tree.selection_set(selected)
            self.tree.see(selected)
        self.count.configure(text=f"{len(self.results)} matches" if self.query.get().strip() else "Enter text to search the active story.")
        self.update_actions()

    @staticmethod
    def result_key(row):
        return f"history:{row['id']}:{row['state_id']}" if row['kind'] == 'history' else f"{row['kind']}:{row['id']}"

    def schedule_refresh(self):
        if self.search_job is not None:
            self.after_cancel(self.search_job)
        self.search_job = self.after(120, self.refresh)

    def remember_selection(self, _event=None):
        if self.tree.selection():
            self.state["selection"] = self.tree.selection()[0]
        self.update_actions()

    def selected_relationship(self):
        if not self.tree.selection():
            return None
        row = self.results.get(self.tree.selection()[0])
        if not row or row["kind"] != "relationship":
            return None
        return next((item for item in self.app.database.relationships() if item["id"] == row["id"]), None)

    def update_actions(self):
        enabled = self.selected_relationship() is not None
        for button in (self.edit_button, self.history_button):
            button.state(["!disabled" if enabled else "disabled"])

    def edit_selected(self):
        relationship = self.selected_relationship()
        if relationship is None:
            self.unavailable()
            return
        dialog = RelationshipDialog(self, self.app.database, self.relationship_changed, relationship)
        self.restore_after_action(dialog)
        return dialog

    def history_selected(self):
        relationship = self.selected_relationship()
        if relationship is None:
            self.unavailable()
            return
        dialog = HistoryDialog(self, self.app.database, self.relationship_changed, relationship["id"])
        self.restore_after_action(dialog)
        return dialog

    def relationship_changed(self, message):
        self.app.refresh(message)
        self.notice.set("Relationship saved. Search results refreshed.")
        self.refresh()

    def restore_after_action(self, dialog):
        selected = self.tree.selection()[0] if self.tree.selection() else None

        def closed(event):
            if event.widget is not dialog:
                return
            if selected:
                self.state["selection"] = selected
            self.refresh()
            self.grab_set()
            if selected in self.results:
                self.tree.selection_set(selected)
                self.tree.focus(selected)

        dialog.bind("<Destroy>", closed, add="+")

    def unavailable(self):
        self.notice.set("That relationship is no longer available. Results were refreshed.")
        self.refresh()

    def focus_results(self, _event=None):
        if self.search_job is not None:
            self.refresh()
        if self.results:
            key = self.tree.selection()[0] if self.tree.selection() else next(iter(self.results))
            self.tree.selection_set(key)
            self.tree.focus(key)
            self.tree.focus_set()
        return "break"

    def open_selected(self, _event=None):
        selected_key = self.tree.selection()[0] if self.tree.selection() else None
        self.refresh()  # Resolve the current story and discard stale result rows.
        if not self.winfo_exists():
            return "break"
        if selected_key is not None and selected_key not in self.results:
            self.notice.set("That result is no longer available in this story.")
            return "break"
        if selected_key in self.results:
            self.tree.selection_set(selected_key)
        if not self.tree.selection():
            self.focus_results()
            return "break"
        row = self.results.get(self.tree.selection()[0])
        if row is None:
            self.notice.set("That result is no longer available.")
            return "break"
        if self.app.mode.get() == 'Simple':
            workspace = self.app.simple
            if row['kind'] == 'character':
                opened = workspace.inspect_character(row['id'])
            elif row['kind'] == 'relationship':
                opened = workspace.inspect_edge(row['id'])
                if opened:
                    workspace.graph.select_edge(row['id'])
            elif row['kind'] in ('event', 'chapter'):
                ident = row['id'] if row['kind'] == 'event' else next((event['id'] for event in self.app.database.events.list() if event['chapter_id'] == row['id']), None)
                opened = workspace.navigate(ident)
            else:
                state = next((state for state in self.app.database.history.rows(row['id']) if state['id'] == row['state_id']), None)
                opened = state is not None and workspace.navigate(state['event_id'])
                if opened:
                    workspace.state_task(row['id'], True)
            if opened:
                self.close()
            return 'break'
        if row["kind"] == "character":
            if self.app.tabs.select() == str(self.app.graph):
                opened = self.app.open_character(row["id"], origin="graph")
            elif self.app.tabs.select() == str(self.app.characters) and self.app.characters.character_id is not None:
                opened = self.app.navigation.open_profile_link(row["id"])
            else:
                opened = self.app.open_character(row["id"])
            if not opened:
                return "break"
        elif row['kind'] == 'relationship':
            if not self.app.characters.can_leave(reset_discard=True):
                return "break"
            if not self.app.relationships.select_relationship(row['id']):
                self.refresh()
                return "break"
            self.app.tabs.select(self.app.relationships)
        elif row['kind'] in ('chapter', 'event'):
            if not self.app.characters.can_leave(reset_discard=True):
                return "break"
            opened = (self.app.events.reveal_chapter(row['id'], self.story_path) if row['kind'] == 'chapter'
                      else self.app.events.reveal_event(row['id'], self.story_path))
            if not opened:
                self.notice.set("That result is no longer available in this story.")
                self.refresh()
                return "break"
        else:
            if not self.app.characters.can_leave(reset_discard=True):
                return "break"
            if not any(item['id'] == row['id'] for item in self.app.database.relationship_records()):
                self.notice.set("That relationship is no longer available in this story.")
                self.refresh()
                return "break"
            state_key = str(row['state_id'])
            self.close()
            dialog = HistoryDialog(self.app, self.app.database, self.app.refresh, row['id'])
            if state_key not in dialog.states:
                dialog.destroy()
                return "break"
            dialog.tree.selection_set(state_key)
            dialog.tree.see(state_key)
            return "break"
        self.close()
        return "break"

    def close(self):
        if self.search_job is not None:
            self.after_cancel(self.search_job)
            self.search_job = None
        self.remember_selection()
        self.destroy()

    def destroy(self):
        if getattr(self, 'search_job', None) is not None:
            self.after_cancel(self.search_job)
            self.search_job = None
        super().destroy()
