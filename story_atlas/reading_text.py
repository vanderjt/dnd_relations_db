"""Selectable wrapping prose that uses its parent reading pane's scrollbar."""


def fit_reading_text(widget):
    if not getattr(widget, 'atlas_outer_scroll', False) or widget.winfo_width() < 20:
        return
    count = widget.count('1.0', 'end', 'displaylines')
    height = max(2, count[0] if count else 2)
    if int(widget.cget('height')) != height:
        widget.configure(height=height)
    widget.yview_moveto(0)


def use_outer_scroll(widget):
    widget.atlas_outer_scroll = True
    widget.vbar.pack_forget()
    widget.bind('<Configure>', lambda _: fit_reading_text(widget), add='+')
    fit_reading_text(widget)
