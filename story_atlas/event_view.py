"""Chronological story events and a small modal event editor."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .widgets import (table, text_area, wrapping_label, ActionBar,
                      read_only_text_area, set_read_only_text)
from .theme import style_tree
from .scroll_frame import ScrollFrame
from .relationship_semantics import connection_label
from .history_dialog import StateDialog, HistoryDialog
from .chapter_dialog import ChapterDialog, ChapterPicker
from .goals_view import ParticipantGoalsDialog
from .chronology_preview import confirm_preview
from .event_detail_state import capture, restore
from .event_context import EventContext
from .illustrated_widgets import IllustratedLabel
from .ui_assets import decorate


class EventView(EventContext, ttk.Frame):
    def __init__(self, parent, database, changed):
        # Keep chapters, events, and the selected event visible together.
        super().__init__(parent, padding=(8, 6))
        self.database, self.changed = database, changed
        self.database_path = database.path
        self.chapter_id = 'all'
        IllustratedLabel(self, 'section.chapter', text="Chapters & story events", size=24).pack(anchor="w", pady=(0, 2))
        self.actions = ActionBar(self)
        self.actions.pack(fill="x")
        self.new_event_button = self.actions.add(ttk.Button(self.actions, text="New event", style="Primary.TButton", command=self.edit))
        self.actions.add(ttk.Button(self.actions, text='New chapter', style='Secondary.TButton', command=self.new_chapter))
        self.chapter_choice = tk.StringVar(self, 'All chapters')
        # Kept as a programmatic selector for existing callers; the outline is the visible workspace.
        self.chapter_box = ttk.Combobox(self, textvariable=self.chapter_choice, state='readonly')
        self.chapter_box.bind('<<ComboboxSelected>>', self.choose_chapter)
        self.more_actions = ttk.Menubutton(self.actions, text="More actions", style="Secondary.TMenubutton")
        more_menu = tk.Menu(self.more_actions, tearoff=False)
        more_menu.add_command(label="Move earlier", command=lambda: self.move(-1))
        more_menu.add_command(label="Move later", command=lambda: self.move(1))
        more_menu.add_separator()
        more_menu.add_command(label='Edit selected chapter', command=self.edit_chapter)
        more_menu.add_command(label='Move chapter earlier', command=lambda: self.move_chapter(-1))
        more_menu.add_command(label='Move chapter later', command=lambda: self.move_chapter(1))
        more_menu.add_separator()
        self.more_actions.configure(menu=more_menu)
        self.actions.add(self.more_actions)
        self.workspace = ttk.Panedwindow(self, orient="horizontal")
        self.workspace.pack(fill="both", expand=True, pady=4)
        self.outline_frame = ttk.Frame(self.workspace)
        self.event_frame = ttk.Frame(self.workspace)
        self.detail = ttk.Frame(self.workspace, style="Detail.TFrame", padding=8)
        self.workspace.add(self.outline_frame, weight=1)
        self.workspace.add(self.event_frame, weight=2)
        self.workspace.add(self.detail, weight=2)
        self.detail_heading = tk.StringVar(self, "Event details")
        self.detail_heading_label = wrapping_label(self.detail, textvariable=self.detail_heading, style="Heading.TLabel", font='AtlasHeading')
        decorate(self.detail_heading_label, 'section.event', 24)
        self.detail_heading_label.pack(fill='x', pady=(0, 4))
        self.detail_text = tk.StringVar(self, "Select an event to view its overview.")
        self.detail_actions = ActionBar(self.detail)
        self.detail_actions.pack(fill="x", pady=(0, 4))
        self.destination_target = None
        self.destination_button = ttk.Button(self.detail, text="Open destination chapter", style="Navigation.TButton",
                                             command=self.open_destination)
        self.add_change_button = self.detail_actions.add(ttk.Button(self.detail_actions, text="Record change", style="Primary.TButton",
                                                                     command=self.add_relationship_change, state="disabled"))
        self.start_relationship_button = self.detail_actions.add(ttk.Button(
            self.detail_actions, text="Start relationship", style="Secondary.TButton",
            command=self.connect_characters, state="disabled"))
        self.detail_graph_button = self.detail_actions.add(ttk.Button(self.detail_actions, text="Graph at event", style="Navigation.TButton",
                                                                      command=self.show_graph, state="disabled"))
        self.detail_action_menu = ttk.Menubutton(self.detail, text="Event actions", style="Secondary.TMenubutton")
        self.detail_menu = tk.Menu(self.detail_action_menu, tearoff=False)
        self.detail_menu.add_command(label="Record change", command=self.add_relationship_change)
        self.detail_menu.add_command(label="Start relationship", command=self.connect_characters)
        self.detail_menu.add_command(label="Graph at event", command=self.show_graph)
        self.detail_action_menu.configure(menu=self.detail_menu)
        self.detail_scroller = ScrollFrame(self.detail)
        self.detail_scroller.pack(fill="both", expand=True)
        content = self.detail_scroller.content
        self.description_heading = tk.StringVar(self, "Description")
        IllustratedLabel(content, 'section.story', size=24, textvariable=self.description_heading).pack(anchor="w", pady=(0, 4))
        self.detail_body = read_only_text_area(content, height=4)
        self.detail_body.pack(fill="x", pady=(0, 12))
        set_read_only_text(self.detail_body, self.detail_text.get())
        self.cast_section = ttk.Frame(content)
        self.cast_heading = tk.StringVar(self, "Characters active in this event")
        ttk.Label(self.cast_section, textvariable=self.cast_heading, style="Heading.TLabel").pack(anchor="w", pady=(0, 4))
        self.cast_body = read_only_text_area(self.cast_section, height=4)
        self.cast_body.pack(fill="x", pady=(0, 12))
        self.goals_section = ttk.Frame(content)
        self.goals_heading = tk.StringVar(self, "Characters and current goals")
        IllustratedLabel(self.goals_section, 'section.goals', size=24, textvariable=self.goals_heading).pack(anchor="w", pady=(0, 4))
        goals_frame = ttk.Frame(self.goals_section)
        goals_frame.pack(fill="x", pady=(0, 12))
        self.goals_tree = ttk.Treeview(goals_frame, show="tree", height=6, selectmode="browse")
        self.goals_tree.column("#0", width=260, minwidth=130)
        self.goals_tree.grid(row=0, column=0, sticky="nsew")
        goals_scroll = ttk.Scrollbar(goals_frame, orient="vertical", command=self.goals_tree.yview)
        goals_scroll.grid(row=0, column=1, sticky="ns")
        goals_horizontal = ttk.Scrollbar(goals_frame, orient="horizontal", command=self.goals_tree.xview)
        goals_horizontal.grid(row=1, column=0, sticky="ew")
        goals_frame.columnconfigure(0, weight=1)
        goals_frame.rowconfigure(0, weight=1)
        self.goals_tree.configure(yscrollcommand=goals_scroll.set, xscrollcommand=goals_horizontal.set)
        self.changes_section = ttk.Frame(content)
        self.changes_heading = tk.StringVar(self, "Relationship changes")
        ttk.Label(self.changes_section, textvariable=self.changes_heading, style="Heading.TLabel").pack(anchor="w", pady=(0, 4))
        wrapping_label(self.changes_section, text="Changes recorded here; relationships merely active at this event are excluded.",
                       style="Muted.TLabel").pack(fill="x", pady=(0, 4))
        change_frame = ttk.Frame(self.changes_section)
        change_frame.pack(fill="x")
        self.change_tree = ttk.Treeview(change_frame, show="tree", height=7, selectmode="browse")
        self.change_tree.column("#0", width=260, minwidth=130)
        self.change_tree.grid(row=0, column=0, sticky="nsew")
        change_scroll = ttk.Scrollbar(change_frame, orient="vertical", command=self.change_tree.yview)
        change_scroll.grid(row=0, column=1, sticky="ns")
        change_horizontal = ttk.Scrollbar(change_frame, orient="horizontal", command=self.change_tree.xview)
        change_horizontal.grid(row=1, column=0, sticky="ew")
        change_frame.columnconfigure(0, weight=1)
        change_frame.rowconfigure(0, weight=1)
        self.change_tree.configure(yscrollcommand=change_scroll.set, xscrollcommand=change_horizontal.set)
        self.detail.bind("<Configure>", self.resize_detail_actions)
        self.outline = table(self.outline_frame, {"chapter": "Chapters"})
        self.outline.column("chapter", width=190, minwidth=120)
        self.outline.bind("<<TreeviewSelect>>", self.choose_outline)
        from .tree_art import install_tree_art
        self.refresh_outline_art = install_tree_art(self.outline,
            lambda: {f"chapter:{row['id']}": row for row in self.database.chapters.list()},
            lambda: self.database, lambda row: 'section.chapter')
        self.tree = table(self.event_frame, {"title": "Events in chapter"})
        self.tree.master.pack_configure(pady=2)
        self.tree.column("title", width=220, minwidth=120)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)
        self.tree.bind("<Double-1>", lambda _: self.edit_selected())
        self.tree.bind("<Return>", lambda _: self.edit_selected())
        self.refresh_event_art = install_tree_art(self.tree, lambda: self.rows,
            lambda: self.database, lambda row: 'section.event')
        self.setup_reading()
        self.refresh()

    def resize_detail_actions(self, event=None):
        """Keep details readable and their actions reachable in a short window."""
        required_width = max(button.winfo_reqwidth() for button in self.detail_actions.items) + 16
        compact = self.detail.winfo_height() < 220 or self.detail.winfo_width() < required_width
        if compact == getattr(self, '_compact_detail', None):
            return
        self._compact_detail = compact
        if compact:
            self.detail_heading_label.pack_forget()
            self.detail_actions.pack_forget()
            self.detail_action_menu.pack(fill="x", before=self.detail_scroller, pady=(0, 4))
        else:
            self.detail_action_menu.pack_forget()
            self.detail_heading_label.pack(fill='x', before=self.detail_scroller, pady=(0, 4))
            self.detail_actions.pack(fill="x", before=self.detail_scroller, pady=(0, 4))

    def refresh(self):
        selected = self.tree.selection()
        if self.database.path != self.database_path:
            selected = ()
            self.chapter_id = 'all'
            self.database_path = self.database.path
        chapters = self.database.chapters.list()
        all_events = self.database.events.list()
        self.chapter_choices = {'All chapters': 'all', 'Unassigned events': None}
        self.chapter_choices.update({f"{row['title']} (#{row['id']})": row['id'] for row in chapters})
        if self.chapter_id not in self.chapter_choices.values():
            self.chapter_id = 'all'
        self.chapter_box.configure(values=tuple(self.chapter_choices))
        self.chapter_choice.set(next(key for key, value in self.chapter_choices.items() if value == self.chapter_id))
        self._refreshing_outline = True
        self.outline.delete(*self.outline.get_children())
        self.outline.insert('', 'end', iid='all', values=('All chapters',))
        for chapter in chapters:
            self.outline.insert('', 'end', iid=f"chapter:{chapter['id']}",
                                values=(f"{chapter['title']} (#{chapter['id']})",))
        self.outline.insert('', 'end', iid='unassigned', values=('Unassigned',))
        outline_key = 'all' if self.chapter_id == 'all' else 'unassigned' if self.chapter_id is None else f'chapter:{self.chapter_id}'
        self.outline.selection_set(outline_key)
        self.outline.see(outline_key)
        self.refresh_outline_art()
        self._refreshing_outline = False
        self.rows = {str(row["id"]): row for row in all_events
                     if self.chapter_id == 'all' or row['chapter_id'] == self.chapter_id}
        chapter_names = {row['id']: row['title'] for row in chapters}
        self.tree.delete(*self.tree.get_children())
        for key, row in self.rows.items():
            title = row["title"]
            if self.chapter_id == 'all':
                title = f"{chapter_names.get(row['chapter_id'], 'Unassigned')} / {title}"
            self.tree.insert("", "end", iid=key, values=(title,))
        self.refresh_event_art()
        if selected and selected[0] in self.rows:
            self.tree.selection_set(selected[0])
        self.show_details()
        if self.destination_target and self.destination_target[0] != self.database.path:
            self.destination_target = None
            self.destination_button.pack_forget()

    def choose_outline(self, _event=None):
        if getattr(self, '_refreshing_outline', False) or not self.outline.selection():
            return
        key = self.outline.selection()[0]
        selected = 'all' if key == 'all' else None if key == 'unassigned' else int(key.split(':')[1])
        if selected == self.chapter_id:
            return
        self.chapter_id = selected
        self.refresh()

    def reveal_chapter(self, chapter_id, story_path=None):
        if story_path is not None and story_path != self.database.path:
            return False
        if chapter_id not in ('all', None) and chapter_id not in {row['id'] for row in self.database.chapters.list()}:
            return False
        self.chapter_id = chapter_id
        self.refresh()
        self.winfo_toplevel().tabs.select(self)
        return True

    def restore_selection(self, chapter_id, selection):
        """Restore only IDs belonging to the newly installed story, without navigation."""
        known = {row['id'] for row in self.database.chapters.list()}
        self.chapter_id = chapter_id if chapter_id in ('all', None) or chapter_id in known else 'all'
        self.tree.selection_remove(*self.tree.selection())
        self.refresh()
        if selection and selection[0] in self.rows:
            self.tree.selection_set(selection[0])
            self.tree.focus(selection[0])
            self.tree.see(selection[0])
        self.show_details()

    def reveal_event(self, event_id, story_path=None):
        if story_path is not None and story_path != self.database.path:
            return False
        event = next((row for row in self.database.events.list() if row['id'] == event_id), None)
        if event is None or not self.reveal_chapter(event['chapter_id'], self.database.path):
            return False
        self.tree.selection_set(str(event_id))
        self.tree.see(str(event_id))
        self.show_details()
        return True

    def show_details(self, _event=None):
        self.new_event_button.configure(style='Secondary.TButton' if self.tree.selection() else 'Primary.TButton')
        if not self.tree.selection():
            chapter = next((row for row in self.database.chapters.list() if row['id'] == self.chapter_id), None)
            self.detail_heading.set("Chapter overview" if chapter else "Event overview")
            self.description_heading.set("Chapter description" if chapter else "Description")
            self.set_detail_text(f"{chapter['title']}\n\n{chapter['summary'] or 'No chapter summary.'}\n\nChoose New event to add an event to this chapter."
                                 if chapter else "Select an event to view its description, characters, goals, and relationship changes.")
            self.clear_event_sections()
            self.add_change_button.state(["disabled"])
            self.start_relationship_button.state(["disabled"])
            self.detail_graph_button.state(["disabled"])
            for index in range(3):
                self.detail_menu.entryconfig(index, state="disabled")
            return
        event = self.rows.get(self.tree.selection()[0])
        if event is None:
            self.detail_heading.set("Event overview")
            self.set_detail_text("That event is no longer available.")
            self.clear_event_sections()
            self.add_change_button.state(["disabled"])
            self.start_relationship_button.state(["disabled"])
            self.detail_graph_button.state(["disabled"])
            for index in range(3):
                self.detail_menu.entryconfig(index, state="disabled")
            return
        self.add_change_button.state(["!disabled"])
        self.start_relationship_button.state(["!disabled"])
        self.detail_graph_button.state(["!disabled"])
        for index in range(3):
            self.detail_menu.entryconfig(index, state="normal")
        self.detail_heading.set(event['title'])
        self.description_heading.set("Description")
        chapter = next((row['title'] for row in self.database.chapters.list()
                        if row['id'] == event['chapter_id']), 'Unassigned')
        self.set_detail_text(f"After: {chapter} / {event['title']}\n\n{event['summary'] or 'No description.'}")
        self.show_event_sections(event)

    def clear_event_sections(self):
        self._rendered_event = None
        self.cast_section.pack_forget()
        self.goals_section.pack_forget()
        self.changes_section.pack_forget()
        self.goals_tree.delete(*self.goals_tree.get_children())
        self.change_tree.delete(*self.change_tree.get_children())
        self.read_goal()
        self.read_change()

    def show_event_sections(self, event):
        """Show current goals and event changes grouped under each involved character."""
        key = (str(self.database.path), event['id'])
        previous = [capture(tree) for tree in (self.goals_tree, self.change_tree)] if getattr(self, '_rendered_event', None) == key else None
        self._rendered_event = key
        self.cast_section.pack(fill="x")
        self.goals_section.pack(fill="x")
        self.changes_section.pack(fill="x")
        characters = {row['id']: dict(row) for row in self.database.connection.execute(
            "SELECT id,name,goals,deleted_at FROM characters")}
        participant_ids = list(dict.fromkeys(row['character_id'] for row in self.database.events.participants()
                                            if row['event_id'] == event['id']))
        self.cast_heading.set(f"Characters active in this event ({len(participant_ids)})")
        cast_lines = []
        self.goals_heading.set(f"Current goals ({len(participant_ids)} characters)")
        self.goals_tree.delete(*self.goals_tree.get_children())
        for ident in participant_ids:
            character = characters.get(ident)
            name = character['name'] + (' [Trash]' if character['deleted_at'] else '') if character else 'Missing character'
            label = name
            cast_lines.append(f"• {label}")
            parent = self.goals_tree.insert('', 'end', iid=f'character:{ident}', text=label, open=True)
            goals = [line for line in character['goals'].splitlines() if line.strip()] if character else []
            for index, goal in enumerate(goals or ["No saved goals."]):
                self.goals_tree.insert(parent, 'end', iid=f'{parent}:goal:{index}', text=goal if len(goal) <= 90 else goal[:87] + '…')
        set_read_only_text(self.cast_body, "\n".join(cast_lines) if cast_lines else "No characters marked active in this event.")
        if not participant_ids:
            self.goals_tree.insert('', 'end', iid='empty', text="No participating characters.")
        changes = [dict(row) for row in self.database.history.rows() if row['event_id'] == event['id']]
        self.changes_heading.set(f"Relationship changes ({len(changes)})")
        self.change_tree.delete(*self.change_tree.get_children())
        involved_ids = list(participant_ids)
        for change in changes:
            for ident in (change['source_id'], change['target_id']):
                if ident not in involved_ids:
                    involved_ids.append(ident)
        if not involved_ids:
            self.change_tree.insert('', 'end', iid='empty', text="No characters or relationship changes recorded.")
        for ident in involved_ids:
            character = characters.get(ident)
            name = character['name'] + (' [Trash]' if character['deleted_at'] else '') if character else 'Missing character'
            own_changes = [change for change in changes if ident in (change['source_id'], change['target_id'])]
            label = f"{name} · {len(own_changes)} change{'s' if len(own_changes) != 1 else ''}"
            parent = self.change_tree.insert('', 'end', iid=f'character:{ident}', text=label, open=True)
            if not own_changes:
                self.change_tree.insert(parent, 'end', iid=f'{parent}:empty', text="No relationship changes recorded here.")
            for change in own_changes:
                change.update(source_name=characters.get(change['source_id'], {}).get('name', f"#{change['source_id']}"),
                              target_name=characters.get(change['target_id'], {}).get('name', f"#{change['target_id']}"))
                change_key = f"{parent}:change:{change['id']}"
                self.change_tree.insert(parent, 'end', iid=change_key, open=True,
                                        text=f"{'Present' if change['active'] else 'Ended'} — {connection_label(change)}")
                for index, line in enumerate(change['notes'].splitlines() or ['No notes.']):
                    self.change_tree.insert(change_key, 'end', iid=f'{change_key}:note:{index}', text=line if len(line) <= 90 else line[:87] + '…')
        if previous:
            for tree, state in zip((self.goals_tree, self.change_tree), previous):
                restore(tree, state)
        self.read_goal()
        self.read_change()

    def set_detail_text(self, text):
        """Keep the testable text value and selectable detail surface in sync."""
        self.detail_text.set(text)
        set_read_only_text(self.detail_body, text)

    def choose_chapter(self, _event=None):
        self.chapter_id = self.chapter_choices[self.chapter_choice.get()]
        self.refresh()

    def chapter_saved(self, ident):
        self.chapter_id = ident
        self.changed('Chapter saved')

    def new_chapter(self):
        return ChapterDialog(self, self.database, self.chapter_saved)

    def edit_chapter(self):
        row = next((row for row in self.database.chapters.list() if row['id'] == self.chapter_id), None)
        if row:
            return ChapterDialog(self, self.database, self.chapter_saved, row)
        messagebox.showinfo('Choose a chapter', 'Choose a chapter in the chapter selector first.', parent=self)

    def move_chapter(self, offset):
        if self.chapter_id in ('all', None):
            messagebox.showinfo('Choose a chapter', 'Choose a chapter first.', parent=self)
            return
        try:
            while True:
                preview = self.database.chapters.preview_move(self.chapter_id, offset)
                if not confirm_preview(self, preview):
                    return
                try:
                    self.database.chapters.move(self.chapter_id, offset, expected=preview)
                    self.changed('Chapters reordered')
                    return
                except ValueError as error:
                    if 'since the preview' not in str(error):
                        raise
                    messagebox.showinfo('Chronology changed', str(error), parent=self)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror('Cannot reorder chapter', str(error), parent=self)

    def add_relationship_change(self):
        if self.tree.selection():
            return EventRelationshipChangeDialog(self, self.database, self.changed, self.rows[self.tree.selection()[0]], self.change_recorded)

    def connect_characters(self):
        from .relationship_dialog import RelationshipDialog
        event = self.rows.get(self.tree.selection()[0]) if self.tree.selection() else None
        return RelationshipDialog(self, self.database, self.changed,
                                  context_event_id=event["id"] if event else None)

    def change_recorded(self, message):
        self.changed(message)
        self.show_details()

    def edit(self, row=None):
        return EventDialog(self, self.database, self.changed, row,
                           self.chapter_id if self.chapter_id != 'all' else None, moved=self.event_moved)

    def event_moved(self, event_id, chapter_id):
        self.destination_target = (self.database.path, chapter_id, event_id)
        label = next((row['title'] for row in self.database.chapters.list() if row['id'] == chapter_id), 'Unassigned')
        self.destination_button.configure(text=f"Open destination chapter: {label}")
        self.destination_button.pack(anchor='w', before=self.detail_scroller, pady=2)
        self.clear_event_sections()
        self.detail_heading.set("Event moved")
        self.description_heading.set("New location")
        self.set_detail_text(f"Event saved in {label}. Open the destination chapter to see it in its new position.")

    def open_destination(self):
        target = self.destination_target
        if target and self.reveal_event(target[2], target[0]):
            self.destination_target = None
            self.destination_button.pack_forget()
        else:
            self.set_detail_text('That destination is no longer available in this story.')
            self.destination_button.pack_forget()

    def edit_selected(self):
        if self.tree.selection():
            return self.edit(self.rows[self.tree.selection()[0]])

    def move(self, offset):
        if not self.tree.selection():
            return
        if not messagebox.askyesno("Reorder story", "Exchange this event's order with its neighbor? This recalculates relationship history and Current state.", parent=self):
            return
        try:
            self.database.events.move(int(self.tree.selection()[0]), offset)
            self.changed("Story chronology reordered")
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot reorder", str(error), parent=self)

    def show_graph(self):
        if self.tree.selection():
            self.winfo_toplevel().navigation.open_graph_from_event(int(self.tree.selection()[0]))



# Compatibility exports for existing callers. The page owns navigation only.
from .event_change_dialog import EventRelationshipChangeDialog
from .event_editor import EventDialog
