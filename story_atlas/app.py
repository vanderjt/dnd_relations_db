"""Application composition, shared refresh, and top-level actions."""
import logging
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from .database import Database
from .theme import apply_theme, style_tree
from .characters import CharactersView
from .relationships import RelationshipsView
from .graph_view import GraphView
from .activity import ActivityView
from .event_view import EventView
from .settings import Settings
from .appearance import AppearanceDialog
from .widgets import wrapping_label, ActionBar
from .projects import Projects
from .recovery import RecoveryDialog
from .backup import snapshot
from .guidance import GuidanceBar, show_help, show_about
from .paths import resource
from .navigation import NavigationController


class StoryAtlas(tk.Tk):
    def __init__(self, database_path, settings_path=None):
        super().__init__()
        self.title("Story Atlas · Character & Relationship Studio")
        self.geometry("1180x720")
        self.minsize(760, 480)
        if resource("story-atlas.ico").exists():
            self.iconbitmap(str(resource("story-atlas.ico")))
        self.settings = Settings(settings_path or Path(database_path).parent / "settings.json")
        apply_theme(self, self.settings.values["theme"], self.settings.values["text_size"])
        try:
            self.database = Database(database_path)
        except Exception:
            self.destroy()
            raise
        self.backup_timer = None
        header = self.header = ActionBar(self)
        header.pack(fill="x", padx=16, pady=6)
        self.story_title = ttk.Label(header, text="Story Atlas", style="Title.TLabel")
        header.add(self.story_title)
        self.story_menu = ttk.Menubutton(header, text="Story")
        story_actions = tk.Menu(self.story_menu, tearoff=False)
        for label, command in (("New story", lambda: self.projects.choose(True)),
                               ("Open story…", lambda: self.projects.choose()),
                               ("Recent stories…", lambda: self.projects.recent()),
                               ("Try expanded Greyhaven sample…", lambda: self.projects.try_sample()),
                               ("Try the modern prometheus…", lambda: self.projects.try_sample('prometheus')),
                               ("Export all data…", self.export_data)):
            story_actions.add_command(label=label, command=command)
        self.story_menu.configure(menu=story_actions)
        header.add(self.story_menu)
        header.add(ttk.Button(header, text="Search · Ctrl+K", command=lambda: self.projects.search()))
        header.add(ttk.Button(header, text="Help · F1", command=lambda: show_help(self)))
        header.add(ttk.Button(header, text="About", command=lambda: show_about(self)))
        self.maintenance_menu = ttk.Menubutton(header, text="Maintenance")
        maintenance_actions = tk.Menu(self.maintenance_menu, tearoff=False)
        maintenance_actions.add_command(label="Recovery, Trash, and drafts…", command=self.open_recovery)
        maintenance_actions.add_command(label="Appearance…", command=lambda: AppearanceDialog(self))
        maintenance_actions.add_command(label="Activity log (Advanced)", command=self.open_activity)
        self.maintenance_menu.configure(menu=maintenance_actions)
        header.add(self.maintenance_menu)
        self.mode = tk.StringVar(self, self.settings.values['mode'])
        mode_box = ttk.Combobox(header, textvariable=self.mode, values=('Simple', 'Advanced'), state='readonly', width=11)
        self.mode_label = header.add(ttk.Label(header, text='Mode'))
        self.mode_box = mode_box
        header.add(mode_box)
        mode_box.bind('<<ComboboxSelected>>', self.switch_mode)
        self.guidance = GuidanceBar(self)
        self.guidance.pack(fill="x")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12)
        self.navigation = NavigationController(self)
        self.back_button = header.add(ttk.Button(header, text="Back", command=self.navigation.back, state="disabled"))
        self.header_items = list(header.items)
        story_actions.add_separator()
        story_actions.add_command(label='Search · Ctrl+K', command=lambda: self.projects.search())
        story_actions.add_command(label='Help · F1', command=lambda: show_help(self))
        story_actions.add_command(label='About', command=lambda: show_about(self))
        self.characters = CharactersView(self.tabs, self.database, self.refresh, self.navigation)
        self.relationships = RelationshipsView(self.tabs, self.database, self.refresh)
        self.graph = GraphView(self.tabs, self.database, self.refresh, self.open_character)
        self.activity = ActivityView(self.tabs, self.database)
        self.events = EventView(self.tabs, self.database, self.refresh)
        self.views = (self.characters, self.events, self.relationships, self.graph, self.activity)
        for view, label in zip(self.views, ("Characters", "Chapters & events", "Relationships", "Graph", "Activity log")):
            self.tabs.add(view, text=label)
        self.tabs.hide(self.activity)
        self.tabs.bind("<<NotebookTabChanged>>", self.tab_changed)
        self.status = tk.StringVar(value=f"Ready  ·  Local database: {self.database.path}")
        self.status_label = wrapping_label(self, textvariable=self.status, style="Muted.TLabel", padding=(16, 6))
        self.status_label.pack(fill="x")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Control-s>", lambda _: self.simple.task.save() if self.mode.get() == 'Simple' and self.simple.task else self.characters.save() if self.mode.get() == 'Advanced' and self.tabs.select() == str(self.characters) else None)
        self.bind("<Control-k>", lambda _: self.projects.search())
        self.bind("<F1>", lambda _: show_help(self))
        self.projects = Projects(self)
        from .simple_workspace import SimpleWorkspace
        self.simple = SimpleWorkspace(self, self)
        self.apply_mode()
        self.database.enable_undo()
        from .undo_controls import UndoControls
        self.undo_controls = UndoControls(self)
        story_actions.add_separator()
        story_actions.add_command(label='Undo saved change', accelerator='Ctrl+Z', command=lambda: self.undo_controls.change())
        story_actions.add_command(label='Redo saved change', accelerator='Ctrl+Y', command=lambda: self.undo_controls.change(True))
        self.bind('<Escape>', lambda _: self.simple.escape() if self.mode.get() == 'Simple' and self.grab_current() is None else None)
        style_tree(self)
        self.automatic_backup()
        draft_count = len(self.database.drafts.list())
        if draft_count:
            self.status.set(f"{draft_count} recoverable task draft(s). Open Maintenance → Recovery to review them.")

    def switch_mode(self, _event=None):
        if not self.characters.can_leave(reset_discard=True) or not self.simple.close_task():
            self.mode.set(self.settings.values['mode'])
            return False
        if self.grab_current() is not None:
            self.mode.set(self.settings.values['mode'])
            return False
        source, target = (self.graph, self.simple.graph) if self.mode.get() == 'Simple' else (self.simple.graph, self.graph)
        if source.signature is not None:
            target.apply_state(source.capture_state())
        self.settings.save(mode=self.mode.get())
        self.apply_mode()
        return True

    def apply_mode(self):
        for widget in self.header_items:
            widget.grid_forget()
        self.header.items = [self.story_menu, self.maintenance_menu, self.mode_label, self.mode_box] if self.mode.get() == 'Simple' else list(self.header_items)
        self.projects.update_title()
        self.header.reflow()
        if self.mode.get() == 'Simple':
            self.tabs.pack_forget()
            self.guidance.pack_forget()
            self.simple.pack(fill='both', expand=True, before=self.status_label)
            self.simple.refresh()
        else:
            self.simple.pack_forget()
            self.guidance.pack(fill='x', before=self.status_label)
            self.tabs.pack(fill='both', expand=True, padx=12, before=self.status_label)
            if self.tabs.select() == str(self.graph) and self.graph.is_visible():
                self.graph.ensure_current()

    def tab_changed(self, _event=None):
        selected = self.tabs.select()
        if selected != str(self.activity) and self.tabs.tab(self.activity, 'state') != 'hidden':
            self.tabs.hide(self.activity)
        topics = {str(self.characters): "saving", str(self.relationships): "relationships", str(self.graph): "graph", str(self.events): "events", str(self.activity): "recovery"}
        self.guidance.show(topics.get(selected, "saving"))
        if selected == str(self.graph):
            self.graph.ensure_current()

    def open_activity(self):
        if self.mode.get() == 'Simple':
            self.mode.set('Advanced')
            if not self.switch_mode():
                return
        self.tabs.select(self.activity)

    def open_recovery(self):
        self.guidance.show("recovery")
        if self.simple.task and hasattr(self.simple.task, 'draft'):
            self.simple.task.draft.flush()
        self.characters.draft.cancel()
        # Do not erase an older recovery draft just by opening the center.
        if self.characters.values() != self.characters.original:
            self.characters.draft.flush()
        RecoveryDialog(self)

    def automatic_backup(self):
        try:
            snapshot(self.database.connection, self.database.path, "auto", self.settings.values["backup_retention"])
        except (OSError, sqlite3.Error, ValueError) as error:
            self.status.set(f"Automatic backup failed: {error}. Use Maintenance → Recovery to retry.")
        self.backup_timer = self.after(15 * 60 * 1000, self.automatic_backup)

    def switch_database(self, path):
        return self.projects.switch(path)

    def destroy(self):
        timer = getattr(self, "backup_timer", None)
        if timer:
            self.after_cancel(timer)
            self.backup_timer = None
        super().destroy()

    def set_appearance(self, mode, size):
        try:
            self.settings.save(theme=mode, text_size=size)
        except OSError as error:
            messagebox.showerror("Cannot save appearance", str(error), parent=self)
            return
        apply_theme(self, mode, size)
        self.update_idletasks()
        self.graph.invalidate(appearance=True)
        self.graph.controls.reflow()
        self.simple.graph._inspector_width = max(self.simple.graph._inspector_width or 380, size * 28)
        self.simple.graph._inspector_body_width = None
        self.simple.graph.size_inspector()
        self.simple.graph.invalidate(appearance=True)
        self.status.set("Appearance saved")

    def refresh(self, message="Ready"):
        for view in self.views:
            if view is self.graph:
                view.invalidate()
            else:
                view.refresh()
        if hasattr(self, 'simple'):
            self.simple.refresh()
        self.status.set(message)

    def open_character(self, character_id, origin=None):
        if self.mode.get() == "Simple":
            return self.simple.inspect_character(character_id)
        if origin == "graph":
            return self.navigation.open_from_graph(character_id)
        if self.characters.open_character(character_id):
            self.tabs.select(self.characters)
            return True
        return False

    def export_data(self):
        if not self.characters.can_leave():
            return
        filename = filedialog.asksaveasfilename(parent=self, title="Export all story data",
                                              defaultextension=".json", filetypes=[("JSON data", "*.json")])
        if filename:
            try:
                self.database.export_json(filename)
            except OSError as error:
                messagebox.showerror("Export failed", str(error), parent=self)
                return
            self.refresh(f"Story data exported to {filename}")

    def report_callback_exception(self, exception, value, traceback):
        logging.error("Application callback failed", exc_info=(exception, value, traceback))
        messagebox.showerror("Action failed", f"The action could not be completed.\n\n{value}", parent=self)

    def close(self):
        if self.characters.can_leave() and self.simple.close_task():
            try:
                width = (self.graph.body.winfo_width() - self.graph.body.sashpos(0)
                         if self.graph._inspector_restored else self.settings.values['graph_inspector_width'])
                self.settings.save(roster_width=self.characters.panes.sashpos(0),
                                   relationship_roster_width=self.relationships.panes.sashpos(0),
                                   graph_inspector_width=max(160, min(1000, width)))
            except OSError as error:
                messagebox.showwarning("Preferences not saved", str(error), parent=self)
            self.database.close()
            self.destroy()
