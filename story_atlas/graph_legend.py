"""Shared legend wording, swatches, and accessible explanations."""
from matplotlib.lines import Line2D
from .character_type import TYPE_COLORS

EDGE_STYLES = {
    'Support': ('#159f86', 'solid'), 'Conflict': ('#d77632', 'dashed'),
    'Personal': ('#a47bdd', 'dotted'), 'Other': ('#7897aa', 'dashdot'),
}
LINK_EXPLANATIONS = {
    'Support': 'help, cooperation or protection',
    'Conflict': 'opposition, harm or hostility',
    'Personal': 'family, friendship or affection',
    'Other': 'unassigned or another kind of connection',
}


def handles():
    dots = [Line2D([], [], marker='o', linestyle='None', color=color, label=name)
            for name, color in TYPE_COLORS.items()]
    links = [Line2D([], [], color=color, linestyle=style, label=name)
             for name, (color, style) in EDGE_STYLES.items()]
    return dots + links


def add_menu_explanations(menu):
    menu.add_separator()
    menu.add_command(label='LINKS · visual category at selected event', state='disabled')
    for name, (color, style) in EDGE_STYLES.items():
        menu.add_command(label=f'{name} ({style}) — {LINK_EXPLANATIONS[name]}',
                         foreground=color, command=lambda: None)
    menu.add_separator()
    for line in ('One arrow → source to target; two arrows ↔ mutual',
                 'Hollow / dashed dot = planned or unsaved character',
                 'Ended-at-event links are dashed when highlighted',
                 'Dot types describe Current, not a moral judgment',
                 'Link categories are assigned explicitly; unassigned = Other'):
        menu.add_command(label=line, state='disabled')


def category_for(row, widget):
    """Keep a legacy view's visible color when first editing its connection."""
    root = widget._root()
    workspace = getattr(root, 'simple', None)
    graph = getattr(workspace, 'graph', None) if getattr(root, 'mode', None) and root.mode.get() == 'Simple' else getattr(root, 'graph', None)
    return row.get('category') or getattr(graph, 'visual_categories', {}).get(row.get('kind'), 'Other')
