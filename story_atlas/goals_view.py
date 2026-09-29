"""Read-only views of committed character goals."""
import tkinter as tk
from tkinter import ttk

from .widgets import ActionBar, read_only_text_area, set_read_only_text, wrapping_label
from .theme import style_tree


def saved_goal_text(character):
    return character['goals'] if character['goals'] else 'No saved goals.'


class CastGoalsDialog(tk.Toplevel):
    def __init__(self, parent, database):
        super().__init__(parent)
        self.title('Cast goals · committed data')
        self.geometry('700x520')
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        wrapping_label(body, text='Saved goals across the active cast. These are committed profile fields.').pack(fill='x')
        self.app = parent.winfo_toplevel()
        self.query = tk.StringVar(self)
        ttk.Label(body, text='Search names, IDs, and current goals').pack(anchor='w')
        ttk.Entry(body, textvariable=self.query).pack(fill='x')
        self.choice = tk.StringVar(self)
        self.selector = ttk.Combobox(body, textvariable=self.choice, state='readonly')
        self.selector.pack(fill='x', pady=4)
        self.selector.bind('<Return>', lambda _: self.open_character())
        self.content = read_only_text_area(body, height=18)
        self.content.pack(fill='both', expand=True, pady=8)
        self.rows = database.characters()
        self.query.trace_add('write', self.filter)
        self.filter()
        bar = ActionBar(body)
        bar.pack(fill='x')
        bar.add(ttk.Button(bar, text='Open current profile', style='Primary.TButton', command=self.open_character))
        bar.add(ttk.Button(bar, text='Close', command=self.close))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda _: self.close())
        style_tree(self)

    def filter(self, *_):
        query = self.query.get().casefold()
        rows = [row for row in self.rows if query in f"{row['name']} #{row['id']} {row['goals']}".casefold()]
        self.choices = {f"{row['name']} (#{row['id']})": row['id'] for row in rows}
        self.selector.configure(values=tuple(self.choices))
        if self.choice.get() not in self.choices:
            self.choice.set(next(iter(self.choices), ''))
        set_read_only_text(self.content, '\n\n'.join(f"{row['name']} (#{row['id']})\n{saved_goal_text(row)}" for row in rows) or 'No matching active characters.')

    def open_character(self):
        ident = self.choices.get(self.choice.get())
        if ident is not None and self.app.characters.open_character(ident):
            self.app.tabs.select(self.app.characters)
            self.destroy()

    def close(self):
        self.destroy()


class ParticipantGoalsDialog(tk.Toplevel):
    def __init__(self, parent, character):
        super().__init__(parent)
        self.title(f"Saved profile · {character['name']} (#{character['id']})")
        self.geometry('600x440')
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill='both', expand=True)
        wrapping_label(body, text=f"Committed profile · {character['name']} (#{character['id']})",
                       style='Heading.TLabel').pack(fill='x')
        self.content = read_only_text_area(body, height=14)
        self.content.pack(fill='both', expand=True, pady=8)
        set_read_only_text(self.content, f"Summary\n{character['summary'] or 'No saved summary.'}\n\n"
                           f"Goals\n{saved_goal_text(character)}")
        bar = ActionBar(body)
        bar.pack(fill='x')
        bar.add(ttk.Button(bar, text='Back to event editor', style='Navigation.TButton', command=self.close))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda _: self.close())
        style_tree(self)

    def close(self):
        parent = self.master
        self.destroy()
        if parent.winfo_exists():
            parent.grab_set()
            parent.cast.focus_set()
