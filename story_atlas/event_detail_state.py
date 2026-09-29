"""Retain outline state by internal IDs without exposing IDs in display labels."""


def capture(tree):
    def descendants(parent=''):
        for key in tree.get_children(parent):
            yield key
            yield from descendants(key)
    return dict(open={key: bool(tree.item(key, 'open')) for key in descendants()},
                selection=tree.selection(), focus=tree.focus(), x=tree.xview()[0], y=tree.yview()[0])


def restore(tree, state):
    for key, opened in state['open'].items():
        if tree.exists(key):
            tree.item(key, open=opened)
    tree.selection_set([key for key in state['selection'] if tree.exists(key)])
    if tree.exists(state['focus']):
        tree.focus(state['focus'])
    tree.xview_moveto(state['x'])
    tree.yview_moveto(state['y'])
