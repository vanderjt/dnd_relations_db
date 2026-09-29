"""Scrollable forms with wheel support and automatic keyboard focus reveal."""
import tkinter as tk
from tkinter import ttk
from .theme import style_tk_widget


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, width=1, height=1, takefocus=False)
        style_tk_widget(self.canvas)
        scrollbar = ttk.Scrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.content = ttk.Frame(self.canvas, padding=(0, 0, 12, 0))
        self.window = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.window, width=event.width))
        # Replace the native closed-combobox wheel action before it can select
        # another value. Popdown listboxes retain their own scrolling bindings.
        root = self._root()
        if not getattr(root, '_atlas_combo_wheel', False):
            root._atlas_combo_wheel = True
            for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                root.bind_class('TCombobox', sequence, self.combo_wheel)
        self.top = self.winfo_toplevel()
        self.focus_binding = self.top.bind("<FocusIn>", self.reveal_focus, add="+")
        self.wheel_binding = self.top.bind("<MouseWheel>", self.on_wheel, add="+")

    @staticmethod
    def combo_wheel(event):
        owner = event.widget
        while owner is not None and not isinstance(owner, ScrollFrame):
            owner = getattr(owner, 'master', None)
        direction = (-1 if event.num == 4 else 1) if event.num in (4, 5) else (-1 if event.delta > 0 else 1)
        if owner is not None and (event.delta or event.num in (4, 5)):
            owner.canvas.yview_scroll(direction, 'units')
        return 'break'

    def contains(self, widget):
        return widget is not None and str(widget).startswith(str(self.content) + ".")

    def reveal_focus(self, event):
        if not self.contains(event.widget):
            return
        self.update_idletasks()
        y = event.widget.winfo_rooty() - self.content.winfo_rooty()
        top = self.canvas.canvasy(0)
        height = self.canvas.winfo_height()
        bottom = y + event.widget.winfo_height()
        if y < top or bottom > top + height:
            desired = y if y < top or event.widget.winfo_height() > height else bottom - height
            self.canvas.yview_moveto(max(0, desired) / max(1, self.content.winfo_height()))

    def on_wheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        if isinstance(widget, (tk.Text, ttk.Treeview)) and not getattr(widget, 'atlas_outer_scroll', False):
            return
        # Toplevel bindings run in creation order. Only the nearest ScrollFrame
        # may consume this event, including its content/canvas background.
        owner = widget
        while owner is not None and not isinstance(owner, ScrollFrame):
            owner = getattr(owner, 'master', None)
        if owner is self and event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            # Contain at boundaries: one gesture never scrolls a second pane.
            return "break"

    def destroy(self):
        self.top.unbind("<FocusIn>", self.focus_binding)
        self.top.unbind("<MouseWheel>", self.wheel_binding)
        super().destroy()
