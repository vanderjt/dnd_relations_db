"""Small, atomic JSON preferences stored beside the selected database."""
import json
from pathlib import Path

DEFAULTS = {"mode": "Advanced", "theme": "dark", "text_size": 10, "roster_width": 280, "relationship_roster_width": 260, "graph_inspector_width": 300, "backup_retention": 7, "recent_stories": [], "last_story": "", "dismissed_guidance": []}


class Settings:
    def __init__(self, path):
        self.path = Path(path)
        self.values = DEFAULTS.copy()
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                if saved.get("mode") in ("Simple", "Advanced"):
                    self.values["mode"] = saved["mode"]
                if isinstance(saved.get("last_story"), str) and "\0" not in saved["last_story"]:
                    self.values["last_story"] = saved["last_story"]
                dismissed = saved.get("dismissed_guidance", [])
                if isinstance(dismissed, list) and all(isinstance(value, str) for value in dismissed):
                    self.values["dismissed_guidance"] = dismissed
                recent = saved.get("recent_stories", [])
                if isinstance(recent, list) and all(isinstance(path, str) and path and "\0" not in path for path in recent):
                    self.values["recent_stories"] = recent[:12]
                if saved.get("theme") in ("dark", "light"):
                    self.values["theme"] = saved["theme"]
                for key, lower, upper in (("text_size", 9, 16), ("roster_width", 180, 1000), ("relationship_roster_width", 160, 1000), ("graph_inspector_width", 160, 1000), ("backup_retention", 1, 100)):
                    value = saved.get(key)
                    if type(value) is int and lower <= value <= upper:
                        self.values[key] = value
        except (OSError, ValueError):
            pass

    def save(self, **changes):
        values = {**self.values, **changes}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(values, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        self.values = values
