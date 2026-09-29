"""Small reusable UI helpers."""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from .theme import style_tk_widget, palette, SPACE


def text_area(parent, height=8):
    widget = ScrolledText(parent, height=height, width=24, wrap="word", relief="flat",
                          padx=12, pady=10, undo=True)
    style_tk_widget(widget)
    style_tk_widget(widget.vbar)
    return widget


def read_only_text_area(parent, height=8):
    """Create a scrollable, selectable detail surface that is not an input.

    Use :func:`set_read_only_text` to update it. Disabled Tk text still supports
    keyboard focus, selection, scrolling, and copying, while preventing edits.
    """
    widget = text_area(parent, height=height)
    widget.atlas_read_only_detail = True
    colors = palette(parent)
    widget.configure(bg=colors["detail"], relief="solid", bd=1, highlightthickness=1,
                     highlightbackground=colors["border"], highlightcolor=colors["focus"],
                     takefocus=True, state="disabled")
    # Text's default Tab binding inserts a tab, even when editing is disabled.
    # Detail surfaces must let keyboard users leave them normally.
    def traverse(backward=False):
        target = widget.tk_focusPrev() if backward else widget.tk_focusNext()
        target.focus_set()
        return "break"

    def select_all(_event):
        widget.tag_add("sel", "1.0", "end-1c")
        return "break"

    widget.bind("<Tab>", lambda _: traverse())
    widget.bind("<Shift-Tab>", lambda _: traverse(True))
    widget.bind("<Control-a>", select_all)
    return widget


def set_read_only_text(widget, text):
    """Replace detail text without ever leaving the selectable widget editable."""
    if widget.get("1.0", "end-1c") == text:
        return  # Unrelated refreshes must not discard the reader's selection/scroll.
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", text)
    widget.configure(state="disabled")
    if getattr(widget, 'atlas_outer_scroll', False):
        from .reading_text import fit_reading_text
        fit_reading_text(widget)


def table(parent, columns):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=tuple(columns), show="headings", selectmode="browse")
    for key, title in columns.items():
        tree.heading(key, text=title)
        tree.column(key, width=160, minwidth=70)
    scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    horizontal = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
    tree.configure(xscrollcommand=horizontal.set)
    tree.grid(row=0, column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    frame.pack(fill="both", expand=True, pady=10)
    return tree


def wrapping_label(parent, **kwargs):
    label = ttk.Label(parent, **kwargs)
    label.bind("<Configure>", lambda event: label.configure(wraplength=max(100, event.width)))
    return label


def field_error(parent, variable, after):
    """Reserve space for validation only when a field has feedback."""
    label = wrapping_label(parent, textvariable=variable, style='Validation.TLabel')
    def update(*_):
        if variable.get():
            label.pack(fill='x', after=after, pady=(2, 0))
        else:
            label.pack_forget()
    variable.trace_add('write', update)
    update()
    return label


class ActionBar(ttk.Frame):
    """Wrap controls onto additional rows when the window or text size changes."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.items = []
        self.bind("<Configure>", self.reflow)

    def add(self, widget):
        self.items.append(widget)
        self.reflow()
        return widget

    def reflow(self, _event=None):
        width = max(1, self.winfo_width())
        row, column, used = 0, 0, 0
        for widget in self.items:
            needed = widget.winfo_reqwidth() + SPACE["small"]
            if used and used + needed > width:
                row, column, used = row + 1, 0, 0
            widget.grid(row=row, column=column, sticky="w", padx=(0, SPACE["small"]), pady=3)
            column += 1
            used += needed
