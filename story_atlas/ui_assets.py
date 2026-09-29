"""Optional product artwork, isolated from user portraits and story data.

Tk images belong to one interpreter. Each root owns a bounded LRU; decorated
widgets also retain their displayed image so eviction cannot blank a control.
"""
from collections import OrderedDict
import json
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk
from .paths import resource


class UIAssetCache:
    def __init__(self, root, folder=None, capacity=64):
        self.root = root
        self.folder = Path(folder) if folder is not None else resource('ui')
        self.capacity = max(1, capacity)
        self.images = OrderedDict()
        try:
            manifest = json.loads((self.folder / 'manifest.json').read_text(encoding='utf-8'))
            self.assets = manifest.get('assets', {})
            self.aliases = manifest.get('aliases', {})
            if not isinstance(self.assets, dict) or not isinstance(self.aliases, dict):
                raise ValueError('Invalid asset catalog')
        except (OSError, ValueError, AttributeError):
            self.assets, self.aliases = {}, {}

    def get(self, key, size=32, theme='dark', state='normal'):
        size = max(8, min(256, int(size)))
        cache_key = (key, size, theme, state)
        if cache_key in self.images:
            self.images.move_to_end(cache_key)
            return self.images[cache_key]
        photo = None
        try:
            entry = self.assets[self.aliases.get(key, key)]
            path = (self.folder / entry['path']).resolve()
            if not path.is_relative_to(self.folder.resolve()):
                raise ValueError('Asset path outside catalog')
            with Image.open(path) as original:
                if original.width > 2048 or original.height > 2048:
                    raise ValueError('Decorative asset exceeds supported dimensions')
                image = original.convert('RGBA')
                ratio = min(size / image.width, size / image.height)
                image = image.resize((max(1, round(image.width * ratio)), max(1, round(image.height * ratio))), Image.Resampling.NEAREST)
                canvas = Image.new('RGBA', (size, size))
                canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
                photo = ImageTk.PhotoImage(canvas, master=self.root)
        except (OSError, ValueError, KeyError, TypeError, tk.TclError,
                Image.DecompressionBombError, Image.DecompressionBombWarning):
            pass  # Text remains usable even if optional resources are damaged.
        self.images[cache_key] = photo
        while len(self.images) > self.capacity:
            self.images.popitem(last=False)
        return photo


def cache_for(widget):
    root = widget._root()
    if not hasattr(root, '_ui_asset_cache'):
        root._ui_asset_cache = UIAssetCache(root)
        def clear(event):
            if event.widget is root:
                root._ui_asset_cache.images.clear()
        root.bind('<Destroy>', clear, add='+')
    return root._ui_asset_cache


def decorate(widget, key, size=32):
    """Add optional art to an existing labeled control without changing behavior."""
    widget.atlas_art = (key, size)
    refresh_widget(widget)
    return widget


def refresh_widget(widget):
    key, size = widget.atlas_art
    settings = getattr(widget._root(), 'settings', None)
    values = settings.values if settings else {}
    image = None
    if values.get('illustrations', 'Illustrated') == 'Illustrated':
        image = cache_for(widget).get(key, size, values.get('theme', 'dark'))
    widget.atlas_art_image = image
    widget.configure(image=image or '', compound='left')


def refresh_illustrations(root):
    """Refresh existing controls only: never rebuild forms or mutate their values."""
    if hasattr(root, 'atlas_art'):
        refresh_widget(root)
    for child in root.winfo_children():
        refresh_illustrations(child)


def artwork_credits():
    return ('HAS IconPack and HAS Buildings Pack artwork by Aleksandr Makarov '
            '(@IKnowKingRabbit). Selected artwork is incorporated into Story Atlas. '
            'Original license texts are included in resources/ui/licenses.')
