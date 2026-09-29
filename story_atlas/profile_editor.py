"""Grouped profile fields, optional writing templates, and portrait selection."""
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk

from .models import PROFILE_FIELDS
from .profile_templates import TEMPLATES
from .scroll_frame import ScrollFrame
from .widgets import text_area, wrapping_label, ActionBar
from .illustrated_widgets import IllustratedLabel
from .ui_assets import decorate


class ProfileEditor(ttk.Frame):
    def __init__(self, parent, database_provider, simple=False):
        super().__init__(parent)
        self.database_provider = database_provider
        self.fields = {key: tk.StringVar(self, value) for key, value in (('classification', 'Neutral'), ('narrative_role', 'neutral'))}
        self.field_widgets = {}
        self.section_fields = {"identity": "name", "story": "summary", "goals": "goals", "abilities": "traits", "inventory": "inventory", "notes": "notes"}
        self.collapsible_sections = {}
        self.scroller = ScrollFrame(self)
        self.scroller.pack(fill="both", expand=True)
        body = self.scroller.content
        if not simple:
            wrapping_label(body, text="Only a name is required. Add other details whenever you need them.",
                           style="Muted.TLabel").pack(fill="x", pady=8)
        core = body
        if simple:
            for field in ('name', 'character_type'):
                ttk.Label(core, text=PROFILE_FIELDS[field]).pack(anchor='w', pady=(6, 2))
                self.fields[field] = tk.StringVar(self)
                from .character_type import CHARACTER_TYPES
                box = ttk.Entry(core, textvariable=self.fields[field]) if field == 'name' else ttk.Combobox(core, textvariable=self.fields[field], values=CHARACTER_TYPES, state='readonly')
                box.pack(fill='x')
                self.field_widgets[field] = box
            header = ttk.Button(core, text='Optional details ▸', command=lambda: self.toggle_section('details'))
            header.pack(anchor='w', pady=8)
            body = ttk.Frame(core)
            self.collapsible_sections['details'] = (header, body, False)
        templates = ActionBar(body)
        templates.pack(fill="x")
        templates.add(ttk.Button(templates, text="Add writing prompts for this type", style="Secondary.TButton", command=self.apply_template))
        self.template_status = tk.StringVar(self)
        wrapping_label(body, textvariable=self.template_status, style="Muted.TLabel").pack(fill="x")
        IllustratedLabel(body, 'section.identity', text="Identity").pack(fill='x', pady=(12, 6))
        for field in ("name", "character_type", "role", "species", "status", "faction", "location", "tags"):
            if field in self.fields:
                continue
            ttk.Label(body, text=PROFILE_FIELDS[field]).pack(anchor="w", pady=(6, 2))
            self.fields[field] = tk.StringVar(self)
            if field == 'character_type':
                from .character_type import CHARACTER_TYPES
                box = ttk.Combobox(body, textvariable=self.fields[field], values=CHARACTER_TYPES, state='readonly')
                box.pack(fill='x')
            elif field == "tags":
                from .tag_picker import TagPicker
                box = TagPicker(body, self.fields[field], self.database_provider)
                box.pack(fill="x")
            elif field in ("role", "species", "status", "faction", "location"):
                from .suggestions import choices
                box = ttk.Combobox(body, textvariable=self.fields[field])
                box.configure(postcommand=lambda box=box, field=field: box.configure(
                    values=choices(self.database_provider(), field)))
                box.pack(fill="x")
            else:
                box = ttk.Entry(body, textvariable=self.fields[field])
                box.pack(fill="x")
            self.field_widgets[field] = box
        self.template = self.fields['character_type']
        self.fields['character_type'].trace_add('write', self.type_changed)
        self.type_choices()
        self.fields["portrait"] = tk.StringVar(self)
        self.portrait_preview = ttk.Label(body, text="No portrait")
        self.portrait_preview.pack(anchor="w", pady=8)
        self.field_widgets["portrait"] = self.portrait_preview
        portraits = ActionBar(body)
        portraits.pack(fill="x")
        portraits.add(ttk.Button(portraits, text="Import portrait", style="Secondary.TButton", command=self.import_portrait))
        portraits.add(ttk.Button(portraits, text="Remove portrait", style="Danger.TButton", command=lambda: self.fields["portrait"].set("")))
        self.fields["portrait"].trace_add("write", self.refresh_portrait)
        body = core
        for section, fields in (("Story", ("summary", "backstory")), ("Goals", ("goals",)), ("Abilities", ("traits", "skills")),
                                ("Inventory", ("inventory",)), ("Notes", ("notes",))):
            section_key = section.casefold()
            header = ttk.Button(body, text=f"{section} ▾", command=lambda key=section_key: self.toggle_section(key))
            decorate(header, f'section.{section_key}', 24)
            header.pack(anchor="w", pady=(18, 6))
            section_body = ttk.Frame(body)
            section_body.pack(fill="x")
            self.collapsible_sections[section_key] = (header, section_body, True)
            for field in fields:
                ttk.Label(section_body, text=PROFILE_FIELDS[field]).pack(anchor="w", pady=4)
                widget = text_area(section_body, height=3 if field == "summary" else 6)
                widget.pack(fill="x", pady=(0, 8))
                self.fields[field] = widget
                self.field_widgets[field] = widget
            if simple:
                self.toggle_section(section_key)

    def toggle_section(self, section):
        header, body, open_ = self.collapsible_sections[section]
        if open_:
            body.pack_forget()
            header.configure(text=f"{section.title()} ▸" + self.section_indicator(body))
        else:
            body.pack(fill="x", after=header)
            header.configure(text=f"{section.title()} ▾")
        self.collapsible_sections[section] = (header, body, not open_)

    def section_indicator(self, body):
        count = 0
        for field, widget in self.field_widgets.items():
            if str(widget).startswith(str(body) + '.'):
                value = self.fields[field]
                content = value.get('1.0', 'end-1c') if isinstance(value, tk.Text) else value.get()
                count += bool(content.strip()) and not (field == 'narrative_role' and content == 'neutral')
        return f' · {count} filled' if count else ''

    def refresh_indicators(self):
        for key, (header, body, opened) in self.collapsible_sections.items():
            if not opened:
                header.configure(text=f'{"Optional details" if key == "details" else key.title()} ▸' + self.section_indicator(body))

    def focus_section(self, section):
        field = self.section_fields.get(section, "name")
        if section in self.collapsible_sections and not self.collapsible_sections[section][2]:
            self.toggle_section(section)
        widget = self.field_widgets[field]
        widget.focus_set()
        self.after_idle(lambda: self.scroller.reveal_focus(type("Event", (), {"widget": widget})()))

    def type_choices(self):
        from .character_type import CHARACTER_TYPES
        self.field_widgets['character_type'].configure(values=CHARACTER_TYPES)

    def type_changed(self, *_):
        from .character_type import legacy_values, validate
        value = self.fields['character_type'].get()
        if value:
            value = validate(value)
            self.fields['character_type'].set(value)
            classification, role = legacy_values(value)
            self.fields['classification'].set(classification)
            self.fields['narrative_role'].set(role)
            self.type_choices()

    def apply_template(self):
        filled = 0
        template = {'Player': 'Protagonist', 'Enemy NPC': 'Antagonist'}.get(self.fields['character_type'].get(), 'Minor NPC')
        for field, prompt in TEMPLATES.get(template, TEMPLATES['Minor NPC']).items():
            widget = self.fields[field]
            if not widget.get("1.0", "end-1c").strip():
                widget.insert("1.0", prompt)
                filled += 1
        self.template_status.set(f"Added prompts to {filled} empty fields. Review them before saving.")

    def import_portrait(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a portrait to copy",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")])
        if not path:
            return
        try:
            filename = self.database_provider().assets.import_image(path)
            self.fields["portrait"].set(filename)
        except (OSError, ValueError, sqlite3.Error) as error:
            messagebox.showerror("Cannot import portrait", str(error), parent=self)

    def refresh_portrait(self, *_):
        filename = self.fields["portrait"].get()
        image = self.database_provider().assets.thumbnail(filename, (100, 100))
        self.photo = ImageTk.PhotoImage(image, master=self) if image else None
        self.portrait_preview.configure(image=self.photo or "", text="" if image else (
            "Portrait unavailable. Import another image or remove it." if filename else "No portrait (optional)"))
