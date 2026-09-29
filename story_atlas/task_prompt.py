"""Task-specific choices with literal Save / Discard / Stay labels."""
import tkinter as tk
from tkinter import ttk
from .widgets import wrapping_label, ActionBar


def save_discard_stay(parent):
    dialog = tk.Toplevel(parent)
    dialog.title('Unfinished input')
    dialog.transient(parent.winfo_toplevel())
    dialog.result = None
    wrapping_label(dialog, text='Save changes before leaving this task?').pack(fill='x', padx=20, pady=16)
    def finish(value):
        dialog.result = value
        dialog.destroy()
    bar = ActionBar(dialog)
    bar.pack(fill='x', padx=16, pady=12)
    for label, value in (('Save', True), ('Discard', False), ('Stay', None)):
        button = bar.add(ttk.Button(bar, text=label, command=lambda value=value: finish(value)))
    dialog.protocol('WM_DELETE_WINDOW', lambda: finish(None))
    dialog.bind('<Escape>', lambda _: finish(None))
    dialog.grab_set()
    button.focus_set()
    parent.wait_window(dialog)
    return dialog.result
