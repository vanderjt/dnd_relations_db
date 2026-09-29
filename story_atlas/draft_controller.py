"""Debounced editor drafts: no committed saves or activity noise while typing."""
import sqlite3
import tkinter as tk
from .models import LONG_FIELDS


class DraftController:
    def __init__(self, view):
        self.view = view
        self.pending = None
        self.loading = False
        view.editor.field_widgets['tags'].pending.trace_add('write', lambda *_: self.schedule())
        self.status = tk.StringVar(view, value="Changes are committed only with Save changes.")
        for field, widget in view.fields.items():
            if field in LONG_FIELDS:
                widget.edit_modified(False)
                widget.bind("<<Modified>>", lambda event: self.text_changed(event.widget))
            else:
                widget.trace_add("write", lambda *_: self.schedule())

    def set_status(self, text, kind="context"):
        setter = getattr(self.view, "set_draft_status", None)
        if setter:
            setter(text, kind)
        else:
            self.status.set(text)

    def text_changed(self, widget):
        if widget.edit_modified():
            widget.edit_modified(False)
            self.schedule()

    def cancel(self):
        if self.pending is not None:
            self.view.after_cancel(self.pending)
            self.pending = None

    def schedule(self):
        if self.loading:
            return
        self.cancel()
        if hasattr(self.view, "update_save"):
            self.view.update_save()
        self.set_status("Unsaved changes · saving a recovery draft…")
        self.pending = self.view.after(1000, self.flush)

    def flush(self):
        # Explicit flushes must cancel the scheduled callback too; otherwise a
        # stale callback can outlive this editor or run against the next story.
        self.cancel()
        try:
            if self.view.values() == self.view.original:
                self.view.database.drafts.discard(self.view.character_id)
                self.set_status("No uncommitted changes.", "muted")
            else:
                self.view.database.drafts.save(self.view.character_id, self.view.values())
                self.set_status("Recovery draft saved · use Save changes to commit.")
        except sqlite3.Error as error:
            self.set_status(f"Draft could not be saved: {error}", "error")

    def discard(self):
        self.cancel()
        self.view.database.drafts.discard(self.view.character_id)
        self.set_status("Draft discarded.", "muted")
