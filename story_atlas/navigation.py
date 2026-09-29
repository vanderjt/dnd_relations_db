"""Small, story-scoped Back stack for contextual profile navigation."""
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox


@dataclass(frozen=True)
class ProfileDestination:
    story: str
    character_id: int
    query: str
    filters: dict
    scroll: float
    profile_tab: str
    label: str


@dataclass(frozen=True)
class GraphDestination:
    story: str
    state: dict
    label: str = "Back to graph"


@dataclass(frozen=True)
class EventDestination:
    story: str
    state: dict
    label: str


class NavigationController:
    def __init__(self, app):
        self.app, self.stack = app, []

    def story_key(self):
        return str(Path(self.app.database.path).resolve())

    def clear(self):
        self.stack.clear()
        self.update_control()

    def update_control(self):
        destination = self.stack[-1] if self.stack else None
        self.app.back_button.configure(text=destination.label if destination else "Back", state="normal" if destination else "disabled")

    def profile_destination(self):
        view = self.app.characters
        row = next((row for row in self.app.database.characters() if row["id"] == view.character_id), None)
        if row is None:
            return None
        tab = "editor" if view.profile_tabs.select() == str(view.editor) else "overview"
        return ProfileDestination(self.story_key(), row["id"], view.search.get(), dict(view.roster.filters),
                                  view.overview.scroller.canvas.yview()[0], tab, f"Back to {row['name']}")

    def open_profile_link(self, character_id):
        origin = self.profile_destination()
        if origin is None:
            return False
        if not self.app.characters.open_character(character_id):
            return False
        self.stack.append(origin)
        self.app.tabs.select(self.app.characters)
        self.update_control()
        return True

    def open_from_graph(self, character_id):
        origin = GraphDestination(self.story_key(), self.app.graph.capture_state())
        if not self.app.characters.open_character(character_id):
            return False
        self.stack.append(origin)
        self.app.tabs.select(self.app.characters)
        self.update_control()
        return True

    def event_destination(self):
        view = self.app.events
        selected = view.tree.selection()
        row = view.rows.get(selected[0]) if selected else None
        return EventDestination(self.story_key(), view.capture_context(), f"Back to {row['title']}" if row else 'Back to events')

    def open_graph_from_event(self, event_id):
        self.stack.append(self.event_destination())
        graph = self.app.graph
        graph.as_of_id = event_id
        graph.dirty = True
        self.app.tabs.select(graph)
        graph.ensure_current()
        self.update_control()

    def open_goals_from_event(self, character_id):
        origin = self.event_destination()
        if not self.app.characters.open_character(character_id):
            return False
        self.stack.append(origin)
        self.app.tabs.select(self.app.characters)
        self.app.characters.edit_profile('goals')
        self.update_control()
        return True

    def back(self):
        if not self.stack:
            return False
        while self.stack:
            destination = self.stack[-1]
            if destination.story != self.story_key():
                self.stack.pop()
                continue
            if isinstance(destination, ProfileDestination):
                row = next((row for row in self.app.database.characters() if row["id"] == destination.character_id), None)
                if row is None:
                    self.stack.pop()
                    messagebox.showinfo("Character unavailable", "That character was deleted. Returned to the nearest available location.", parent=self.app)
                    continue
                view = self.app.characters
                if not view.open_character(destination.character_id):
                    return False
                view.roster.filters = dict(destination.filters)
                view.search.set(destination.query)
                view.profile_tabs.select(view.editor if destination.profile_tab == "editor" else view.overview)
                self.app.tabs.select(view)
                view.after_idle(lambda: view.overview.scroller.canvas.yview_moveto(destination.scroll))
            elif isinstance(destination, EventDestination):
                if not self.app.characters.can_leave(reset_discard=True):
                    return False
                self.app.tabs.select(self.app.events)
                self.app.events.restore_context(destination.state)
            else:
                if not self.app.characters.can_leave(reset_discard=True):
                    return False
                self.app.graph.apply_state(destination.state)
                self.app.tabs.select(self.app.graph)
            self.stack.pop()
            self.update_control()
            return True
        self.app.status.set("The previous location is no longer available.")
        self.update_control()
        return False
