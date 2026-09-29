"""Batch relationship entry with explicit validation and safe close behavior."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from .models import RELATIONSHIP_TYPES
from .searchable_combo import SearchableCombobox
from .widgets import text_area, wrapping_label, ActionBar
from .scroll_frame import ScrollFrame
from .graph_legend import category_for
from .theme import style_tree
from .relationship_semantics import normalize, perspectives
from .quick_character import QuickCharacterDialog
from .chapters import event_label
from .history_dialog import HistoryDialog


class RelationshipDialog(tk.Toplevel):
    def __init__(self, parent, database, changed, row=None, context_source_id=None, context_event_id=None):
        super().__init__(parent)
        self.database, self.changed = database, changed
        self.relationship_id = row["id"] if row else None
        self.context_source_id = context_source_id if row is None else None
        self.context_event_id = context_event_id if row is None else None
        self.context_story = database.path
        self.last_saved_id = None
        self.title("Edit relationship" if row else "New relationship")
        self.geometry("620x650")
        self.minsize(420, 340)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _: self.close())
        self.bind("<Control-Return>", self.save_shortcut)
        self.bind("<Control-KP_Enter>", self.save_shortcut)
        self.choices = {f"{c['name']} (#{c['id']})": c["id"] for c in database.characters()}
        self.variables = {field: tk.StringVar(self) for field in ("source", "target", "kind", "semantics", "inverse_label", "start_event")}
        self.category = tk.StringVar(self, category_for(row or {}, self))
        self.original_category = (row or {}).get('category', '')
        self.category_changed = False
        self.category.trace_add('write', lambda *_: setattr(self, 'category_changed', True))
        self.errors = {field: tk.StringVar(self) for field in ("source", "target", "kind", "semantics")}
        self.boxes = {}
        self.create_buttons = {}
        self.preview = tk.StringVar(self)
        self.status = tk.StringVar(self)
        self.scroller = ScrollFrame(self)
        self.scroller.pack(fill="both", expand=True, padx=16, pady=12)
        frame = self.scroller.content
        ttk.Label(frame, text=self.title(), style="Heading.TLabel").pack(anchor="w", pady=(0, 8))
        wrapping_label(frame, text="Type to filter, then press Down and Enter to select. Add relationship saves, clears all fields, and stays open.",
                  style="Muted.TLabel").pack(fill="x", pady=(0, 10))
        self.event_context = tk.StringVar(self)
        self.use_event_button = None
        if self.context_event_id is not None:
            wrapping_label(frame, textvariable=self.event_context, style="Detail.TLabel").pack(fill="x", pady=(0, 8))
            self.use_event_button = ttk.Button(frame, text="Use this event as beginning", style="Secondary.TButton",
                                               command=self.use_context_event)
            self.use_event_button.pack(anchor="w", pady=(0, 8))
            self.refresh_event_context()
        self.use_source_button = None
        if self.context_source_id is not None:
            source_label = next((label for label, ident in self.choices.items() if ident == self.context_source_id), None)
            if source_label:
                name = next(row["name"] for row in database.characters() if row["id"] == self.context_source_id)
                self.use_source_button = ttk.Button(frame, text=f"Use {name} as Source", style="Secondary.TButton",
                                                    command=lambda: self.use_context_source(source_label))
                self.use_source_button.pack(anchor="w", pady=(0, 8))
        for field, label in (("source", "Source · from character"), ("target", "Target · to character"), ("kind", "Type (choose or enter your own)")):
            label_row = ttk.Frame(frame)
            label_row.pack(fill="x")
            ttk.Label(label_row, text=label).pack(side="left")
            if field in ("source", "target"):
                button = ttk.Button(label_row, text="Create character…", style="Secondary.TButton", takefocus=False,
                                    command=lambda field=field: self.create_character(field))
                button.pack(side="right")
                self.create_buttons[field] = button
            choices = self.type_choices() if field == "kind" else self.choices
            box = SearchableCombobox(frame, self.variables[field], choices)
            box.pack(fill="x", pady=(4, 0))
            self.boxes[field] = box
            wrapping_label(frame, textvariable=self.errors[field], style="Validation.TLabel").pack(fill="x")
            self.variables[field].trace_add("write", lambda *_, field=field: self.field_changed(field))
        from .graph_legend import EDGE_STYLES
        ttk.Label(frame, text='Link category · legend color').pack(anchor='w')
        self.boxes['category'] = ttk.Combobox(frame, textvariable=self.category, values=tuple(EDGE_STYLES), state='readonly')
        self.boxes['category'].pack(fill='x', pady=4)
        ttk.Label(frame, text="Meaning (required) · Directional → one-way / Mutual ↔ shared").pack(anchor="w")
        self.boxes["semantics"] = ttk.Combobox(frame, textvariable=self.variables["semantics"],
                                               values=("Directional", "Mutual"), state="readonly")
        self.boxes["semantics"].pack(fill="x", pady=4)
        wrapping_label(frame, textvariable=self.errors["semantics"], style="Validation.TLabel").pack(fill="x")
        self.variables["semantics"].trace_add("write", lambda *_: self.field_changed("semantics"))
        self.inverse_frame = ttk.Frame(frame)
        self.inverse_frame.pack(fill="x")
        ttk.Label(self.inverse_frame, text="Inverse label (optional, Directional only)").pack(anchor="w")
        self.boxes["inverse_label"] = SearchableCombobox(self.inverse_frame, self.variables["inverse_label"],
                                                        ("Mentee", "Employee", *self.type_choices()))
        self.boxes["inverse_label"].pack(fill="x", pady=4)
        self.variables["inverse_label"].trace_add("write", lambda *_: self.update_preview())
        self.optional_toggle = ttk.Button(frame, text="Timing and notes ▸", command=self.toggle_optional)
        self.optional_toggle.pack(anchor="w", pady=4)
        self.optional_frame = ttk.Frame(frame)
        self.optional_open = False
        self.event_choices = {event_label(database, event): event["id"] for event in database.events.list()}
        ttk.Label(self.optional_frame, text="Begins at event (optional; blank = present before first event)").pack(anchor="w")
        self.boxes["start_event"] = ttk.Combobox(self.optional_frame, textvariable=self.variables["start_event"],
                                                values=("", *self.event_choices), state="disabled" if row else "readonly")
        self.boxes["start_event"].pack(fill="x", pady=4)
        if row:
            entry = database.history.editing_state(self.relationship_id)
            event = next((item for item in database.events.list() if item['id'] == entry['event_id']), None)
            target = f"state #{entry['id']} at {event_label(database, event)}" if event else 'baseline (undated)'
            status = 'Present' if entry['active'] else 'Absent / ended'
            wrapping_label(frame, text=f"Current correction: updates {target} · {status}. Use History to correct an earlier entry or record a story change.").pack(fill="x", pady=6)
        preview_panel = ttk.Frame(frame, style="Detail.TFrame", padding=6)
        preview_panel.pack(fill="x", pady=(4, 10))
        ttk.Label(preview_panel, text="Relationship preview", style="Detail.TLabel").pack(anchor="w")
        wrapping_label(preview_panel, textvariable=self.preview, style="Detail.TLabel").pack(fill="x")
        ttk.Label(self.optional_frame, text="Context / how this relationship evolved").pack(anchor="w")
        self.notes = text_area(self.optional_frame, height=5)
        self.notes.pack(fill="both", expand=True, pady=8)
        # Tab navigates instead of inserting an invisible tab into the notes.
        self.notes.bind("<Tab>", lambda _: self.move_from_notes(False))
        self.notes.bind("<Shift-Tab>", lambda _: self.move_from_notes(True))
        self.notes.bind("<Control-Return>", self.save_shortcut)
        self.notes.bind("<Control-KP_Enter>", self.save_shortcut)
        footer = ttk.Frame(self, padding=12)
        self.footer = footer
        footer.pack(side="bottom", fill="x")
        self.status_label = wrapping_label(footer, textvariable=self.status,
                                           style="Muted.TLabel")
        self.status_label.pack(fill="x", pady=4)
        buttons = ActionBar(footer)
        buttons.pack(fill="x")
        self.scroller.pack_forget()
        self.scroller.pack(fill="both", expand=True, padx=16, pady=12)
        self.save_button = ttk.Button(buttons, text="Save correction" if row else "Add relationship", style="Primary.TButton", command=self.save)
        buttons.add(self.save_button)
        self.close_button = ttk.Button(buttons, text="Return to event" if self.context_event_id is not None else "Close",
                                       style="Secondary.TButton", command=self.close)
        buttons.add(self.close_button)
        self.inspect_saved_button = None
        if self.context_event_id is not None:
            self.inspect_saved_button = ttk.Button(buttons, text="Inspect saved relationship here",
                                                   style="Navigation.TButton", command=self.inspect_saved, state="disabled")
            buttons.add(self.inspect_saved_button)
        if row:
            for field in ("source", "target"):
                label = next((label for label, ident in self.choices.items() if ident == row[f"{field}_id"]), "")
                self.variables[field].set(label)
            self.variables["kind"].set(row["kind"])
            self.variables["semantics"].set(row.get("semantics", "directional").title())
            self.variables["inverse_label"].set(row.get("inverse_label", ""))
            self.notes.insert("1.0", row["notes"])
        if row and (row.get('notes') or row.get('inverse_label')):
            self.toggle_optional()
        self.original = self.values()
        self.update_preview()
        style_tree(self)
        self.grab_set()
        self.focus_job = self.after_idle(self.boxes["source"].focus_set)

    def destroy(self):
        job = getattr(self, "focus_job", None)
        if job:
            self.after_cancel(job)
            self.focus_job = None
        super().destroy()

    def type_choices(self):
        return sorted(set(RELATIONSHIP_TYPES) | {value for row in self.database.relationships()
                      for value in (row["kind"], row.get("inverse_label", "")) if value}, key=str.casefold)

    def use_context_source(self, label):
        """Apply profile context only after an intentional user action."""
        self.variables["source"].set(label)
        self.boxes["source"].focus_set()

    def context_event(self):
        if self.database.path != self.context_story:
            return None
        return next((row for row in self.database.events.list() if row["id"] == self.context_event_id), None)

    def refresh_event_context(self):
        event = self.context_event()
        if event is None:
            self.event_context.set("The originating event is no longer available in this story.")
            return
        chapter = next((row["title"] for row in self.database.chapters.list()
                        if row["id"] == event["chapter_id"]), "Unassigned")
        active = {row["id"]: row["name"] for row in self.database.characters()}
        participants = [f"{active[row['character_id']]} (#{row['character_id']})"
                        for row in self.database.events.participants()
                        if row["event_id"] == event["id"] and row["character_id"] in active]
        self.event_context.set(f"Originating event · {chapter} / {event['title']} "
                               f"(#{event['id']})\nSuggested participants: {', '.join(participants) if participants else 'None active'}")

    def use_context_event(self):
        event = self.context_event()
        label = next((label for label, ident in self.event_choices.items() if event and ident == event["id"]), None)
        if label is None:
            self.status.set("The originating event is no longer available. Choose another beginning event.")
            return False
        self.variables["start_event"].set(label)
        if not self.optional_open:
            self.toggle_optional()
        return True

    def inspect_saved(self):
        if self.database.path != self.context_story or self.context_event() is None:
            self.status.set("The originating event is no longer available in this story.")
            return None
        if not any(row["id"] == self.last_saved_id for row in self.database.relationship_records()):
            self.status.set("The saved relationship is no longer available.")
            return None
        history = HistoryDialog(self, self.database, self.changed, self.last_saved_id, as_of_id=self.context_event_id)
        history.bind("<Destroy>", lambda event: self.grab_set() if event.widget is history and self.winfo_exists() else None)
        return history

    def create_character(self, field):
        """Resume this exact entry after a separately committed character is made."""
        if getattr(self, "character_step", None):
            return
        self.scroller.pack_forget()
        self.footer.pack_forget()
        self.character_step = QuickCharacterDialog(
            self, self.database, lambda character_id: self.character_created(field, character_id),
            lambda: self.close_character_step(field))
        self.character_step.pack(fill="both", expand=True, padx=16, pady=12)

    def close_character_step(self, field):
        self.character_step = None
        self.scroller.pack(fill="both", expand=True, padx=16, pady=12)
        self.footer.pack(side="bottom", fill="x")
        if self.focus_job:
            self.after_cancel(self.focus_job)
        self.focus_job = self.after_idle(self.boxes[field].focus_set)

    def character_created(self, field, character_id):
        character = next((row for row in self.database.characters() if row["id"] == character_id), None)
        if character is None:
            return
        label = f"{character['name']} (#{character_id})"
        self.choices[label] = character_id
        for selector in ("source", "target"):
            self.boxes[selector].set_choices(self.choices)
        # The user explicitly chose the selector before creating this character.
        self.variables[field].set(label)
        self.status.set("Character created. Relationship not saved yet.")
        self.status_label.configure(style="Muted.TLabel")

    def values(self):
        return {**{field: variable.get() for field, variable in self.variables.items()},
                "category": self.category.get(), "notes": self.notes.get("1.0", "end-1c")}

    def field_changed(self, field):
        self.errors[field].set("")
        self.boxes[field].state(["!invalid"])
        self.update_preview()

    def toggle_optional(self):
        if self.optional_open:
            self.optional_frame.pack_forget()
        else:
            self.optional_frame.pack(fill='x', after=self.optional_toggle)
        self.optional_open = not self.optional_open
        self.optional_toggle.configure(text='Timing and notes ▾' if self.optional_open else 'Timing and notes ▸')

    def update_preview(self):
        if hasattr(self, 'optional_frame'):
            show_inverse = self.variables['semantics'].get() == 'Directional' or bool(self.variables['inverse_label'].get())
            if show_inverse:
                self.inverse_frame.pack(fill='x', before=self.optional_toggle)
            else:
                self.inverse_frame.pack_forget()
        source = self.variables["source"].get() or "Source"
        target = self.variables["target"].get() or "Target"
        kind = self.variables["kind"].get().strip() or "relationship type"
        self.preview.set(perspectives(source, target, kind, self.variables["semantics"].get().lower(),
                                     self.variables["inverse_label"].get().strip()))

    def move_from_notes(self, backwards):
        previous = self.boxes["inverse_label"] if self.relationship_id else self.boxes["start_event"]
        (previous if backwards else self.save_button).focus_set()
        return "break"

    def save_shortcut(self, _event=None):
        self.save()
        return "break"

    def validate(self, values):
        errors = {}
        current_ids = {row["id"] for row in self.database.characters()}
        for field in ("source", "target"):
            if self.choices.get(values[field]) not in current_ids:
                errors[field] = "Select a character from the matching suggestions."
        if not errors and values["source"] == values["target"]:
            errors["target"] = "Choose a different character from Source."
        if not values["kind"].strip():
            errors["kind"] = "Choose or enter a relationship type."
        if values["semantics"] not in ("Mutual", "Directional"):
            errors["semantics"] = "Choose Mutual or Directional deliberately."
        elif values["semantics"] == "Mutual" and values["inverse_label"].strip():
            errors["semantics"] = "Mutual uses the same label both ways. Clear the inverse label or choose Directional."
        if not errors:
            try:
                data = normalize(self.choices[values["source"]], self.choices[values["target"]], values["kind"],
                                 values["notes"], values["semantics"].lower(), values["inverse_label"])
                self.database.relationship_store.validate(data, self.relationship_id)
            except ValueError as error:
                errors["kind"] = str(error)
        for field, variable in self.errors.items():
            variable.set(errors.get(field, ""))
            self.boxes[field].state(["invalid" if field in errors else "!invalid"])
        if errors:
            self.boxes[next(iter(errors))].focus_set()
        return not errors

    def save(self):
        values = self.values()
        self.status.set("")
        self.status_label.configure(style="Muted.TLabel")
        if not self.validate(values):
            return False
        try:
            saved_id = self.database.save_relationship(
                self.choices[values["source"]], self.choices[values["target"]],
                values["kind"], values["notes"], self.relationship_id,
                semantics=values["semantics"].lower(), inverse_label=values["inverse_label"],
                start_event=self.event_choices.get(values["start_event"]), category=values["category"] if self.relationship_id is None or self.category_changed else self.original_category)
        except (ValueError, sqlite3.Error) as error:
            self.status.set(f"Could not save: {error}. Your entry has been kept.")
            self.status_label.configure(style="Error.TLabel")
            return False
        saved_connection = self.preview.get()
        self.last_saved_id = saved_id
        if self.inspect_saved_button is not None:
            self.inspect_saved_button.state(["!disabled"])
        self.boxes["kind"].set_choices(self.type_choices())
        self.boxes["inverse_label"].set_choices(sorted(set(("Mentee", "Employee", *self.type_choices())), key=str.casefold))
        if self.relationship_id is None:
            self.category.set("Other")
            for variable in self.variables.values():
                variable.set("")
            self.notes.delete("1.0", "end")
            self.notes.edit_reset()
        # An edit stays attached to its original record; subsequent saves update it.
        self.original = self.values()
        self.status.set(f"✓ Saved: {saved_connection.splitlines()[0]}"
                        + (f" · Relationship #{saved_id}; inspect it at the originating event."
                           if self.context_event_id is not None else ""))
        self.status_label.configure(style="Success.TLabel")
        self.changed("Relationship saved")
        self.boxes["source"].focus_set()
        return True

    def close(self):
        if self.values() != self.original:
            answer = messagebox.askyesnocancel(
                "Unfinished relationship", "Save this relationship before closing?\n\n"
                "Yes: save and close. No: discard changes. Cancel: continue editing.", parent=self)
            if answer is None or (answer and not self.save()):
                return
        self.destroy()
