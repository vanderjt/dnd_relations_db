"""Explicit presentation presets stored with the bundled example stories."""
from .graph import build_graph
from .graph_state import SavedViews, layout_positions, filter_graph
from .introductions import visible_cast

OVERVIEW = 'Example overview'


def save_example_views(db, categories, scenes=()):
    graph = build_graph(db.characters(), db.relationships())
    positions = layout_positions(graph, {}, set(), 'Circle')
    state = dict(version=1, show_planned=False, as_of_event=None, focus=None,
                 depth='Full graph', direction='Both', kind='All types', layout='Circle',
                 isolates=True, labels=False, positions={str(k): v for k, v in positions.items()},
                 pins=[], selection=None, xlim=[-1.5, 1.5], ylim=[-1.5, 1.5],
                 visual_categories=categories, highlight_changes=False, changes_only=False)
    store = SavedViews(db)
    store.save(OVERVIEW, state)
    for name, event, focus in scenes:
        scene_graph = filter_graph(build_graph(visible_cast(db, event), db.relationships(event)),
                                   focus, 'Direct' if focus else 'Full graph')
        scene_positions = layout_positions(scene_graph, {}, set(), 'Circle')
        store.save(name, dict(state, as_of_event=event, focus=focus,
                             depth='Direct' if focus else 'Full graph', labels=True,
                             positions={str(k): v for k, v in scene_positions.items()}))


def opening_view(db):
    store = SavedViews(db)
    return store.load(OVERVIEW) if OVERVIEW in store.names() else None
