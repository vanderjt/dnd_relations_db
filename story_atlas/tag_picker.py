"""Additive tags backed by the existing comma-separated field."""
import tkinter as tk
from tkinter import ttk
from .retrieval import tags
from .suggestions import choices


class TagPicker(ttk.Frame):
    def __init__(self, parent, variable, database_provider):
        super().__init__(parent)
        self.variable = variable
        self.pending = tk.StringVar(self)
        self.box = ttk.Combobox(self, textvariable=self.pending)
        self.box.configure(postcommand=lambda: self.box.configure(values=choices(database_provider(), 'tags')))
        self.box.pack(fill='x')
        self.box.bind('<<ComboboxSelected>>', lambda _: self.add())
        self.box.bind('<Return>', lambda _: self.add())
        ttk.Button(self, text='Add tag', command=self.add).pack(anchor='w')
        self.chips = ttk.Frame(self)
        self.chips.pack(fill='x')
        self.trace = variable.trace_add('write', self.refresh)
        self.refresh()

    def value(self):
        existing = tags(self.variable.get())
        added = [value for value in tags(self.pending.get()) if value not in existing]
        return self.variable.get() + (', ' if self.variable.get().strip() and added else '') + ', '.join(added)

    def add(self):
        existing = tags(self.variable.get())
        added = [value for value in tags(self.pending.get()) if value not in existing]
        if added:
            self.variable.set(self.variable.get() + (', ' if self.variable.get().strip() else '') + ', '.join(added))
        self.pending.set('')
        return 'break'

    def remove(self, value):
        self.variable.set(', '.join(tag for tag in tags(self.variable.get()) if tag != value))

    def refresh(self, *_):
        for child in self.chips.winfo_children():
            child.destroy()
        for value in tags(self.variable.get()):
            ttk.Button(self.chips, text=f'{value} ×', command=lambda value=value: self.remove(value)).pack(anchor='w')

    def destroy(self):
        self.variable.trace_remove('write', self.trace)
        super().destroy()
