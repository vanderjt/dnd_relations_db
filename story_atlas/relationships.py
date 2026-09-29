"""Relationship list and a compact modal editor."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .relationship_dialog import RelationshipDialog
from .widgets import table, wrapping_label, ActionBar, read_only_text_area, set_read_only_text
from .consolidation_dialog import ConsolidationDialog
from .history_dialog import HistoryDialog
from .relationship_display import LEGEND, relationship_list_label, relationship_list_type, relationship_details
from .relationship_roster import RelationshipRoster


class RelationshipsView(ttk.Frame):
    def __init__(self, parent, database, changed):
        super().__init__(parent, padding=16)
        self.database, self.changed = database, changed
        self.database_path = database.path
        self.character_id = None
        self._pane_restored = False
        self.title_label = ttk.Label(self, text="Relationships", style="Heading.TLabel")
        self.title_label.pack(anchor='w')
        self.context_label = wrapping_label(self, text='Current — after the last event\n' + LEGEND,
                  style="Muted.TLabel")
        self.context_label.pack(fill="x", pady=(0, 8))
        global_panel = ttk.Frame(self)
        global_panel.pack(fill="x", pady=(0, 8))
        bar = ActionBar(global_panel)
        bar.pack(fill="x")
        self.actions = bar
        bar.add(ttk.Button(bar, text="Add relationship", command=self.edit, style="Primary.TButton"))
        bar.add(ttk.Button(bar, text="All relationship history", command=self.all_history,
                           style="Secondary.TButton"))
        bar.add(ttk.Button(bar, text="Explore graph", command=lambda: self.winfo_toplevel().tabs.select(self.winfo_toplevel().graph),
                           style="Navigation.TButton"))
        self.full_actions = list(bar.items)
        self.compact_menu = ttk.Menubutton(bar, text='More')
        compact_menu = tk.Menu(self.compact_menu, tearoff=False)
        compact_menu.add_command(label='All relationship history', command=self.all_history)
        compact_menu.add_command(label='Explore graph', command=lambda: self._root().tabs.select(self._root().graph))
        compact_menu.add_command(label='Direction legend', command=lambda: messagebox.showinfo('Relationship direction', LEGEND, parent=self))
        compact_menu.add_separator()
        compact_menu.add_command(label='Read selected connection…', command=self.read_selected)
        compact_menu.add_command(label='Correct selected entry…', command=self.edit_selected)
        compact_menu.add_command(label='Selected history / story change…', command=self.history)
        compact_menu.add_command(label='Consolidate selected reciprocal…', command=self.consolidate)
        compact_menu.add_command(label='Delete selected connection…', command=self.delete)
        self.compact_actions_menu = compact_menu
        self.compact_menu.configure(menu=compact_menu)
        self.undo_target = None
        self.undo_notice = ttk.Frame(global_panel, style="Context.TFrame", padding=6)
        ttk.Label(self.undo_notice, text="Relationship moved to Trash.", style="Context.TLabel").pack(side="left")
        self.undo_button = ttk.Button(self.undo_notice, text="Undo deletion", style="Secondary.TButton",
                                      command=self.undo_delete, state="disabled")
        self.undo_button.pack(side="right", padx=(12, 0))
        self.panes = ttk.Panedwindow(self, orient='horizontal')
        self.panes.pack(fill='both', expand=True)
        self.roster = RelationshipRoster(self.panes, self.select_character)
        right = ttk.Frame(self.panes, padding=(12, 0, 0, 0), style="Content.TFrame")
        self.content = right
        self.panes.add(self.roster, weight=1)
        self.panes.add(right, weight=3)
        self.panes.bind('<Configure>', self.restore_pane)
        self.heading = wrapping_label(right, text='Relationship list', style='Content.Heading.TLabel')
        self.selected_portrait = ttk.Label(right, style='Content.TLabel')
        self.selected_portrait.pack(anchor='w')
        self.heading.pack(fill='x')
        self.empty = wrapping_label(right, style="Content.Muted.TLabel")
        self.empty.pack(fill="x", pady=(6, 0))
        detail_panel = ttk.Frame(right, style="Detail.TFrame", padding=(4, 2))
        detail_panel.pack(fill='x', side='bottom')
        self.detail_panel = detail_panel
        self.selected_heading = ttk.Label(detail_panel, text="Selected connection", style="Detail.TLabel")
        self.selected_heading.pack(anchor="w")
        self.details = read_only_text_area(detail_panel, height=3)
        self.details.pack(fill='x')
        detail_actions = ActionBar(detail_panel)
        detail_actions.pack(fill="x", pady=(4, 0))
        self.detail_actions = detail_actions
        selected_actions = ttk.Menubutton(detail_actions, text="Selected actions", style="Secondary.TMenubutton", state="disabled")
        menu = tk.Menu(selected_actions, tearoff=False)
        menu.add_command(label='Read selected connection…', command=self.read_selected)
        menu.add_command(label="Correct entry", command=self.edit_selected)
        menu.add_command(label="History / story change…", command=self.history)
        menu.add_command(label="Consolidate reciprocal…", command=self.consolidate)
        selected_actions.configure(menu=menu)
        self.selected_actions_button = detail_actions.add(selected_actions)
        self.delete_button = detail_actions.add(ttk.Button(detail_actions, text="Delete", style="Danger.TButton",
                                                           command=self.delete, state="disabled"))
        self.tree = table(right, {"connection": "Connection / direction", "kind": "Type / inverse", "notes": "Notes"})
        self.tree.column('connection', width=260)
        self.tree.bind("<Double-1>", lambda _: self.edit_selected())
        self.tree.bind('<<TreeviewSelect>>', self.show_details)
        self.refresh()
        self.bind('<Configure>', self.compact_layout, add='+')

    def compact_layout(self, event=None):
        if event is not None and event.widget is not self:
            return
        compact = self._root().winfo_height() < 620
        if compact == getattr(self, '_compact', None):
            return
        self._compact = compact
        self.configure(padding=4 if compact else 16)
        self.title_label.pack_forget()
        if not compact:
            self.title_label.pack(anchor='w', before=self.context_label)
        self.context_label.configure(text='Current · Source → Target; mutual ↔' if compact else 'Current — after the last event\n' + LEGEND)
        for item in [*self.full_actions, self.compact_menu]:
            item.grid_forget()
        self.actions.items = [self.full_actions[0], self.compact_menu] if compact else list(self.full_actions)
        self.actions.reflow()
        self.show_details()
        self.refresh_heading()

    def refresh_heading(self):
        character = next((row for row in self.database.characters() if row['id'] == self.character_id), None)
        if character:
            label = f"{character['name']} (#{character['id']})"
            self.heading.configure(text=label + ' · connections' if getattr(self, '_compact', False) else f"Connections from {label}'s perspective")
        else:
            self.heading.configure(text='All relationships')

    def read_selected(self):
        if not self.tree.selection():
            return
        dialog = tk.Toplevel(self)
        dialog.title('Selected connection')
        dialog.geometry('560x360')
        dialog.transient(self._root())
        text = read_only_text_area(dialog)
        text.pack(fill='both', expand=True, padx=12, pady=12)
        set_read_only_text(text, self.details.get('1.0', 'end-1c'))
        ttk.Button(dialog, text='Close', command=dialog.destroy).pack(pady=8)
        dialog.bind('<Escape>', lambda _: dialog.destroy())

    def show_undo_notice(self):
        self.undo_button.state(["!disabled"])
        self.undo_notice.pack(fill="x", pady=(4, 0))

    def clear_undo(self):
        self.undo_target = None
        self.undo_button.state(["disabled"])
        self.undo_notice.pack_forget()

    def refresh(self):
        if self.database.path != self.database_path:
            self.database_path = self.database.path
            self.character_id = None
            self.roster.query.set('')
            self.clear_undo()
        selection = self.tree.selection()
        characters = self.database.characters()
        character = next((row for row in characters if row['id'] == self.character_id), None)
        if character is None:
            self.character_id = None
        self.roster.refresh(characters, self.character_id)
        if character:
            label = f"{character['name']} (#{character['id']})"
            self.heading.configure(text=f"Connections from {label}'s perspective")
            from .tree_art import portrait_photo
            self.selected_portrait.image = portrait_photo(self.selected_portrait, self.database, character.get('portrait', ''))
            self.selected_portrait.configure(image=self.selected_portrait.image or '')
            if self.selected_portrait.image:
                self.selected_portrait.pack(anchor='w', before=self.heading)
            else:
                self.selected_portrait.pack_forget()
        else:
            self.heading.configure(text="All relationships")
            self.selected_portrait.pack_forget()
        self.refresh_heading()
        self.rows = {str(row['id']): row for row in self.database.relationships()
                     if self.character_id is None or self.character_id in (row['source_id'], row['target_id'])}
        self.empty.configure(text='' if self.rows else 'No connections here yet. Add a relationship; you can create missing characters inside the form.')
        self.empty.pack_forget()
        if not self.rows:
            self.empty.pack(fill='x', before=self.tree.master, pady=(6, 0))
        self.tree.delete(*self.tree.get_children())
        for key, row in self.rows.items():
            self.tree.insert("", "end", iid=key, values=(relationship_list_label(row, self.character_id),
                                                           relationship_list_type(row, self.character_id), row['notes']))
        if selection and selection[0] in self.rows:
            self.tree.selection_set(selection[0])
        self.show_details()

    def select_character(self, ident):
        self.character_id = ident
        self.refresh()

    def select_relationship(self, ident):
        row = next((row for row in self.database.relationships() if row['id'] == ident), None)
        if row is None:
            return False
        if self.character_id not in (row['source_id'], row['target_id']):
            self.character_id = row['source_id']
        self.roster.query.set('')
        self.refresh()
        self.tree.selection_set(str(ident))
        self.tree.focus(str(ident))
        self.tree.see(str(ident))
        self.show_details()
        return True

    def show_details(self, _event=None):
        selected = self.tree.selection()
        row = self.rows.get(selected[0]) if selected else None
        text = f"{relationship_details(row, self.character_id)}\n{row['notes'] or 'No notes.'}" if row else 'Select a connection to inspect or edit its exact record.'
        set_read_only_text(self.details, text)
        self.details.pack_forget()
        self.selected_heading.pack_forget()
        if not getattr(self, '_compact', False):
            self.selected_heading.pack(anchor='w', before=self.detail_actions)
            self.details.pack(fill='x', before=self.detail_actions)
        for button in (self.selected_actions_button, self.delete_button):
            button.state(["!disabled" if row else "disabled"])
        for index in range(4, 9):
            self.compact_actions_menu.entryconfigure(index, state='normal' if row else 'disabled')
        if row and not getattr(self, '_compact', False):
            # Restore it before the expanding table so a later selection cannot
            # leave the panel squeezed to one pixel by pack's order.
            self.detail_panel.pack(fill="x", side="bottom", before=self.tree.master)
        else:
            self.detail_panel.pack_forget()

    def restore_pane(self, _event=None):
        width = self.panes.winfo_width()
        if width < 100:
            return
        if not self._pane_restored:
            desired = self.winfo_toplevel().settings.values['relationship_roster_width']
            self.panes.sashpos(0, min(desired, width // 2))
            self._pane_restored = True
        elif self.panes.sashpos(0) > width // 2:
            self.panes.sashpos(0, width // 2)

    def edit_selected(self):
        if self.tree.selection():
            self.edit(self.rows[self.tree.selection()[0]])

    def history(self):
        ident = int(self.tree.selection()[0]) if self.tree.selection() else None
        return HistoryDialog(self, self.database, self.changed, ident)

    def all_history(self):
        """Ended connections remain reachable even with no current row selected."""
        return HistoryDialog(self, self.database, self.changed)

    def consolidate(self):
        if self.tree.selection():
            return ConsolidationDialog(self, self.database, self.changed, self.rows[self.tree.selection()[0]])
        messagebox.showinfo("Select a relationship", "Select one directional record to find its reciprocal records.", parent=self)

    def delete(self):
        if self.tree.selection() and messagebox.askyesno("Move to Trash", "Move the selected relationship to Trash? You can restore it from Recovery.", parent=self):
            self.database.delete_relationship(int(self.tree.selection()[0]))
            self.undo_target = int(self.tree.selection()[0])
            self.show_undo_notice()
            self.changed("Relationship moved to Trash.")

    def undo_delete(self):
        if self.undo_target is None:
            return
        try:
            self.database.trash.restore("relationship", self.undo_target)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot undo deletion", f"The relationship remains in Trash: {error}", parent=self)
            return
        self.clear_undo()
        self.changed("Relationship restored from Trash.")

    def edit(self, row=None):
        return RelationshipDialog(self, self.database, self.changed, row)
