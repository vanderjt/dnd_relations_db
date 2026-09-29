"""An editable ttk selector with case-insensitive substring suggestions."""
from tkinter import ttk


class SearchableCombobox(ttk.Combobox):
    def __init__(self, parent, variable, choices=(), **kwargs):
        super().__init__(parent, textvariable=variable, **kwargs)
        self.variable = variable
        self.choices = ()
        self.set_choices(choices)
        self.trace_id = variable.trace_add("write", self.filter_choices)
        self.bind("<Button-1>", self.open_from_text)

    def set_choices(self, choices):
        self.choices = tuple(choices)
        self.filter_choices()

    def filter_choices(self, *_):
        query = self.variable.get().strip().casefold()
        # A selected value should not prevent switching to another option.
        exact = any(query == value.casefold() for value in self.choices)
        matches = self.choices if exact else tuple(
            value for value in self.choices if query in value.casefold())
        self.configure(values=matches)

    def open_from_text(self, event):
        if "textarea" in self.identify(event.x, event.y):
            self.focus_set()
            # Native editable combobox text behavior retains cursor placement.
            return None

    def destroy(self):
        self.variable.trace_remove("write", self.trace_id)
        super().destroy()
