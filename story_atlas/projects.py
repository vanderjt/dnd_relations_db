"""One database per story: file actions, safe handoff, and recent paths."""
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .database import Database
from .migrations import CURRENT_VERSION
from .backup import publish_database
from .global_search import SearchDialog
from .theme import style_tree
from .widgets import table, ActionBar, wrapping_label
from .paths import validate_writable_location


class Projects:
    def __init__(self, app):
        self.app = app
        self.sessions = {}
        self.search_states = {}
        app.header.bind('<Configure>', self.update_header_title, add='+')
        self.update_title()
        self.remember(app.database.path)

    def key(self, path):
        return str(Path(path).resolve())

    def update_title(self):
        title = self.app.database.connection.execute("SELECT value FROM story_metadata WHERE key='title'").fetchone()
        name = title[0] if title else self.app.database.path.stem
        self.app.title(f"Story Atlas · {name}")
        self.app.story_title.full_title = name
        self.update_header_title()
        self.app.story_title.master.reflow()

    def update_header_title(self, _event=None):
        from tkinter import font
        label = self.app.story_title
        title = getattr(label, 'full_title', 'Story Atlas')
        budget = max(120, min(360, int(self.app.winfo_width() * .27)))
        heading = font.nametofont('AtlasHeading', root=self.app)
        text = title
        while text and heading.measure(text + ('…' if text != title else '')) > budget:
            text = text[:-1]
        text += '…' if text != title else ''
        if label.cget('text') != text:
            label.configure(text=text)

    def remember(self, path):
        path = self.key(path)
        recent = [path] + [value for value in self.app.settings.values["recent_stories"] if self.key(value) != path]
        try:
            self.app.settings.save(recent_stories=recent[:12], last_story=path)
        except OSError as error:
            self.app.status.set(f"Story opened; recent list could not be saved: {error}")

    def permitted(self):
        # File actions cannot invalidate a database held by an open modal editor.
        # Recovery invokes switching from its own dialog and manages that lifecycle.
        from .relationship_dialog import RelationshipDialog
        from .event_view import EventDialog
        from .event_change_dialog import EventRelationshipChangeDialog
        from .history_dialog import StateDialog, HistoryDialog
        from .consolidation_dialog import ConsolidationDialog
        def has_editor(widget):
            return isinstance(widget, (RelationshipDialog, EventDialog, EventRelationshipChangeDialog, StateDialog, HistoryDialog, ConsolidationDialog)) or any(has_editor(child) for child in widget.winfo_children())
        if has_editor(self.app):
            messagebox.showinfo("Finish story entry", "Close the relationship or event dialog before switching stories.", parent=self.app)
            return False
        return self.app.characters.can_leave() and (not hasattr(self.app, 'simple') or self.app.simple.can_leave())

    def switch(self, path, create=False):
        path = validate_writable_location(path)
        if path == self.app.database.path.resolve():
            if create:
                raise ValueError("Choose a NEW filename; the active story cannot be overwritten.")
            return True
        if create and path.exists():
            raise ValueError("Choose a NEW database filename; existing files are never overwritten.")
        if not create and not path.is_file():
            raise ValueError(f"Story file is missing: {path}. Locate it with Open story or remove it from Recent stories.")
        # Validate existing files read-only before prompting or opening a writable connection.
        if not create:
            connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            try:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version < 1:
                    raise ValueError("This is not a versioned Story Atlas database.")
                if version > CURRENT_VERSION:
                    raise ValueError(f"Story schema {version} is newer than supported schema {CURRENT_VERSION}.")
            finally:
                connection.close()
        if not self.permitted():
            return False
        try:
            if create:
                publish_database(path, lambda temporary: Database(temporary).close())
            new_database = Database(path)
        except Exception:
            # Discard was permission to leave, but leaving failed. Keep the
            # still-visible edits recoverable as well as keeping the old connection.
            if self.app.characters.values() != self.app.characters.original:
                self.app.characters.draft.flush()
            if self.app.simple.task and hasattr(self.app.simple.task, 'draft'):
                self.app.simple.task.draft.flush()
            raise
        self.install(new_database)
        return True

    def install(self, new_database):
        app = self.app
        new_database.enable_undo()
        app.navigation.clear()
        # Undo IDs are meaningful only in the story where deletion occurred.
        for page in (app.characters, app.relationships):
            page.clear_undo()
        old_database = app.database
        view = app.characters
        self.sessions[self.key(old_database.path)] = dict(query=view.search.get(), filters=dict(view.roster.filters),
                                                        character=view.character_id,
                                                        relationship=app.relationships.tree.selection(),
                                                        relationship_character=app.relationships.character_id,
                                                        relationship_query=app.relationships.roster.query.get(),
                                                        chapter=app.events.chapter_id,
                                                        event=app.events.tree.selection())
        view.draft.cancel()
        if hasattr(app, 'simple'):
            app.simple.remove_task()
            app.simple.database = new_database
        app.database = new_database
        for page in app.views:
            page.database = new_database
        # Clear selections before IDs from a different database are loaded.
        app.relationships.tree.selection_remove(*app.relationships.tree.selection())
        state = self.sessions.get(self.key(new_database.path), {})
        view.roster.filters = state.get("filters", {})
        view.load(next((row for row in new_database.characters() if row["id"] == state.get("character")), None))
        view.search.set(state.get("query", ""))
        old_database.close()
        app.refresh(f"Opened {new_database.path}")
        app.events.restore_selection(state.get('chapter', 'all'), state.get('event', ()))
        app.relationships.select_character(state.get('relationship_character'))
        app.relationships.roster.query.set(state.get('relationship_query', ''))
        selection = state.get("relationship", ())
        if selection and selection[0] in app.relationships.rows:
            app.relationships.tree.selection_set(selection[0])
        self.update_title()
        self.remember(new_database.path)
        if app.backup_timer:
            app.after_cancel(app.backup_timer)
        app.automatic_backup()

    def try_sample(self, example='greyhaven'):
        """Create a separate sample only after pending edits permit switching."""
        from .sample_story import new_sample
        if not self.permitted():
            return False
        try:
            path = new_sample(self.app.settings.path.parent, example)
            database = Database(path)
        except (ValueError, OSError, sqlite3.Error) as error:
            messagebox.showerror('Cannot create sample', str(error), parent=self.app)
            return False
        self.install(database)
        return True

    def choose(self, create=False):
        if create:
            if not self.permitted():
                return
            from .story_setup import StorySetup
            return StorySetup(self.app, self.app.settings.path.parent / 'stories', lambda path: self.open_path(path))
        picker = filedialog.asksaveasfilename if create else filedialog.askopenfilename
        path = picker(parent=self.app, title="New story" if create else "Open story", defaultextension=".db",
                      initialdir=self.app.database.path.parent,
                      filetypes=[("Story Atlas database", "*.db"), ("SQLite database", "*.sqlite *.sqlite3")])
        if path:
            self.open_path(path, create)

    def open_path(self, path, create=False):
        try:
            return self.switch(path, create)
        except (ValueError, OSError, sqlite3.Error) as error:
            messagebox.showerror("Cannot open story", str(error), parent=self.app)
            return False

    def search(self):
        # Avoid opening another modal dialog over an unfinished modal entry.
        if self.app.grab_current() is not None:
            return "break"
        SearchDialog(self.app, self.search_states.setdefault(self.key(self.app.database.path), {}))
        return "break"

    def recent(self):
        dialog = tk.Toplevel(self.app)
        dialog.title("Recent stories")
        dialog.geometry("700x360")
        dialog.transient(self.app)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=16)
        body.pack(fill="both", expand=True)
        wrapping_label(body, text="Missing files stay listed until you remove them. Open story can locate a moved file.").pack(fill="x")
        bar = ActionBar(body)
        bar.pack(side="bottom", fill="x")
        tree = table(body, {"name": "Story", "path": "Full path", "status": "File"})
        paths = list(self.app.settings.values["recent_stories"])
        for index, path in enumerate(paths):
            tree.insert("", "end", iid=str(index), values=(Path(path).stem, path, "Available" if Path(path).is_file() else "Missing"))

        def open_selected(_event=None):
            if tree.selection() and self.open_path(paths[int(tree.selection()[0])]):
                dialog.destroy()

        def remove():
            if tree.selection():
                key = tree.selection()[0]
                try:
                    self.app.settings.save(recent_stories=[path for path in self.app.settings.values["recent_stories"] if path != paths[int(key)]])
                    tree.delete(key)
                except OSError as error:
                    messagebox.showerror("Cannot save recent list", str(error), parent=dialog)

        bar.add(ttk.Button(bar, text="Open selected", command=open_selected))
        bar.add(ttk.Button(bar, text="Remove from list", command=remove))
        bar.add(ttk.Button(bar, text="Close", command=dialog.destroy))
        tree.bind("<Return>", open_selected)
        tree.bind("<Double-1>", open_selected)
        dialog.bind("<Escape>", lambda _: dialog.destroy())
        style_tree(dialog)
