"""New stories are exclusively published into an unused title-derived path."""
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .backup import publish_database
from .database import Database
from .simple_event import create_chapter_event
from .widgets import wrapping_label, ActionBar
from .scroll_frame import ScrollFrame
from .ui_assets import decorate
from .theme import style_tree


def create_story(destination, title, chapter='Chapter 1', event='Opening scene'):
    if not all(value.strip() for value in (title, chapter, event)):
        raise ValueError('Enter a story title, first chapter, and initial event.')
    def populate(path):
        database = Database(path)
        try:
            create_chapter_event(database, chapter, event)
            with database.connection:
                database.connection.execute('INSERT INTO story_metadata VALUES (?,?)', ('title', title.strip()))
        finally:
            database.close()
    return publish_database(destination, populate)


def story_filename(title):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip().rstrip('. ')
    name = name[:120].rstrip('. ') or 'Untitled story'
    if name.split('.')[0].rstrip().upper() in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$', *(f'{prefix}{digit}' for prefix in ('COM', 'LPT') for digit in '¹²³'), *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        name = '_' + name
    return name + '.db'


def available_path(directory, filename):
    path = Path(directory) / filename
    index = 2
    while path.exists():
        path = Path(directory) / f'{Path(filename).stem} ({index}).db'
        index += 1
    return path


class StorySetup(tk.Toplevel):
    def __init__(self, parent, directory, completed):
        super().__init__(parent)
        self.title('Start a story')
        self.transient(parent)
        self.grab_set()
        self.geometry('480x400')
        self.minsize(360, 280)
        self.custom_path = None
        bar = ActionBar(self)
        bar.pack(side='bottom', fill='x', padx=16, pady=10)
        self.scroller = ScrollFrame(self)
        self.scroller.pack(fill='both', expand=True, padx=16, pady=12)
        body = self.scroller.content
        decorate(ttk.Label(body, text='Start a story', style='Heading.TLabel'), 'section.story').pack(anchor='w', pady=(0, 8))
        self.fields = [tk.StringVar(self, value) for value in ('', 'Chapter 1', 'Opening scene')]
        ttk.Label(body, text='Story title').pack(anchor='w')
        entry = ttk.Entry(body, textvariable=self.fields[0])
        entry.pack(fill='x', pady=8)
        self.destination = tk.StringVar(self)
        def update(*_):
            self.path = available_path(self.custom_path.parent, self.custom_path.name) if self.custom_path else available_path(directory, story_filename(self.fields[0].get()))
            self.destination.set(f'Save to {self.path}')
        self.fields[0].trace_add('write', update)
        update()
        wrapping_label(body, textvariable=self.destination, style='Muted.TLabel').pack(fill='x')
        def change():
            chosen = filedialog.asksaveasfilename(parent=self, initialdir=self.path.parent, initialfile=story_filename(self.fields[0].get()), defaultextension='.db', filetypes=[('Story Atlas', '*.db')])
            if chosen:
                self.custom_path = Path(chosen)
                update()
        ttk.Button(body, text='Change location…', command=change).pack(anchor='w')
        opening = ttk.Frame(body)
        def toggle():
            if opening.winfo_manager():
                opening.pack_forget()
            else:
                opening.pack(fill='x', after=customize)
        customize = ttk.Button(body, text='Customize opening ▸', command=toggle)
        self.customize_button = customize
        customize.pack(anchor='w', pady=8)
        for label, variable in zip(('First chapter', 'Initial event'), self.fields[1:]):
            ttk.Label(opening, text=label).pack(anchor='w')
            ttk.Entry(opening, textvariable=variable).pack(fill='x')
        def save():
            update()
            try:
                result = create_story(self.path, *(field.get() for field in self.fields))
            except Exception as error:
                messagebox.showerror('Cannot create story', str(error), parent=self)
                update()
                return
            self.destroy()
            completed(result)
        self.save = save
        self.change_location = change
        self.create_button = bar.add(ttk.Button(bar, text='Create story', command=save, style='Primary.TButton'))
        self.cancel_button = bar.add(ttk.Button(bar, text='Cancel', command=self.destroy, style='Secondary.TButton'))
        self.bind('<Escape>', lambda _: self.destroy())
        style_tree(self)
        entry.focus_set()
