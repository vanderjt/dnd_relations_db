"""Route shortcuts to the focused editor or to committed story history."""
import sqlite3
import tkinter as tk
from tkinter import ttk
from weakref import WeakKeyDictionary, WeakSet


class UndoControls:
    def __init__(self, app):
        self.app = app
        self.entries = WeakKeyDictionary()
        self.texts = WeakSet()
        self.tag = 'StoryAtlasUndo'
        app.bind_class(self.tag, '<Control-z>', lambda event: self.shortcut(event, False))
        app.bind_class(self.tag, '<Control-y>', lambda event: self.shortcut(event, True))
        app.bind_class(self.tag, '<Control-Shift-Z>', lambda event: self.shortcut(event, True))
        app.bind_class(self.tag, '<FocusIn>', self.focus_entry)
        app.bind_class(self.tag, '<KeyRelease>', self.record_entry)
        app.bind_class(self.tag, '<<ComboboxSelected>>', self.record_entry)
        app.bind_all('<Map>', lambda event: self.install(event.widget), add='+')
        self.install(app)

    def install(self, widget):
        if not isinstance(widget, tk.Misc):
            return
        if self.tag not in widget.bindtags():
            widget.bindtags((self.tag, *widget.bindtags()))
        for child in widget.winfo_children():
            self.install(child)

    def is_entry(self, widget):
        return isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox, tk.Spinbox, ttk.Spinbox))

    def reset_editor(self, widget):
        if self.is_entry(widget):
            self.entries[widget] = ([widget.get()], [])
        else:
            self.entries.pop(widget, None)
        self.texts.discard(widget)
        if isinstance(widget, tk.Text):
            widget.edit_reset()
        for child in widget.winfo_children():
            self.reset_editor(child)

    def focus_entry(self, event):
        widget = event.widget
        if isinstance(widget, tk.Text) and widget not in self.texts:
            widget.edit_reset()
            self.texts.add(widget)
        if self.is_entry(widget):
            value = widget.get()
            if widget not in self.entries or self.entries[widget][0][-1] != value:
                self.entries[widget] = ([value], [])

    def record_entry(self, event):
        widget = event.widget
        if not self.is_entry(widget) or event.keysym in ('z', 'y', 'Z') and event.state & 4:
            return
        state = self.entries.setdefault(widget, ([widget.get()], []))
        if state[0][-1] != widget.get():
            state[0].append(widget.get())
            del state[0][:-100]
            state[1].clear()

    def shortcut(self, event, redo):
        widget = event.widget
        if isinstance(widget, tk.Text) and not getattr(widget, 'atlas_read_only_detail', False) and str(widget['state']) == 'normal':
            try:
                widget.edit_redo() if redo else widget.edit_undo()
            except tk.TclError:
                pass
            return 'break'
        if self.is_entry(widget) and str(widget['state']) != 'disabled':
            past, future = self.entries.setdefault(widget, ([widget.get()], []))
            if past[-1] != widget.get():
                past.append(widget.get())
                future.clear()
            if redo and future:
                past.append(future.pop())
            elif not redo and len(past) > 1:
                future.append(past.pop())
            else:
                return 'break'
            if isinstance(widget, ttk.Combobox):
                widget.set(past[-1])
                widget.event_generate('<<ComboboxSelected>>')
            else:
                widget.delete(0, 'end')
                widget.insert(0, past[-1])
                widget.icursor('end')
            return 'break'
        self.change(redo)
        return 'break'

    def change(self, redo=False):
        app = self.app
        verb = 'Redo' if redo else 'Undo'
        if app.grab_current() is not None:
            app.status.set('Finish or close the current dialog before undoing a saved change.')
            return False
        task = app.simple.task
        if app.characters.values() != app.characters.original or (task and task.values() != task.original):
            app.status.set('Save or discard the current edits before undoing a saved change. In a field, Ctrl+Z undoes typing.')
            return False
        try:
            result = app.database.enable_undo().apply(redo)
        except (ValueError, sqlite3.Error) as error:
            app.status.set(f'{verb} could not be completed: {error}')
            return False
        if not result:
            app.status.set(f'Nothing to {verb.lower()} in this story session.')
            return False
        if result == 'story':
            app.characters.draft.cancel()
            ident = app.characters.character_id
            row = next((r for r in app.database.characters() if r['id'] == ident), None)
            app.characters.load(row)
            app.characters.clear_undo()
            app.relationships.clear_undo()
            app.simple.remove_task()
            app.simple.clear_selection()
            app.simple.recent_creation = None
            app.navigation.clear()
            app.refresh(f'{verb} complete.')
            app.simple.graph.ensure_current()
        else:
            app.status.set(f'{verb} graph change complete.')
        return True

    def record_graph(self, before, after):
        def restore(state):
            graph = self.app.simple.graph if self.app.mode.get() == 'Simple' else self.app.graph
            graph.apply_state(state)
        self.app.database.enable_undo().record_view(before, after, restore)
