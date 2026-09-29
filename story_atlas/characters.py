"""Searchable character roster and profile editor."""
import tkinter as tk
import sqlite3
from tkinter import ttk, messagebox
from .models import LONG_FIELDS
from .widgets import wrapping_label, ActionBar
from .profile_editor import ProfileEditor
from .profile_overview import ProfileOverview
from .character_roster import CharacterRoster
from .relationship_dialog import RelationshipDialog
from .draft_controller import DraftController
from .retrieval import filter_characters, FILTER_FIELDS
from .filter_dialog import FilterDialog
from .goals_view import CastGoalsDialog


class CharactersView(ttk.Frame):
    def __init__(self, parent, database, changed, navigation=None):
        super().__init__(parent, padding=16)
        self.database, self.changed, self.navigation = database, changed, navigation
        self.character_id = None
        self.original = {}
        self.rows = {}
        self.draft = None
        heading = ttk.Frame(self)
        heading.pack(fill='x', pady=(0, 8))
        ttk.Label(heading, text="Characters", style="Heading.TLabel").pack(side='left')
        ttk.Button(heading, text='Cast goals', style='Secondary.TButton',
                   command=lambda: CastGoalsDialog(self, self.database)).pack(side='left', padx=12)
        ttk.Button(heading, text="Next: chapters & events", style="Navigation.TButton",
                   command=lambda: self.winfo_toplevel().tabs.select(self.winfo_toplevel().events)).pack(side='right')
        self.panes = panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)
        self.roster = roster = CharacterRoster(panes, self.new)
        editor = ttk.Frame(panes, padding=(16, 0, 0, 0))
        panes.add(roster, weight=1)
        panes.add(editor, weight=3)
        self.search, self.tree = roster.search, roster.tree
        roster.filter_button.configure(command=lambda: FilterDialog(roster, self.database, self.apply_filters))
        self.tree.bind("<<TreeviewSelect>>", self.select)
        self.buttons = buttons = ActionBar(editor)
        buttons.pack(side="bottom", fill="x", pady=(8, 0))
        self.primary_button = buttons.add(ttk.Button(buttons, text="Save changes", style="Primary.TButton", command=self.save))
        self.done_button = buttons.add(ttk.Button(buttons, text="Done", style="Secondary.TButton", command=self.done))
        self.duplicate_button = ttk.Button(buttons, text='Duplicate', command=self.duplicate)
        self.profile_menu_button = buttons.add(ttk.Menubutton(buttons, text='Profile actions', style='Secondary.TMenubutton'))
        self.profile_menu = tk.Menu(self.profile_menu_button, tearoff=False)
        self.profile_menu.add_command(label='Duplicate character', command=self.duplicate)
        self.profile_menu.add_command(label='Delete character…', command=self.delete)
        self.profile_menu_button.configure(menu=self.profile_menu)
        self.undo_target = None
        self.undo_notice = ttk.Frame(editor, style="Context.TFrame", padding=6)
        ttk.Label(self.undo_notice, text="Character moved to Trash.", style="Context.TLabel").pack(side="left")
        self.undo_button = ttk.Button(self.undo_notice, text="Undo deletion", style="Secondary.TButton",
                                      command=self.undo_delete, state="disabled")
        self.undo_button.pack(side="right", padx=(12, 0))
        self.profile_tabs = ttk.Notebook(editor)
        self.profile_tabs.pack(fill="both", expand=True)
        self.editor = ProfileEditor(self.profile_tabs, lambda: self.database)
        self.overview = ProfileOverview(self.profile_tabs, lambda: self.database, self.follow_profile_link,
                                        self.add_relationship_from_profile, self.edit_profile)
        self.profile_tabs.add(self.overview, text="Overview")
        self.profile_tabs.add(self.editor, text="Edit profile")
        self.profile_tabs.bind('<<NotebookTabChanged>>', self.update_actions)
        self.fields = self.editor.fields
        self.scroller = self.editor.scroller
        self._pane_restored = False
        panes.bind("<Configure>", self.restore_pane)
        self.search.trace_add("write", lambda *_: self.refresh())
        self.load(None)
        self.draft = DraftController(self)
        self.draft_status_label = wrapping_label(editor, textvariable=self.draft.status, style="Context.TLabel")
        self.draft_status_label.pack(side="bottom", fill="x")
        self.profile_tabs.pack_forget()
        self.profile_tabs.pack(fill="both", expand=True)
        self.refresh()

    def update_actions(self, _event=None):
        editing = self.profile_tabs.select() == str(self.editor)
        self.primary_button.configure(text='Save changes' if editing else 'Edit profile', command=self.save if editing else self.edit_profile)
        self.done_button.configure(text='Done' if editing else 'Read mode', state='normal' if editing else 'disabled')
        for index in (0, 1):
            self.profile_menu.entryconfigure(index, state='normal' if self.character_id is not None else 'disabled')

    def restore_pane(self, _event=None):
        if self.panes.winfo_width() < 100:
            return
        maximum = max(180, self.panes.winfo_width() // 2)
        if not self._pane_restored:
            settings = getattr(self.winfo_toplevel(), "settings", None)
            desired = settings.values["roster_width"] if settings else 280
            self.panes.sashpos(0, min(desired, maximum))
            self._pane_restored = True
        elif self.panes.sashpos(0) > maximum:
            self.panes.sashpos(0, maximum)
        self.buttons.reflow()

    def set_draft_status(self, text, kind="context"):
        """Keep recovery/unsaved context visible without presenting it as an error."""
        self.draft.status.set(text)
        styles = {"context": "Context.TLabel", "success": "Success.TLabel", "muted": "Muted.TLabel", "error": "Error.TLabel"}
        self.draft_status_label.configure(style=styles[kind])

    def show_undo_notice(self):
        self.undo_button.state(["!disabled"])
        self.undo_notice.pack(side="bottom", fill="x", before=self.draft_status_label, pady=(4, 0))

    def clear_undo(self):
        self.undo_target = None
        self.undo_button.state(["disabled"])
        self.undo_notice.pack_forget()

    def values(self):
        return {**{key: widget.get("1.0", "end-1c") if key in LONG_FIELDS else self.editor.field_widgets['tags'].value() if key == 'tags' else widget.get()
                for key, widget in self.fields.items()}, 'introduction_event_id': getattr(self, 'introduction_event_id', None)}

    def can_leave(self, reset_discard=False):
        if self.values() == self.original:
            return True
        answer = messagebox.askyesnocancel("Unsaved profile", "Save changes before continuing?", parent=self)
        if answer:
            return self.save()
        if answer is False:
            self.draft.discard()
            if reset_discard:
                # Navigation that leaves this editor mounted must replace the
                # discarded buffer. Story switching defers this until it succeeds.
                row = next((row for row in self.database.characters() if row['id'] == self.character_id), None)
                self.load(row)
            return True
        return False

    def load(self, row):
        if self.draft:
            self.draft.cancel()
            self.draft.loading = True
        self.editor.field_widgets["tags"].pending.set("")
        self.character_id = row["id"] if row else None
        self.introduction_event_id = row.get("introduction_event_id") if row else None
        for field, widget in self.fields.items():
            value = row.get(field, "") if row else "Neutral NPC" if field == "character_type" else "Neutral" if field == "classification" else "neutral" if field == "narrative_role" else ""
            if field in LONG_FIELDS:
                widget.delete("1.0", "end")
                widget.insert("1.0", value)
                widget.edit_reset()
                widget.edit_modified(False)
            else:
                widget.set(value)
        self.original = self.values()
        self.editor.template_status.set("")
        controls = getattr(self.winfo_toplevel(), 'undo_controls', None)
        if controls is not None:
            controls.reset_editor(self.editor)
        self.overview.refresh(self.character_id)
        self.duplicate_button.state(["!disabled" if row else "disabled"])
        self.profile_tabs.select(self.overview if row else self.editor)
        if self.draft:
            self.draft.loading = False
            self.set_draft_status("Unsaved changes are committed only with Save changes.")

    def recover_draft(self, draft):
        if not self.can_leave():
            return False
        ident = None if draft["key"] == "new" else int(draft["key"].split(":")[1])
        row = next((row for row in self.database.characters() if row["id"] == ident), None)
        if ident is not None and row is None:
            raise ValueError("Restore this character from Trash before recovering its draft.")
        self.load(row)
        self.draft.loading = True
        self.introduction_event_id = draft["values"].get("introduction_event_id", self.introduction_event_id)
        for field, widget in self.fields.items():
            value = draft["values"].get(field, "")
            if field in LONG_FIELDS:
                widget.delete("1.0", "end")
                widget.insert("1.0", value)
                widget.edit_modified(False)
            else:
                widget.set(value)
        if not draft['values'].get('character_type'):
            from .character_type import from_legacy
            self.fields['character_type'].set(from_legacy(draft['values'].get('classification', 'Neutral'), draft['values'].get('narrative_role', 'neutral')))
        self.draft.loading = False
        self.database.drafts.save(ident, self.values())
        self.set_draft_status("Recovered draft · review and Save changes to commit.")
        self.profile_tabs.select(self.editor)
        return True

    def destroy(self):
        if self.draft:
            self.draft.cancel()
        super().destroy()

    def refresh(self):
        self.rows = {str(row["id"]): row for row in filter_characters(self.database, self.search.get(), self.roster.filters)}
        self.roster.populate(self.rows, self.character_id)
        self.overview.refresh(self.character_id)
        self.duplicate_button.state(["!disabled" if self.character_id is not None else "disabled"])

    def apply_filters(self, state):
        self.roster.filters = {key: state.get(key, "") for key in FILTER_FIELDS}
        self.search.set(state.get("query", ""))

    def select(self, _event=None):
        selection = self.tree.selection()
        if selection and int(selection[0]) != self.character_id:
            row = self.rows[selection[0]]
            if self.can_leave():
                self.load(row)
            elif str(self.character_id) in self.rows:
                self.tree.selection_set(str(self.character_id))
            else:
                self.tree.selection_remove(*self.tree.selection())

    def open_character(self, character_id):
        if not self.can_leave():
            return False
        row = next((row for row in self.database.characters() if row["id"] == character_id), None)
        self.load(row)
        if row:
            # Direct navigation may show a profile outside the roster's filters.
            # Retain those filters so returning to the cast does not lose context.
            self.roster.populate(self.rows, character_id)
        return True

    def follow_profile_link(self, character_id):
        if self.navigation:
            return self.navigation.open_profile_link(character_id)
        return self.open_character(character_id)

    def new(self):
        if self.can_leave():
            self.tree.selection_remove(*self.tree.selection())
            self.load(None)

    def save(self):
        creating = self.character_id is None
        scroll = self.scroller.canvas.yview()[0]
        focus = self.focus_get()
        try:
            self.character_id = self.database.save_character(self.values(), self.character_id)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot save", str(error), parent=self)
            return False
        saved = next(row for row in self.database.characters() if row['id'] == self.character_id)
        self.fields['character_type'].set(saved['character_type'])
        self.editor.field_widgets['tags'].add()
        self.original = self.values()
        self.draft.cancel()
        self.set_draft_status("✓ Saved", "success")
        self.changed("Character saved")
        self.scroller.canvas.yview_moveto(scroll)
        if focus and self.scroller.contains(focus):
            focus.focus_set()
        if creating:
            self.overview.show_completion("Character saved. Choose an optional next step.")
        return True

    def done(self):
        if self.can_leave():
            # A successful save updates original; remaining dirty values mean
            # Discard was chosen. Unlike navigation, Done does not load a new row.
            if self.values() != self.original:
                row = next((row for row in self.database.characters() if row["id"] == self.character_id), None)
                self.load(row)
            self.profile_tabs.select(self.overview)
            return True
        return False

    def edit_profile(self, section=None):
        self.profile_tabs.select(self.editor)
        if section:
            self.editor.focus_section(section)

    def delete(self):
        if self.character_id is None:
            return
        if messagebox.askyesno("Move to Trash", "Move this character and attached relationships to Trash? They can be restored from Recovery.", parent=self):
            self.database.delete_character(self.character_id)
            self.undo_target = self.character_id
            self.show_undo_notice()
            self.load(None)
            self.changed("Character moved to Trash · Undo is available.")

    def undo_delete(self):
        if self.undo_target is None:
            return
        try:
            self.database.trash.restore("character", self.undo_target)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot undo deletion", f"The character remains in Trash: {error}", parent=self)
            return
        ident = self.undo_target
        self.clear_undo()
        self.changed("Character restored from Trash.")
        self.open_character(ident)

    def add_relationship(self):
        if self.character_id is None:
            return
        # Keep new relationship forms empty, including when launched from a profile.
        return RelationshipDialog(self, self.database, self.changed)

    def add_relationship_from_profile(self):
        if self.character_id is None:
            return
        # Context is offered as an explicit action inside an otherwise blank form.
        return RelationshipDialog(self, self.database, self.changed, context_source_id=self.character_id)

    def duplicate(self):
        if self.character_id is None or not self.can_leave():
            return
        if not messagebox.askyesno("Duplicate character", "Create a copy of the saved profile and portrait? "
                                   "Relationships and recovery drafts will NOT be copied.", parent=self):
            return
        ident = self.database.duplicate_character(self.character_id)
        row = next(row for row in self.database.characters() if row["id"] == ident)
        self.load(row)
        self.profile_tabs.select(self.editor)
        self.changed("Character duplicated without relationships")
