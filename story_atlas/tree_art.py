"""Optional Treeview identity images, preserving existing values and stable IDs."""
from collections import OrderedDict
from PIL import ImageTk
from .ui_assets import cache_for


def portrait_photo(tree, database, filename):
    if not filename:
        return None
    root = tree._root()
    if not hasattr(root, '_portrait_row_cache'):
        root._portrait_row_cache = OrderedDict()
        root.bind('<Destroy>', lambda event: root._portrait_row_cache.clear() if event.widget is root else None, add='+')
    cache = root._portrait_row_cache
    key = (str(database.path), filename)
    if key not in cache:
        image = database.assets.thumbnail(filename, (24, 24))
        if image is None:
            return None  # A later import/recovery may restore the same reference.
        cache[key] = ImageTk.PhotoImage(image, master=root)
    cache.move_to_end(key)
    photo = cache[key]
    while len(cache) > 128:
        cache.popitem(last=False)
    return photo


def install_tree_art(tree, rows, database, key_for=None):
    """Rows/provider are callbacks so story switches never retain a database."""
    tree.configure(show='tree headings')
    tree.heading('#0', text='')
    tree.column('#0', width=36, minwidth=36, stretch=False)
    def refresh():
        settings = getattr(tree._root(), 'settings', None)
        values = settings.values if settings else {}
        illustrated = values.get('illustrations', 'Illustrated') == 'Illustrated'
        tree.atlas_row_images = {}
        records = rows()
        for iid in tree.get_children():
            row = records.get(iid, {})
            image = portrait_photo(tree, database(), row.get('portrait', '')) if row else None
            key = key_for(row) if key_for else 'section.identity'
            if image is None and illustrated and row and key:
                image = cache_for(tree).get(key, 24, values.get('theme', 'dark'))
            tree.atlas_row_images[iid] = image
            tree.item(iid, image=image or '')
    tree.atlas_refresh_art = refresh
    return refresh
