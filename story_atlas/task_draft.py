"""Simple task snapshots use the shared per-database recovery store."""
import sqlite3


class TaskDraft:
    def __init__(self, view, key):
        self.view, self.key = view, key
        self.pending = None
        self.last = view.values()
        self.discarded = False
        self.tick()

    def tick(self):
        self.pending = None
        if self.view.values() != self.last:
            self.flush()
        if hasattr(self.view, 'update_save'):
            self.view.update_save()
        self.pending = self.view.after(500, self.tick)

    def flush(self):
        try:
            if self.view.values() != self.view.original:
                self.view.database.drafts.save_task(self.key, self.view.draft_payload())
            self.last = self.view.values()
        except sqlite3.Error as error:
            self.view.error.set(f'Recovery draft could not be saved: {error}')

    def cancel(self):
        if self.pending is not None:
            self.view.after_cancel(self.pending)
            self.pending = None

    def discard(self):
        self.cancel()
        self.view.database.drafts.discard_task(self.key)
        self.discarded = True

    def close(self):
        if not self.discarded:
            self.flush()
        self.cancel()
