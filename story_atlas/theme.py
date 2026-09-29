"""Shared visual vocabulary and live styling for ttk, Tk, and plotting widgets.

Use ``Primary.TButton`` for the single commit action in a region;
``Secondary.TButton`` for a nearby non-destructive alternative; and
``Navigation.TButton`` for changing location or view. ``ToolActive.TButton``
marks a pressed, persistent tool state and must retain its text label.
``Content.TFrame`` groups primary content, while ``Detail.TFrame`` and the
``read_only_text_area`` helper present selectable, non-editable information.
``Context`` styles communicate unsaved or historical context alongside text,
``Success`` confirms a completed action, ``Validation`` identifies field-level
problems, and ``Danger.TButton`` is reserved for explicitly destructive actions.

``Accent.TButton`` and ``Error.TLabel`` remain compatibility aliases while
screens migrate deliberately to the semantic names.
"""
import tkinter as tk
from tkinter import ttk, font

SPACE = {"small": 6, "medium": 12, "large": 20}
# Keep this public mapping close to the styles so future screens use semantics,
# not palette colors, when they adopt the vocabulary.
STYLE_GUIDE = {
    "Primary.TButton": "Commit the main action for this task region.",
    "Secondary.TButton": "Offer a routine, non-destructive alternative.",
    "Navigation.TButton": "Move to another view, step, or destination.",
    "ToolActive.TButton": "Show a labeled tool that remains active/pressed.",
    "Content.TFrame": "Group the content currently being explored.",
    "Detail.TFrame": "Present read-only, selectable details rather than a form.",
    "Context.TFrame": "Call out explicit unsaved or historical context.",
    "Success.TLabel": "Confirm a completed save or record action.",
    "Validation.TLabel": "Place validation feedback directly by its field.",
    "Danger.TButton": "Reserve for an explicitly labeled destructive action.",
}
PALETTES = {
    "dark": dict(bg="#101722", panel="#192333", detail="#1d2939", input="#141f2e", context="#3b3321",
                 text="#e6edf7", muted="#a5b5c9", accent="#61d4bf", on_accent="#101722",
                 hover="#30435a", primary_hover="#80e5d1", primary_pressed="#43b8a6",
                 selected="#315469", navigation="#26364b", context_text="#ffe09a", success="#8ee6c9", error="#ffb4ab",
                 disabled="#8190a3", border="#506078", focus="#9cecff"),
    "light": dict(bg="#f3f6fa", panel="#ffffff", detail="#f7f9fc", input="#ffffff", context="#fff3d8",
                  text="#18283d", muted="#506078", accent="#146d61", on_accent="#ffffff",
                  hover="#e0e9f2", primary_hover="#0f5c52", primary_pressed="#0b4a42",
                  selected="#c8e4ef", navigation="#e8eef5", context_text="#705100", success="#116b52", error="#a12030",
                  disabled="#687689", border="#8b9aab", focus="#075f9f"),
}
BG, PANEL, TEXT, MUTED, ACCENT = (PALETTES["dark"][key] for key in ("bg", "panel", "text", "muted", "accent"))


def palette(widget):
    return getattr(widget._root(), "atlas_palette", PALETTES["dark"])


def style_tk_widget(widget):
    """ttk styles do not affect classic Tk text/canvas/scrollbar widgets."""
    colors = palette(widget)
    if isinstance(widget, ttk.Widget) and not isinstance(widget, ttk.Combobox):
        return
    if isinstance(widget, tk.Text):
        is_detail = getattr(widget, "atlas_read_only_detail", False)
        widget.configure(bg=colors["detail"] if is_detail else colors["input"], fg=colors["text"], insertbackground=colors["accent"],
                         selectbackground=colors["selected"], selectforeground=colors["text"],
                         # Details retain a quiet border, but their focus cue is still visible
                         # to keyboard users and remains distinct from editable-field styling.
                         font="AtlasBody", highlightthickness=1 if is_detail else 2,
                         highlightbackground=colors["border"], highlightcolor=colors["focus"])
    elif isinstance(widget, (tk.Tk, tk.Toplevel, tk.Frame, tk.Canvas)):
        widget.configure(background=colors["bg"])
    elif isinstance(widget, tk.Scrollbar):
        widget.configure(bg=colors["panel"], troughcolor=colors["bg"],
                         activebackground=colors["hover"], highlightthickness=0)
    if isinstance(widget, ttk.Combobox):
        popup = widget.tk.call("ttk::combobox::PopdownWindow", str(widget))
        widget.tk.call(f"{popup}.f.l", "configure", "-background", colors["panel"],
                       "-foreground", colors["text"], "-selectbackground", colors["selected"],
                       "-selectforeground", colors["text"], "-font", "AtlasBody")


def style_tree(widget):
    style_tk_widget(widget)
    for child in widget.winfo_children():
        style_tree(child)


def apply_theme(root, mode="dark", text_size=10):
    root.atlas_palette = colors = PALETTES[mode]
    root.atlas_text_size = text_size
    if not hasattr(root, "atlas_fonts"):
        root.atlas_fonts = {name: font.Font(root=root, name=name, family="Segoe UI")
                            for name in ("AtlasBody", "AtlasTitle", "AtlasHeading")}
    for name, size, weight in (("AtlasBody", text_size, "normal"),
                               ("AtlasTitle", text_size + 8, "bold"),
                               ("AtlasHeading", text_size + 3, "bold")):
        root.atlas_fonts[name].configure(size=size, weight=weight)
    root.option_add("*Font", "AtlasBody")
    style = ttk.Style(root)
    if style.theme_use() != "clam":
        style.theme_use("clam")
    style.configure(".", background=colors["bg"], foreground=colors["text"],
                    bordercolor=colors["border"], lightcolor=colors["border"], darkcolor=colors["border"],
                    font="AtlasBody", focuscolor=colors["focus"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
    style.configure("Content.TFrame", background=colors["panel"])
    style.configure("Detail.TFrame", background=colors["detail"], relief="solid", borderwidth=1)
    style.configure("Detail.TLabel", background=colors["detail"], foreground=colors["text"])
    style.configure("Context.TFrame", background=colors["context"], relief="solid", borderwidth=1)
    style.configure("Context.TLabel", background=colors["context"], foreground=colors["context_text"])
    style.configure("Title.TLabel", font="AtlasTitle")
    style.configure("Heading.TLabel", font="AtlasHeading")
    style.configure("Muted.TLabel", foreground=colors["muted"])
    style.configure("Content.Heading.TLabel", background=colors["panel"], font="AtlasHeading")
    style.configure("Content.Muted.TLabel", background=colors["panel"], foreground=colors["muted"])
    style.configure("Validation.TLabel", foreground=colors["error"])
    style.configure("Error.TLabel", foreground=colors["error"])
    style.configure("Success.TLabel", foreground=colors["success"])
    button_styles = (("TButton", colors["panel"], colors["text"], colors["hover"], colors["selected"]),
                     ("Primary.TButton", colors["accent"], colors["on_accent"], colors["primary_hover"], colors["primary_pressed"]),
                     # Compatibility alias for screens not included in this pilot.
                     ("Accent.TButton", colors["accent"], colors["on_accent"], colors["primary_hover"], colors["primary_pressed"]),
                     ("Secondary.TButton", colors["panel"], colors["text"], colors["hover"], colors["selected"]),
                     ("Navigation.TButton", colors["bg"], colors["text"], colors["navigation"], colors["selected"]),
                     ("Danger.TButton", colors["panel"], colors["error"], colors["hover"], colors["selected"]),
                     # Active tools retain their selected fill even while hovered.
                     ("ToolActive.TButton", colors["selected"], colors["text"], colors["selected"], colors["selected"]))
    for name, background, foreground, hover, pressed in button_styles:
        style.configure(name, background=background, foreground=foreground, padding=(12, 7), borderwidth=1)
        style.map(name, background=[("disabled", colors["bg"]), ("pressed", pressed), ("active", hover)],
                  foreground=[("disabled", colors["disabled"])],
                  bordercolor=[("focus", colors["focus"])])
    # Menubuttons use their own ttk element, so expose the secondary treatment
    # separately for compact, less-frequent action menus.
    style.configure("TMenubutton", background=colors["panel"], foreground=colors["text"],
                    padding=(10, 7), borderwidth=1)
    style.map('TMenubutton', background=[('active', colors['hover'])], bordercolor=[('focus', colors['focus'])])
    style.configure("Secondary.TMenubutton", background=colors["panel"], foreground=colors["text"],
                    padding=(10, 7), borderwidth=1)
    style.map("Secondary.TMenubutton", background=[("disabled", colors["bg"]), ("pressed", colors["selected"]),
                                                     ("active", colors["hover"])],
              foreground=[("disabled", colors["disabled"])], bordercolor=[("focus", colors["focus"])])
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=colors["input"], foreground=colors["text"],
                        insertcolor=colors["text"], padding=6, arrowsize=text_size + 5)
        style.map(name, fieldbackground=[("disabled", colors["bg"]), ("readonly", colors["panel"])],
                  foreground=[("disabled", colors["disabled"]), ("readonly", colors["text"])],
                  bordercolor=[("invalid", colors["error"]), ("focus", colors["focus"])])
    style.configure("Treeview", background=colors["panel"], fieldbackground=colors["panel"],
                    foreground=colors["text"], rowheight=root.atlas_fonts["AtlasBody"].metrics("linespace") + 14)
    style.configure("Treeview.Heading", background=colors["bg"], foreground=colors["muted"], padding=6)
    style.map("Treeview", background=[("selected", colors["selected"])],
              foreground=[("selected", colors["text"])])
    style.configure("TNotebook.Tab", background=colors["panel"], padding=(10, 7))
    style.map("TNotebook.Tab", background=[("selected", colors["selected"])])
    for name in ("TCheckbutton", "TRadiobutton"):
        style.map(name, foreground=[("disabled", colors["disabled"])],
                  background=[("active", colors["hover"])], indicatorbackground=[("selected", colors["accent"])])
    root.option_add("*TCombobox*Listbox.background", colors["panel"])
    root.option_add("*TCombobox*Listbox.foreground", colors["text"])
    root.option_add("*TCombobox*Listbox.font", "AtlasBody")
    style_tree(root)
