"""Labeled ttk controls backed by Matplotlib's normal navigation machinery."""
import tkinter as tk
from tkinter import ttk
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from .widgets import ActionBar


class CanvasNavigation(NavigationToolbar2):
    # Reuse Tk's rubber-band drawing without constructing its generic toolbar.
    draw_rubberband = NavigationToolbar2Tk.draw_rubberband
    remove_rubberband = NavigationToolbar2Tk.remove_rubberband


class GraphControls(ActionBar):
    """Navigation tools, deliberately separate from graph scope controls."""
    def __init__(self, parent, canvas, reset, export, saved_views, layout_variable=None, layout_changed=None):
        super().__init__(parent)
        self.navigation = CanvasNavigation(canvas)
        self.zoom = self.add(ttk.Button(self, text="Zoom", style="Secondary.TButton", command=lambda: self.toggle("zoom")))
        self.pan = self.add(ttk.Button(self, text="Pan", style="Secondary.TButton", command=lambda: self.toggle("pan")))
        self.add(ttk.Button(self, text="Fit", style="Secondary.TButton", command=self.fit))
        more = ttk.Menubutton(self, text="View & layout", style="Secondary.TMenubutton")
        self.actions = actions = tk.Menu(more, tearoff=False)
        self.zoom_active = tk.BooleanVar(self, False)
        self.pan_active = tk.BooleanVar(self, False)
        actions.add_checkbutton(label='Zoom rectangle', variable=self.zoom_active, command=lambda: self.toggle('zoom'))
        actions.add_checkbutton(label='Pan tool', variable=self.pan_active, command=lambda: self.toggle('pan'))
        actions.add_command(label='Fit view', command=self.fit)
        actions.add_separator()
        actions.add_command(label="Back", command=self.navigation.back)
        actions.add_command(label="Forward", command=self.navigation.forward)
        actions.add_separator()
        actions.add_command(label="Reset layout", command=reset)
        if layout_variable is not None and layout_changed is not None:
            layout = tk.Menu(actions, tearoff=False)
            for value in ("Spring", "Circle"):
                layout.add_radiobutton(label=value, variable=layout_variable, value=value, command=layout_changed)
            actions.add_cascade(label="Layout", menu=layout)
        actions.add_command(label="Saved views…", command=saved_views)
        actions.add_separator()
        actions.add_command(label="Export snapshot…", command=export)
        from .graph_legend import add_menu_explanations
        from .character_type import TYPE_COLORS
        legend = tk.Menu(actions, tearoff=False)
        for label, color in TYPE_COLORS.items():
            legend.add_command(label='● ' + label, foreground=color, state='disabled')
        add_menu_explanations(legend)
        actions.add_separator()
        actions.add_cascade(label='Legend · dots & links', menu=legend)
        more.configure(menu=actions)
        self.add(more)

    def toggle(self, name):
        getattr(self.navigation, name)()
        self.update_buttons()

    def update_buttons(self):
        self.zoom_active.set(self.navigation.mode.name == 'ZOOM')
        self.pan_active.set(self.navigation.mode.name == 'PAN')
        self.zoom.configure(style="ToolActive.TButton" if self.navigation.mode.name == "ZOOM" else "Secondary.TButton")
        self.pan.configure(style="ToolActive.TButton" if self.navigation.mode.name == "PAN" else "Secondary.TButton")

    def clear_mode(self):
        if self.navigation.mode.name == "ZOOM":
            self.navigation.zoom()
        elif self.navigation.mode.name == "PAN":
            self.navigation.pan()
        self.update_buttons()

    def fit(self):
        self.clear_mode()
        if hasattr(self, "fit_callback"):
            self.fit_callback()
        else:
            self.navigation.home()

    def reset_history(self):
        self.navigation.update()
        self.navigation.push_current()
