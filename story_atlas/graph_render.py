from .character_type import color as type_color, label as type_label_text
"""Persistent Matplotlib axes and one pickable arrow per relationship."""
from collections import defaultdict
from matplotlib.patches import FancyArrowPatch
from matplotlib.lines import Line2D
import networkx as nx
from .theme import PALETTES
from .relationship_semantics import mutual, type_label

from .graph_legend import EDGE_STYLES, handles as legend_handles


def category(kind):
    # Type names carry no inferred narrative meaning.
    return "Other"


class GraphRenderer:
    def __init__(self, figure):
        self.figure = figure
        self.axes = figure.add_subplot(111)
        self.figure.subplots_adjust(left=.04, right=.96, top=.97, bottom=.06)
        self.edge_artists, self.edge_labels, self.node_labels = {}, {}, {}
        self.draw_count = 0
        self.focus = None
        figure.canvas.mpl_connect('resize_event', lambda _: self.layout_legend())

    def layout_legend(self):
        """Reserve a header for the key so it never covers character nodes."""
        legend = self.axes.get_legend()
        if legend is None:
            self.figure.subplots_adjust(top=.92)
            return
        font = legend.get_texts()[0].get_fontsize()
        height_points = self.figure.get_figheight() * 72
        reserved = 5 * font * 1.5 + 38  # Five rows plus scope title and padding.
        self.figure.subplots_adjust(top=max(.25, 1 - reserved / max(height_points, 1)))

    def draw(self, graph, positions, pins, labels=True, colors=None, text_size=10, limits=None, selection=None):
        self.draw_count += 1
        self.graph, self.positions, self.pins = graph, positions, pins
        self.colors = colors or PALETTES["dark"]
        self.show_labels = labels
        self.axes.clear()
        self.axes.set_axis_off()
        self.axes.set_facecolor(self.colors["bg"])
        self.figure.set_facecolor(self.colors["bg"])
        self.edge_artists, self.edge_labels, self.node_labels, self.curves = {}, {}, {}, {}
        self.nodes = list(graph)
        if not graph:
            self.axes.text(.5, .5, "No characters in this view.\nChoose a focus or adjust the filters.",
                           ha="center", va="center", color=self.colors["muted"], transform=self.axes.transAxes,
                           fontsize=text_size)
            self.fit_limits = ((-1, 1), (-1, 1))
            self.axes.set_xlim(*(limits or self.fit_limits)[0])
            self.axes.set_ylim(*(limits or self.fit_limits)[1])
            return
        self.fit_limits = self.bounds()
        self.axes.set_xlim(*(limits or self.fit_limits)[0])
        self.axes.set_ylim(*(limits or self.fit_limits)[1])
        self.node_artist = nx.draw_networkx_nodes(graph, positions, ax=self.axes, node_size=500,
                                                node_color=[type_color(graph.nodes[node]) if not graph.nodes[node].get('planned') else self.colors['panel'] for node in graph], linewidths=2)
        self.node_artist.set_linestyles(['dashed' if graph.nodes[node].get('planned') or graph.nodes[node].get('provisional') else 'solid' for node in graph])
        self.node_artist.set_picker(8)
        pairs = defaultdict(list)
        for source, target, ident, data in graph.edges(keys=True, data=True):
            pairs[tuple(sorted((source, target)))].append((source, target, ident, data))
        for pair, edges in pairs.items():
            for index, (source, target, ident, data) in enumerate(sorted(edges)):
                radius = (index - (len(edges) - 1) / 2) * .28
                if source != pair[0]:
                    radius = -radius
                color, style = EDGE_STYLES[data.get('category') or getattr(self, 'visual_categories', {}).get(data['kind'], 'Other')]
                if data.get('ended_here'):
                    style = 'dashed'
                patch = FancyArrowPatch(positions[source], positions[target], arrowstyle="<|-|>" if mutual(data) else "-|>",
                                       connectionstyle=f"arc3,rad={radius}", mutation_scale=15,
                                       shrinkA=14, shrinkB=14, linewidth=1.5, color=color,
                                       linestyle=style, picker=6, zorder=1)
                self.axes.add_patch(patch)
                self.edge_artists[ident] = patch
                self.curves[ident] = (source, target, radius)
                if labels:
                    self.edge_labels[ident] = self.axes.text(*self.label_point(source, target, radius),
                        f"{type_label(data)}{' ↔' if mutual(data) else ''}", fontsize=max(6, text_size - 2), color=self.colors["text"],
                        ha="center", va="center", zorder=3,
                        bbox=dict(facecolor=self.colors["bg"], edgecolor="none", alpha=.8, pad=1))
        for node in self.nodes:
            self.node_labels[node] = self.axes.annotate(f"{graph.nodes[node]['name']}", positions[node],
                xytext=(0, -18), textcoords="offset points", ha="center", va="top",
                color=self.colors["text"], fontsize=max(7, text_size - 1))
        legend = self.axes.legend(handles=legend_handles(), loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2, fontsize=max(7, text_size - 2),
                                  facecolor=self.colors["panel"], edgecolor=self.colors["border"])
        for text in legend.get_texts():
            text.set_color(self.colors["text"])
        self.layout_legend()
        self.highlight(selection)

    def bounds(self):
        points = [self.positions[node] for node in self.graph]
        xs, ys = zip(*points)
        margin = max(max(xs) - min(xs), max(ys) - min(ys), 1) * .22
        return ((min(xs) - margin, max(xs) + margin), (min(ys) - margin, max(ys) + margin))

    def label_point(self, source, target, radius):
        x0, y0 = self.positions[source]
        x1, y1 = self.positions[target]
        return ((x0+x1)/2 + (y1-y0)*radius/2, (y0+y1)/2 - (x1-x0)*radius/2)

    def move_node(self, node, point):
        self.positions[node] = list(point)
        self.node_artist.set_offsets([self.positions[ident] for ident in self.nodes])
        self.node_labels[node].xy = point
        for ident, (source, target, radius) in self.curves.items():
            if node in (source, target):
                self.edge_artists[ident].set_positions(self.positions[source], self.positions[target])
                if ident in self.edge_labels:
                    self.edge_labels[ident].set_position(self.label_point(source, target, radius))

    def highlight(self, selection):
        if not self.graph:
            return
        selected_node = selection[1] if selection and selection[0] == "node" else None
        near = {selected_node, self.focus}
        for node in tuple(near):
            if node in self.graph:
                near.update(self.graph.predecessors(node))
                near.update(self.graph.successors(node))
        if selection and selection[0] == 'edge' and selection[1] in self.curves:
            near.update(self.curves[selection[1]][:2])
        self.node_artist.set_edgecolors([self.colors["focus"] if node == selected_node else self.colors["border"]
                                          for node in self.nodes])
        self.node_artist.set_linewidths([4 if node == selected_node else 3 if node in self.pins else 2
                                         for node in self.nodes])
        # Size, outline width, and literal labels keep all three states distinct
        # without borrowing the relationship-edge color vocabulary.
        self.node_artist.set_sizes([850 if node == self.focus else 650 if node in self.pins else 500
                                    for node in self.nodes])
        for node in self.nodes:
            data = self.graph.nodes[node]
            states = [type_label_text(data)]
            if data.get('planned'):
                states.append('PLANNED · not introduced yet')
            if data.get('provisional'):
                states.append('NEW CHARACTER · unsaved')
            ordered = getattr(self, 'ordered_selection', [])
            if node in ordered:
                states.append('SOURCE' if ordered.index(node) == 0 else f'TARGET {ordered.index(node)}')
            if node == self.focus:
                states.append("FOCUS")
            if node == selected_node:
                states.append("SELECTED")
            if node in self.pins:
                states.append("PINNED")
            self.node_labels[node].set_text(f"{self.graph.nodes[node]['name']}" +
                                              (f"\n{' · '.join(states)}" if states else ""))
            self.node_labels[node].set_visible(len(self.nodes) <= 35 or node in near or node in self.pins or node in ordered)
        for ident, patch in self.edge_artists.items():
            changed = ident in getattr(self, 'changed_ids', set())
            patch.set_linewidth(4.5 if selection == ('edge', ident) else 3 if changed else 1.5)
            if ident in self.edge_labels:
                source, target, _ = self.curves[ident]
                data = self.graph.edges[source, target, ident]
                self.edge_labels[ident].set_text(f"{type_label(data)}{' ↔' if mutual(data) else ''}" + (' · ENDED HERE' if data.get('ended_here') else ' · CHANGED' if changed else ''))
                self.edge_labels[ident].set_visible(self.show_labels and (len(self.edge_artists) <= 60 or selection == ('edge', ident) or selected_node in (source, target) or changed))

    def pick_node(self, event):
        if not self.graph:
            return None
        hits = []
        for node in self.nodes:
            x, y = self.axes.transData.transform(self.positions[node])
            distance = (event.x-x)**2 + (event.y-y)**2
            if distance <= 20**2:
                hits.append((distance, node))
        return min(hits)[1] if hits else None

    def pick_edge(self, event):
        return next((ident for ident, artist in self.edge_artists.items() if artist.contains(event)[0]), None)
