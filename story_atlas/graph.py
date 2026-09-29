"""Graph construction and rendering are independent of the GUI."""
import networkx as nx


def build_graph(characters, relationships, kind="All types"):
    graph = nx.MultiDiGraph()
    for character in characters:
        graph.add_node(character["id"], **character)
    for relationship in relationships:
        if kind == "All types" or kind in (relationship["kind"], relationship.get("inverse_label", "")):
            graph.add_edge(relationship["source_id"], relationship["target_id"],
                           key=relationship["id"], **relationship)
    return graph


def draw_graph(figure, graph, layout="Circle", labels=True, colors=None, text_size=10):
    """Standalone rendering entry point, also used by storage integration tests."""
    from .graph_render import GraphRenderer
    from .graph_state import layout_positions
    positions = layout_positions(graph, {}, set(), layout)
    GraphRenderer(figure).draw(graph, positions, set(), labels, colors, text_size)
    return positions
