"""Shared section emblems and readable identity headers."""
from tkinter import ttk
from PIL import ImageTk
from .widgets import wrapping_label
from .ui_assets import decorate


class IllustratedLabel(ttk.Label):
    def __init__(self, parent, key, size=32, **kwargs):
        kwargs.setdefault('style', 'Heading.TLabel')
        super().__init__(parent, **kwargs)
        self.bind('<Configure>', lambda event: self.configure(wraplength=max(100, event.width - size - 8)))
        decorate(self, key, size)


class IdentityHeader(ttk.Frame):
    """Portrait content is independent of the optional illustration preference."""
    def __init__(self, parent):
        super().__init__(parent, padding=(0, 8))
        self.columnconfigure(1, weight=1)
        self.name = wrapping_label(self, style='Heading.TLabel', font='AtlasHeading')
        self.name.grid(row=0, column=1, sticky='ew', pady=(0, 4))
        self.details = wrapping_label(self, style='Muted.TLabel')
        self.details.grid(row=1, column=1, sticky='ew', pady=4)
        self.portrait = wrapping_label(self)
        self.portrait.grid(row=0, column=0, rowspan=2, sticky='nw', padx=(0, 12))
        self.photo = None

    def show_portrait(self, assets, filename):
        image = assets.thumbnail(filename, (96, 96))
        self.photo = ImageTk.PhotoImage(image, master=self) if image else None
        self.portrait.configure(image=self.photo or '', text='' if image else (
            'Portrait unavailable — the rest of this profile is still accessible.' if filename else 'No portrait'))
        if image:
            self.portrait.grid(row=0, column=0, rowspan=2, sticky='nw', padx=(0, 12), columnspan=1)
        else:
            # Missing-portrait feedback remains readable across the full width.
            self.portrait.grid(row=2, column=0, columnspan=2, rowspan=1, sticky='ew', padx=0)
            self.portrait.configure(wraplength=max(140, self.winfo_width()))
            if not filename:
                self.portrait.grid_remove()
        return self.photo
