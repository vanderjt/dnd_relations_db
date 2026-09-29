"""Bounded, scrollable chronology review; persistence remains in Chapters."""
import tkinter as tk
from tkinter import ttk
from .widgets import ActionBar, wrapping_label, read_only_text_area, set_read_only_text
from .theme import style_tree


class ChronologyPreview(tk.Toplevel):
    def __init__(self, parent, preview):
        super().__init__(parent)
        self.result = False
        self.previous_focus = parent.focus_get()
        self.title('Review chapter chronology')
        self.geometry('880x560')
        self.minsize(480, 320)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        footer = ActionBar(self)
        footer.pack(side='bottom', fill='x', padx=12, pady=8)
        self.confirm_button = footer.add(ttk.Button(footer, text='Confirm move', style='Primary.TButton', command=self.confirm))
        self.cancel_button = footer.add(ttk.Button(footer, text='Cancel', command=self.destroy))
        wrapping_label(self, text='Review before and after. Relationship history follows event order; current relationships may change.',
                       style='Context.TLabel').pack(fill='x', padx=12, pady=8)
        panes = ttk.Frame(self)
        panes.pack(fill='both', expand=True, padx=12)
        panes.columnconfigure((0, 1), weight=1, uniform='preview')
        panes.rowconfigure(1, weight=1)
        self.texts = []
        for column, (prefix, title) in enumerate((('old', 'Before'), ('new', 'After'))):
            ttk.Label(panes, text=title, style='Heading.TLabel').grid(row=0, column=column, sticky='w')
            text = read_only_text_area(panes, height=12)
            text.grid(row=1, column=column, sticky='nsew', padx=(0, 6) if column == 0 else (6, 0))
            lines = []
            chapters = preview[f'{prefix}_chapters']
            events = preview[f'{prefix}_events']
            for ident, name in [*chapters, (None, 'Unassigned')]:
                lines.append(f'{name}' + (f' (#{ident})' if ident is not None else ''))
                children = [(i, event) for i, event in enumerate(events, 1) if event[2] == ident]
                lines.extend(f'  {i}. {event[1]} (#{event[0]})' for i, event in children)
                if not children:
                    lines.append('  No events')
                lines.append('')
            set_read_only_text(text, '\n'.join(lines))
            self.texts.append(text)
        self.bind('<Escape>', lambda _: self.destroy())
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        style_tree(self)
        self.cancel_button.focus_set()

    def confirm(self):
        self.result = True
        self.destroy()


def confirm_preview(parent, preview):
    dialog = ChronologyPreview(parent, preview)
    parent.wait_window(dialog)
    if dialog.previous_focus and dialog.previous_focus.winfo_exists():
        dialog.previous_focus.focus_set()
    return dialog.result
