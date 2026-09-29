"""Readable committed profile and contextual relationship actions."""
import tkinter as tk
from tkinter import ttk
from .scroll_frame import ScrollFrame
from .widgets import wrapping_label, ActionBar
from .relationship_semantics import profile_connections
from .relationship_dialog import RelationshipDialog
from .history_dialog import HistoryDialog
from .relationship_display import LEGEND, relationship_details
from .illustrated_widgets import IllustratedLabel, IdentityHeader


class ProfileOverview(ttk.Frame):
    def __init__(self, parent, database_provider, open_character, add_relationship, edit_profile):
        super().__init__(parent)
        self.database_provider = database_provider
        self.open_character = open_character
        self.scroller = ScrollFrame(self)
        self.scroller.pack(fill="both", expand=True)
        body = self.scroller.content
        self.context = wrapping_label(body, text='Current — after the last event\nCurrent profile and goals · not historically versioned', style='Context.TLabel')
        self.context.pack(fill='x', pady=4)
        self.identity = IdentityHeader(body)
        self.identity.pack(fill='x')
        self.name, self.details, self.portrait = self.identity.name, self.identity.details, self.identity.portrait
        IllustratedLabel(body, 'section.story', text="Summary").pack(fill='x', pady=6)
        self.summary = wrapping_label(body)
        self.summary.pack(fill="x", pady=6)
        IllustratedLabel(body, 'section.goals', text="Goals").pack(fill='x', pady=6)
        self.goals = wrapping_label(body)
        self.goals.pack(fill="x", pady=6)
        self.completion = wrapping_label(body, style="Muted.TLabel")
        self.completion.pack(fill="x", pady=(4, 0))
        wrapping_label(body, text="This overview shows the current saved profile and goals; they are not historically versioned. Uncommitted edits stay in Edit profile.",
                       style="Muted.TLabel").pack(fill="x", pady=8)
        bar = ActionBar(body)
        bar.pack(fill="x")
        bar.add(ttk.Button(bar, text="Add more details", command=lambda: edit_profile("story")))
        bar.add(ttk.Button(bar, text="Edit identity", command=lambda: edit_profile("identity")))
        bar.add(ttk.Button(bar, text="Edit notes", command=lambda: edit_profile("notes")))
        bar.add(ttk.Button(bar, text="Edit goals", command=lambda: edit_profile("goals")))
        self.add_button = bar.add(ttk.Button(bar, text="Add relationship", style="Secondary.TButton", command=add_relationship))
        bar.add(ttk.Button(bar, text="Done", command=lambda: self.focus_set()))
        self.connections = ttk.Frame(body)
        self.connections.pack(fill="x", pady=12)
        self.links = []
        self.relationship_actions = {}
        self.character_id = None

    def compact_layout(self, compact):
        self.context.configure(text='Current saved profile' if compact else
            'Current — after the last event\nCurrent profile and goals · not historically versioned',
            style='Muted.TLabel' if compact else 'Context.TLabel')

    def refresh(self, character_id):
        self.character_id = character_id
        database = self.database_provider()
        row = next((row for row in database.characters() if row["id"] == character_id), None)
        self.photo = None
        self.links = []
        self.relationship_actions = {}
        for child in self.connections.winfo_children():
            child.destroy()
        if row is None:
            self.name.configure(text="A new character starts with a name")
            self.details.configure(text="Enter a name in Edit profile and save to create your character.")
            self.summary.configure(text="")
            self.goals.configure(text="")
            self.completion.configure(text="")
            self.portrait.configure(image="", text="")
            self.add_button.state(["disabled"])
            return
        self.add_button.state(["!disabled"])
        self.name.configure(text=f"{row['name']}  ·  #{row['id']}")
        self.details.configure(text="\n".join(f"{label}: {row[field]}" for field, label in (
            ("character_type", "Character type"), ("role", "Role"), ("status", "Status"), ("faction", "Faction"), ("location", "Location"), ("tags", "Tags")) if row[field]))
        self.summary.configure(text=row["summary"] or "No summary yet. Add a few sentences in Edit profile → Story.")
        self.goals.configure(text=row["goals"] or "What does this character want? Add immediate objectives, long-term ambitions, and obstacles in Edit goals.")
        self.photo = self.identity.show_portrait(database.assets, row['portrait'])
        wrapping_label(self.connections, text=LEGEND, style='Muted.TLabel').pack(fill='x')
        groups = profile_connections(database.relationships(), character_id)
        for title, matches in groups.items():
            heading = {'Outgoing': '→', 'Incoming': '←', 'Mutual': '↔'}[title]
            wrapping_label(self.connections, text=heading, style="Heading.TLabel").pack(fill="x", pady=(10, 4))
            if not matches:
                ttk.Label(self.connections, text="No connections yet.", style="Muted.TLabel").pack(anchor="w")
            for relation, ident, name, label in matches:
                row = ttk.Frame(self.connections)
                row.pack(fill="x", pady=(4, 0))
                button = ttk.Button(row, text=f"{name} (#{ident})",
                                    command=lambda ident=ident: self.open_character(ident))
                button.pack(side="left")
                self.links.append((ident, button))
                menu_button = ttk.Menubutton(row, text="More")
                menu_button.pack(side="right")
                menu = tk.Menu(menu_button, tearoff=False)
                menu.add_command(label="Correct entry", command=lambda relation=relation, control=menu_button: self.edit_relationship(relation, control))
                menu.add_command(label="View history", command=lambda relation=relation, control=menu_button: self.view_history(relation, control))
                menu_button.configure(menu=menu)
                self.relationship_actions[relation["id"]] = menu_button
                wrapping_label(self.connections, text=f"{relationship_details(relation, character_id)}\n{relation['notes']}".rstrip()).pack(fill="x")

    def show_completion(self, text):
        self.completion.configure(text=text)

    def edit_relationship(self, relation, launch_control):
        """Edit this exact record without leaving the profile that exposed it."""
        dialog = RelationshipDialog(self, self.database_provider(), self.relationship_changed, relation)
        self.restore_after_close(dialog, launch_control)
        return dialog

    def view_history(self, relation, launch_control):
        dialog = HistoryDialog(self, self.database_provider(), self.relationship_changed, relation["id"])
        self.restore_after_close(dialog, launch_control)
        return dialog

    def relationship_changed(self, message):
        # Keep the application's established refresh/activity behavior, then make
        # this profile reflect a successful modal edit immediately.
        top = self.winfo_toplevel()
        changed = getattr(top, "refresh", None)
        if changed:
            changed(message)
        self.refresh(self.character_id)

    def restore_after_close(self, dialog, launch_control):
        scroll = self.scroller.canvas.yview()[0]
        character_id = self.character_id

        def closed(event):
            if event.widget is not dialog:
                return
            # A cancel needs no special path: it simply returns to the same
            # profile state. Refreshing also covers edits made in HistoryDialog.
            if self.character_id == character_id:
                self.refresh(character_id)
                self.after_idle(lambda: self.scroller.canvas.yview_moveto(scroll))
                self.after_idle(lambda: launch_control.focus_set() if launch_control.winfo_exists() else None)

        dialog.bind("<Destroy>", closed, add="+")
