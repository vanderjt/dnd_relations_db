"""Graph filters, stable layouts, and validated persistent view state."""
import json
import math
import networkx as nx
from .relationship_semantics import mutual


def filter_graph(graph, focus=None, depth="Full graph", direction="Both", isolates=True):
    if depth != "Full graph" and focus in graph:
        # Expand mutual links only for traversal. The rendered/exported graph
        # retains a single edge and ID for each stored connection.
        traversal = nx.DiGraph(graph)
        traversal.add_edges_from((target, source) for source, target, data in graph.edges(data=True) if mutual(data))
        traversal = traversal if direction == "Outgoing" else traversal.reverse(copy=False) if direction == "Incoming" else traversal.to_undirected()
        distance = 1 if depth == "Direct" else 2
        nodes = nx.single_source_shortest_path_length(traversal, focus, cutoff=distance)
        result = graph.subgraph(nodes).copy()
        if direction != "Both":
            remove = [(source, target, key) for source, target, key, data in result.edges(keys=True, data=True)
                      if not mutual(data) and not (nodes[source] < nodes[target] if direction == "Outgoing" else nodes[source] > nodes[target])]
            result.remove_edges_from(remove)
    elif depth != "Full graph":
        result = graph.subgraph([]).copy()
    else:
        result = graph.copy()
    if not isolates:
        result.remove_nodes_from(list(nx.isolates(result)))
    return result


def layout_positions(graph, positions, pins, layout="Circle", reset=False):
    retained = {node: list(point) for node, point in positions.items() if node in graph}
    if not graph:
        return {}
    fixed = set(retained) & pins if reset else set(retained)
    if len(fixed) == len(graph):
        return retained
    if layout == "Circle":
        computed = nx.circular_layout(graph)
    else:
        computed = nx.spring_layout(graph, pos=retained or None, fixed=list(fixed) or None, seed=42)
    return {node: retained[node] if node in fixed else [float(value) for value in computed[node]] for node in graph}


def drawing_signature(graph):
    """Notes/profile edits update the inspector without repainting the graph."""
    return (tuple(sorted((node, data["name"], data.get("narrative_role"), data.get("classification"), data.get("character_type"), data.get("planned"), data.get("provisional")) for node, data in graph.nodes(data=True))),
            tuple(sorted((source, target, key, data["kind"], data.get("semantics", "directional"), data.get("inverse_label", ""), data.get("category", ""))
                         for source, target, key, data in graph.edges(keys=True, data=True))))


def validate_view(data):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Unsupported saved graph view.")
    for key in ('highlight_changes', 'changes_only'):
        if type(data.get(key, False)) is not bool:
            raise ValueError(f'Invalid saved {key}.')
    categories = data.get('visual_categories', {})
    if not isinstance(categories, dict) or any(not isinstance(key, str) or value not in ('Support', 'Conflict', 'Personal', 'Other') for key, value in categories.items()):
        raise ValueError('Invalid visual categories.')
    scroll = data.get('inspector_scroll', [0, 0])
    if not finite_pair(scroll) or any(value < 0 or value > 1 for value in scroll):
        raise ValueError('Invalid inspector scroll position.')
    if data.get("as_of_event") is not None and (type(data["as_of_event"]) is not int or data["as_of_event"] < 0):
        raise ValueError("Invalid saved event selection.")
    for key, options in (("depth", ("Full graph", "Direct", "Two steps")),
                         ("direction", ("Both", "Incoming", "Outgoing")), ("layout", ("Spring", "Circle"))):
        if data.get(key) not in options:
            raise ValueError(f"Invalid saved {key}.")
    for key in ("isolates", "labels"):
        if type(data.get(key)) is not bool:
            raise ValueError(f"Invalid saved {key}.")
    if not isinstance(data.get("kind"), str):
        raise ValueError("Invalid saved relationship filter.")
    if data.get("focus") is not None and (type(data["focus"]) is not int or data["focus"] < 1):
        raise ValueError("Invalid focus character.")
    positions = data.get("positions")
    if not isinstance(positions, dict):
        raise ValueError("Invalid saved positions.")
    for node, point in positions.items():
        if not str(node).isdigit() or int(node) < 1 or not finite_pair(point):
            raise ValueError("Invalid node coordinates.")
    if not isinstance(data.get("pins"), list) or any(type(node) is not int or node < 1 for node in data["pins"]):
        raise ValueError("Invalid pinned characters.")
    for key in ("xlim", "ylim"):
        if not finite_pair(data.get(key)) or data[key][0] >= data[key][1]:
            raise ValueError("Invalid saved zoom limits.")
    selection = data.get("selection")
    if selection is not None and (not isinstance(selection, list) or len(selection) != 2 or
                                  selection[0] not in ("node", "edge") or type(selection[1]) is not int):
        raise ValueError("Invalid saved selection.")
    return data


def finite_pair(value):
    return isinstance(value, (list, tuple)) and len(value) == 2 and all(
        type(number) in (int, float) and math.isfinite(number) and abs(number) < 1e12 for number in value)


class SavedViews:
    def __init__(self, database):
        self.database = database

    def names(self):
        return [row[0] for row in self.database.connection.execute("SELECT name FROM graph_views ORDER BY name COLLATE NOCASE")]

    def save(self, name, state):
        if not name.strip():
            raise ValueError("Enter a name for this graph view.")
        validate_view(state)
        with self.database.connection:
            self.database.connection.execute("INSERT INTO graph_views VALUES (?,?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload",
                                             (name.strip(), json.dumps(state, allow_nan=False)))

    def load(self, name):
        row = self.database.connection.execute("SELECT payload FROM graph_views WHERE name=?", (name,)).fetchone()
        if row is None:
            raise ValueError("Choose an existing saved view.")
        return validate_view(json.loads(row[0]))

    def delete(self, name):
        with self.database.connection:
            self.database.connection.execute("DELETE FROM graph_views WHERE name=?", (name,))
