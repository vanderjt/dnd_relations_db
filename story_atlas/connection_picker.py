"""Direct, searchable character choices for the connection steps."""
import tkinter as tk
from tkinter import ttk
from .scroll_frame import ScrollFrame
from .widgets import wrapping_label


def character_context(row):
    details = [str(row.get(key, '')).strip() for key in ('role', 'species', 'faction', 'location')]
    return ' · '.join([value for value in details if value] + [f"#{row['id']}"])


class CharacterCard(ttk.Frame):
    """One focus stop, with explicit activation rather than focus selection."""
    def __init__(self, parent, command=None):
        super().__init__(parent, padding=10, relief='solid', borderwidth=2,
                         takefocus=bool(command))
        self.command = command
        self.name = wrapping_label(self, style='Heading.TLabel')
        self.name.pack(fill='x')
        self.context = wrapping_label(self, style='Muted.TLabel')
        self.context.pack(fill='x', pady=(3, 0))
        if command:
            for widget in (self, self.name, self.context):
                widget.configure(cursor='hand2')
                widget.bind('<ButtonRelease-1>', lambda _: self.invoke())
            self.bind('<Return>', self.activate)
            self.bind('<space>', self.activate)
            self.bind('<FocusIn>', lambda _: self.configure(relief='ridge'))
            self.bind('<FocusOut>', lambda _: self.configure(relief='solid'))

    def display(self, row):
        self.name.configure(text=row['name'])
        self.context.configure(text=character_context(row))

    def invoke(self):
        if self.command:
            self.command()

    def activate(self, _event):
        self.invoke()
        return 'break'


class CharacterPicker(ttk.Frame):
    def __init__(self, parent, task, source=False):
        super().__init__(parent)
        self.task, self.source = task, source
        self.query = tk.StringVar(self)
        ttk.Label(self, text='Find a character').pack(anchor='w')
        self.search = ttk.Entry(self, textvariable=self.query)
        self.search.pack(fill='x', pady=(2, 6))
        self.list = ScrollFrame(self)
        self.list.canvas.configure(height=160)
        self.list.pack(fill='both', expand=True)
        self.buttons = {}
        self.query.trace_add('write', lambda *_: self.refresh())

    def focus_set(self):
        self.search.focus_set()

    def refresh(self):
        chosen_source = self.task.names.get(self.task.variables['source'].get())
        query = self.query.get().strip().casefold()
        active = set(self.task.names.values())
        rows = {row['id']: row for row in self.task.database.characters()}
        for ident in list(self.buttons):
            if ident not in active:
                self.buttons.pop(ident).destroy()
        for child in self.list.content.winfo_children():
            child.pack_forget()
        visible = 0
        for label, ident in self.task.names.items():
            button = self.buttons.get(ident)
            if button is None:
                if self.source:
                    button = CharacterCard(self.list.content, command=lambda ident=ident: self.choose_source(ident))
                else:
                    selected = tk.BooleanVar(self)
                    button = ttk.Checkbutton(self.list.content, variable=selected,
                                             command=lambda ident=ident: self.task.toggle_target(ident))
                    button.selected = selected
                self.buttons[ident] = button
            if self.source:
                button.display(rows[ident])
            else:
                button.configure(text=label)
                button.selected.set(ident in self.task.targets)
            searchable = label + ' ' + character_context(rows[ident]) if self.source else label
            if (not self.source and ident == chosen_source) or query not in searchable.casefold():
                continue
            button.pack(fill='x', anchor='w', pady=2)
            visible += 1
        if not hasattr(self, 'empty'):
            self.empty = wrapping_label(self.list.content)
        if not visible:
            self.empty.configure(text='No matching characters.' if self.task.names else 'No characters yet. Create one below.')
            self.empty.pack(fill='x')
        if not self.source and self.task.targets and hasattr(self.task, 'selected_bar'):
            self.task.selected_bar.pack(fill='x', pady=6)

    def choose_source(self, ident):
        self.task.variables['source'].set(self.task.label(ident))
        self.task.source_chosen()
