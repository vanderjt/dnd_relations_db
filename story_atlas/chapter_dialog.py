"""Small chapter editor and reusable chapter selector."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from .widgets import text_area, ActionBar
from .theme import style_tree


class ChapterPicker(ttk.Frame):
    def __init__(self, parent, database, selected=None, on_change=None):
        super().__init__(parent)
        self.database, self.on_change = database, on_change
        self.value = tk.StringVar(self)
        ttk.Label(self, text='Chapter').pack(anchor='w')
        self.box = ttk.Combobox(self, textvariable=self.value, state='readonly')
        self.box.pack(fill='x')
        self.refresh(selected)
        self.box.bind('<<ComboboxSelected>>', lambda _: on_change() if on_change else None)

    def refresh(self, selected=None):
        self.choices = {'Unassigned events': None}
        self.choices.update({f"{row['title']} (#{row['id']})": row['id'] for row in self.database.chapters.list()})
        self.box.configure(values=tuple(self.choices))
        self.value.set(next((key for key, ident in self.choices.items() if ident == selected), 'Unassigned events'))

    def get(self):
        return self.choices[self.value.get()]


class ChapterDialog(tk.Toplevel):
    def __init__(self, parent, database, changed, row=None):
        super().__init__(parent)
        self.database, self.changed, self.ident = database, changed, row['id'] if row else None
        self.title('Edit chapter' if row else 'New chapter')
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.geometry('550x360')
        body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        self.name = tk.StringVar(self, row['title'] if row else '')
        ttk.Label(body, text='Chapter title').pack(anchor='w')
        entry = ttk.Entry(body, textvariable=self.name)
        entry.pack(fill='x')
        ttk.Label(body, text='Summary').pack(anchor='w', pady=(8, 0))
        bar = ActionBar(body)
        bar.pack(side='bottom', fill='x')
        bar.add(ttk.Button(bar, text='Save chapter', style='Primary.TButton', command=self.save))
        bar.add(ttk.Button(bar, text='Cancel', command=self.close))
        self.summary = text_area(body, height=5)
        self.summary.pack(fill='both', expand=True)
        self.summary.insert('1.0', row['summary'] if row else '')
        self.original = self.values()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda _: self.close())
        self.bind('<Control-Return>', lambda _: self.save())
        style_tree(self)
        entry.focus_set()

    def values(self):
        return self.name.get(), self.summary.get('1.0', 'end-1c')

    def save(self):
        try:
            ident = self.database.chapters.save(*self.values(), self.ident)
        except (ValueError, sqlite3.Error) as error:
            messagebox.showerror('Cannot save chapter', str(error), parent=self)
            return False
        self.changed(ident)
        self.destroy()
        return True

    def close(self):
        if self.values() != self.original:
            answer = messagebox.askyesnocancel('Unfinished chapter', 'Save this chapter before closing?', parent=self)
            if answer is None or (answer and not self.save()):
                return
            if answer:
                return
        self.destroy()
