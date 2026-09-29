"""Appearance preferences dialog; changes are applied and saved explicitly."""
import tkinter as tk
from tkinter import ttk
from .scroll_frame import ScrollFrame
from .theme import style_tree
from .widgets import wrapping_label


class AppearanceDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.title("Appearance")
        self.geometry("460x350")
        self.minsize(360, 280)
        self.transient(app)
        self.grab_set()
        buttons = ttk.Frame(self, padding=12)
        buttons.pack(side="bottom", fill="x")
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True, padx=16, pady=12)
        frame = scroll.content
        ttk.Label(frame, text="Appearance", style="Heading.TLabel").pack(anchor="w", pady=8)
        theme = tk.StringVar(value=app.settings.values["theme"])
        size = tk.StringVar(value=str(app.settings.values["text_size"]))
        self.illustrations = illustrations = tk.StringVar(self, app.settings.values['illustrations'])
        self.theme, self.size = theme, size
        ttk.Label(frame, text="Theme").pack(anchor="w")
        ttk.Combobox(frame, values=("dark", "light"), textvariable=theme, state="readonly").pack(fill="x", pady=6)
        ttk.Label(frame, text="Text size (points)").pack(anchor="w")
        ttk.Combobox(frame, values=tuple(range(9, 17)), textvariable=size, state="readonly").pack(fill="x", pady=6)
        ttk.Label(frame, text='Artwork').pack(anchor='w')
        ttk.Combobox(frame, values=('Illustrated', 'Minimal'), textvariable=illustrations, state='readonly').pack(fill='x', pady=6)
        wrapping_label(frame, text='Minimal reduces decorative artwork. Your imported portraits remain visible.', style='Muted.TLabel').pack(fill='x', pady=6)
        self.apply_button = ttk.Button(buttons, text="Apply", style="Primary.TButton",
                   command=lambda: app.set_appearance(theme.get(), int(size.get()), illustrations.get()))
        self.apply_button.pack(side="left")
        ttk.Button(buttons, text="Close", style="Secondary.TButton", command=self.destroy).pack(side="right")
        self.bind("<Escape>", lambda _: self.destroy())
        style_tree(self)
