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
        self.name = wrapping_label(self, style='Heading.TLabel', font='AtlasHeading')
        self.name.pack(fill='x', pady=(0, 4))
        self.details = wrapping_label(self, style='Context.TLabel')
        self.details.pack(fill='x', pady=4)
        self.portrait = ttk.Label(self)
        self.portrait.pack(anchor='w', pady=6)
        self.photo = None

    def show_portrait(self, assets, filename):
        image = assets.thumbnail(filename, (96, 96))
        self.photo = ImageTk.PhotoImage(image, master=self) if image else None
        self.portrait.configure(image=self.photo or '', text='' if image else (
            'Portrait unavailable — the rest of this profile is still accessible.' if filename else 'No portrait'))
        return self.photo
