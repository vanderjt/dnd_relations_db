"""Separate installed program resources from upgrade-safe writable user data."""
import os
from pathlib import Path
import sys


def data_root(override=None):
    value = override or os.environ.get("STORY_ATLAS_HOME")
    if value:
        return Path(value).expanduser().resolve()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "StoryAtlas"
    base = os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else Path.home() / ".local" / "share") / "StoryAtlas"


def resource(name):
    return Path(__file__).resolve().parent / "resources" / name


def validate_writable_location(path):
    """Never let an installed build keep a story inside its replaceable folder."""
    path = Path(path).expanduser().resolve()
    if getattr(sys, "frozen", False):
        directories = [Path(sys.executable).resolve().parent]
        if hasattr(sys, "_MEIPASS"):
            directories.append(Path(sys._MEIPASS).resolve())
        if any(path.is_relative_to(folder) for folder in directories):
            raise ValueError("Choose a data location outside the Story Atlas application folder so upgrades preserve your story.")
    return path


def prepare_data(override=None):
    root = validate_writable_location(data_root(override))
    (root / "stories").mkdir(parents=True, exist_ok=True)
    cache = root / "cache" / "matplotlib"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(cache)
    return root
