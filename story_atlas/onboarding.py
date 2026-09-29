"""First launch chooses a story before creating the main application."""
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .backup import publish_database
from .database import Database
from .sample_story import new_sample
from .paths import validate_writable_location, resource
from .theme import apply_theme
from .widgets import wrapping_label
from .scroll_frame import ScrollFrame


def resume_path(settings, explicit=None):
    if explicit is not None:
        return validate_writable_location(explicit)
    value = settings.values.get("last_story", "")
    return validate_writable_location(value) if value and Path(value).is_file() else None


def create_empty(destination):
    return publish_database(validate_writable_location(destination), lambda path: Database(path).close())


def check_existing(path):
    path = validate_writable_location(path)
    if not path.is_file():
        raise ValueError("This story file is missing. Choose an existing database.")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        if connection.execute("PRAGMA user_version").fetchone()[0] < 1:
            raise ValueError("This is not a versioned Story Atlas database.")
    finally:
        connection.close()
    return path


class Welcome(tk.Tk):
    def __init__(self, root_folder, settings, legacy_path=None):
        super().__init__()
        self.root_folder, self.settings, self.legacy_path = root_folder, settings, legacy_path
        if not settings.path.exists():
            settings.save(mode='Simple')
        self.result = None
        self.title("Welcome to Story Atlas")
        self.geometry("660x450")
        self.minsize(500, 350)
        apply_theme(self, settings.values["theme"], settings.values["text_size"])
        if resource("story-atlas.ico").exists():
            self.iconbitmap(str(resource("story-atlas.ico")))
        scroller = ScrollFrame(self)
        scroller.pack(fill="both", expand=True, padx=24, pady=16)
        body = scroller.content
        ttk.Label(body, text="Your next story starts here", style="Title.TLabel").pack(anchor="w")
        wrapping_label(body, text="Keep characters, relationships, and story events together. Everything stays in local story files.").pack(fill="x", pady=14)
        for label, action, text in (("Start empty", self.start_empty, "Name your story, first chapter, and opening event."),
                                    ("Open story", self.open_story, "Continue an existing Story Atlas database."),
                                    ("Try Greyhaven", self.try_sample, "18 characters, five character types, colored links, 3 chapters and 10 events."),
                                    ("Try the modern prometheus", lambda: self.try_sample('prometheus'), "Explore Mary Shelley's Frankenstein through characters, events, and changing relationships. Contains the full story, including its ending.")):
            ttk.Button(body, text=label, command=action, style="Accent.TButton").pack(anchor="w", pady=(8, 2))
            wrapping_label(body, text=text, style="Muted.TLabel").pack(fill="x")
        hint = f"Data folder: {root_folder}"
        if legacy_path and legacy_path.is_file():
            hint += f"\nEarlier local story found: {legacy_path}. Choose Open story to continue it; it has not been moved."
        elif settings.values.get("last_story"):
            hint += "\nYour last story is unavailable. Locate it with Open story; no replacement was created."
        wrapping_label(body, text=hint, style="Muted.TLabel").pack(fill="x", pady=14)

    def finish(self, operation):
        try:
            self.result = operation()
        except (ValueError, OSError, sqlite3.Error) as error:
            messagebox.showerror("Cannot open story", str(error), parent=self)
            return
        self.destroy()

    def start_empty(self):
        from .story_setup import StorySetup
        return StorySetup(self, self.root_folder / 'stories', lambda path: self.finish(lambda: path))

    def open_story(self):
        initial = self.legacy_path.parent if self.legacy_path and self.legacy_path.is_file() else self.root_folder / "stories"
        path = filedialog.askopenfilename(parent=self, title="Open story", initialdir=initial,
                                         filetypes=[("Story Atlas", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")])
        if path:
            self.finish(lambda: check_existing(path))

    def try_sample(self, example='greyhaven'):
        self.finish(lambda: new_sample(self.root_folder, example))
