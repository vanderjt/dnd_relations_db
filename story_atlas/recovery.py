"""Recovery center: snapshots, safe import, Trash, and uncommitted drafts."""
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .backup import snapshot, backup_directory, restore_backup
from .imports import read_export, import_payload
from .widgets import table, wrapping_label, ActionBar
from .theme import style_tree


class RecoveryDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Recovery and data")
        self.geometry("820x570")
        self.minsize(650, 440)
        self.transient(app)
        self.grab_set()
        self.status = tk.StringVar(self)
        bottom = ttk.Frame(self, padding=12)
        bottom.pack(side="bottom", fill="x")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right")
        wrapping_label(bottom, textvariable=self.status, style="Muted.TLabel").pack(fill="x")
        tabs = self.tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.pages = {}
        for name in ("Backups & import", "Trash", "Drafts"):
            page = ttk.Frame(tabs, padding=12)
            tabs.add(page, text=name)
            self.pages[name] = page
        page = self.pages["Backups & import"]
        wrapping_label(page, text="Restore or import into a new story file.", style='Muted.TLabel').pack(fill="x")
        bar = ActionBar(page)
        bar.pack(fill="x")
        bar.add(ttk.Button(bar, text='Back up now', command=lambda: self.run(self.backup), style='Primary.TButton'))
        self.restore_backup_button = bar.add(ttk.Button(bar, text='Restore selected', command=lambda: self.run(self.restore_selected)))
        more = bar.add(ttk.Menubutton(bar, text='More'))
        menu = tk.Menu(more, tearoff=False)
        menu.add_command(label='Browse backup…', command=lambda: self.run(self.browse_backup))
        menu.add_command(label='Import JSON…', command=lambda: self.run(self.import_json))
        more.configure(menu=menu)
        retention = ActionBar(page)
        retention.pack(side='bottom', fill="x")
        retention.add(ttk.Label(retention, text="Keep automatic backups"))
        self.retention = tk.StringVar(value=str(app.settings.values["backup_retention"]))
        retention.add(ttk.Spinbox(retention, from_=1, to=100, width=5, textvariable=self.retention))
        retention.add(ttk.Button(retention, text="Save retention", command=lambda: self.run(self.save_retention)))
        self.backups = table(page, {"name": "Backup (UTC timestamp)"})
        for name in ("Trash", "Drafts"):
            page = self.pages[name]
            text = ("Restore characters first. Connections return when both endpoints are active; conflicts remain in Trash."
                    if name == "Trash" else "Recovery drafts are not committed profiles. Recover to review, then Save changes to commit.")
            wrapping_label(page, text=text).pack(fill="x")
        self.restore_trash_button = ttk.Button(self.pages["Trash"], text="Restore selected", command=lambda: self.run(self.restore_trash), style='Primary.TButton')
        self.restore_trash_button.pack(side='bottom', anchor="w")
        self.trash = table(self.pages["Trash"], {"type": "Type", "label": "Item", "time": "Deleted (UTC)"})
        draft_bar = ActionBar(self.pages["Drafts"])
        draft_bar.pack(side='bottom', fill="x")
        self.recover_button = draft_bar.add(ttk.Button(draft_bar, text="Recover selected", command=lambda: self.run(self.recover_draft), style='Primary.TButton'))
        self.discard_button = draft_bar.add(ttk.Button(draft_bar, text="Discard selected", style="Danger.TButton", command=lambda: self.run(self.discard_draft)))
        self.drafts = table(self.pages["Drafts"], {"name": "Task draft", "time": "Saved (UTC)"})
        for tree in (self.backups, self.trash, self.drafts):
            tree.bind('<<TreeviewSelect>>', self.update_actions, add='+')
        self.bind('<Escape>', lambda _: self.destroy())
        self.refresh()
        style_tree(self)

    def run(self, action):
        try:
            action()
        except (OSError, ValueError, sqlite3.Error) as error:
            messagebox.showerror("Recovery action failed", str(error), parent=self)

    def refresh(self):
        for tree in (self.backups, self.trash, self.drafts):
            tree.delete(*tree.get_children())
        directory = backup_directory(self.app.database.path)
        self.backup_paths = sorted(directory.glob("*.db"), reverse=True)
        for index, path in enumerate(self.backup_paths):
            self.backups.insert("", "end", iid=str(index), values=(path.name,))
        self.trash_items = self.app.database.trash.items()
        for index, row in enumerate(self.trash_items):
            self.trash.insert("", "end", iid=str(index), values=(row["type"], row["label"], row["deleted_at"]))
        self.draft_items = self.app.database.drafts.list()
        for index, row in enumerate(self.draft_items):
            self.drafts.insert("", "end", iid=str(index), values=(row["values"].get("name") or row["values"].get("task") or "Unnamed character", row["updated_at"]))
        self.status.set(f"{len(self.backup_paths)} backups · {len(self.trash_items)} Trash items · {len(self.draft_items)} drafts")
        self.update_actions()

    def update_actions(self, _event=None):
        for tree, buttons in ((self.backups, (self.restore_backup_button,)),
                              (self.trash, (self.restore_trash_button,)),
                              (self.drafts, (self.recover_button, self.discard_button))):
            for button in buttons:
                button.state(['!disabled' if tree.selection() else 'disabled'])

    def save_retention(self):
        value = int(self.retention.get())
        if not 1 <= value <= 100:
            raise ValueError("Retention must be between 1 and 100 automatic backups.")
        self.app.settings.save(backup_retention=value)
        self.status.set("Retention saved. Applied after the next automatic backup. Manual and migration backups are kept.")

    def backup(self):
        path = snapshot(self.app.database.connection, self.app.database.path)
        self.refresh()
        self.status.set(f"Backup saved: {path.name}")

    def restore_selected(self):
        if self.backups.selection():
            self.restore(self.backup_paths[int(self.backups.selection()[0])])

    def browse_backup(self):
        path = filedialog.askopenfilename(parent=self, title="Choose SQLite backup", filetypes=[("SQLite database", "*.db"), ("All files", "*.*")])
        if path:
            self.restore(path)

    def new_path(self):
        return filedialog.asksaveasfilename(parent=self, title="Choose a NEW database filename", defaultextension=".db", filetypes=[("SQLite database", "*.db")])

    def restore(self, source):
        destination = self.new_path()
        if destination:
            self.offer_open(restore_backup(source, destination))

    def import_json(self):
        path = filedialog.askopenfilename(parent=self, title="Import Story Atlas export", filetypes=[("JSON export", "*.json")])
        if not path:
            return
        data = read_export(path)
        summary = "\n".join(f"{len(rows)} {name}" for name, rows in data.items())
        if not messagebox.askyesno("Import preview", f"Validated export:\n{summary}\n\nCreate a new database from these records?", parent=self):
            return
        destination = self.new_path()
        if destination:
            self.offer_open(import_payload(data, destination))

    def offer_open(self, path):
        self.status.set(f"New database created: {path}")
        if messagebox.askyesno("Database ready", f"Open {path.name} now?", parent=self):
            if self.app.switch_database(path):
                self.refresh()

    def restore_trash(self):
        if self.trash.selection():
            item = self.trash_items[int(self.trash.selection()[0])]
            self.app.database.trash.restore(item["type"], item["id"])
            self.app.refresh("Trash item restored. Connections with deleted endpoints remain in Trash.")
            self.refresh()

    def recover_draft(self):
        if self.drafts.selection():
            item = self.draft_items[int(self.drafts.selection()[0])]
            if item['key'].startswith('task:'):
                if self.app.mode.get() != 'Simple':
                    self.grab_release()
                    self.app.mode.set('Simple')
                    if not self.app.switch_mode():
                        self.grab_set()
                        return
                    self.grab_set()
                workspace = self.app.simple
                payload = item['values']
                if payload['task'] == 'relationship':
                    from .simple_batch import BatchPane
                    task = workspace.mount(lambda: BatchPane(workspace.host, workspace, payload))
                elif payload['task'] == 'state':
                    from .simple_state import recover_state
                    task = recover_state(workspace, payload)
                else:
                    from .simple_event import EventPane
                    ident = payload.get('event_id')
                    row = next((r for r in self.app.database.events.list() if r['id'] == ident), None)
                    if ident is not None and row is None:
                        raise ValueError('This event no longer exists. Its draft is retained; restore a backup to recover its references.')
                    task = workspace.mount(lambda: EventPane(workspace.host, workspace, payload.get('new_chapter', False), row, payload))
                if task:
                    self.destroy()
                return
            if self.app.mode.get() == 'Simple':
                workspace = self.app.simple
                from .simple_profile import SimpleProfile
                ident = None if item['key'] == 'new' else int(item['key'].split(':')[1])
                row = next((row for row in self.app.database.characters() if row['id'] == ident), None)
                if ident is not None and row is None:
                    raise ValueError('Restore this character from Trash before recovering its draft.')
                task = workspace.mount(lambda: SimpleProfile(workspace.host, workspace, row, item['values']))
                if task:
                    workspace.provisional = ident is None
                    workspace.graph.refresh(force=True)
                    self.destroy()
                return
            if self.app.characters.recover_draft(item):
                self.app.tabs.select(self.app.characters)
                self.destroy()

    def discard_draft(self):
        if self.drafts.selection() and messagebox.askyesno("Discard draft", "Permanently discard this recovery draft? The committed character stays unchanged.", parent=self):
            item = self.draft_items[int(self.drafts.selection()[0])]
            self.app.database.drafts.discard_task(item["key"])
            self.refresh()
