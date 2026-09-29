"""One application version and a verifiable source/package identity."""
import hashlib
import json
from pathlib import Path
import sys

from .migrations import CURRENT_VERSION

APPLICATION_VERSION = "0.19.0"


def source_fingerprint(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    files = [root / "main.py", *sorted((root / "story_atlas").glob("*.py"))]
    files.extend(sorted(path for path in (root / 'story_atlas/resources/ui').rglob('*') if path.is_file()))
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_identity():
    if getattr(sys, "frozen", False):
        manifest = Path(__file__).with_name("build_metadata.json")
        try:
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            if metadata["version"] == APPLICATION_VERSION and metadata["schema"] == CURRENT_VERSION:
                return "Packaged", metadata["fingerprint"]
        except (OSError, KeyError, ValueError):
            pass
        return "Packaged", "unknown (manifest unavailable)"
    return "Source", source_fingerprint()


def about_text(database):
    mode, fingerprint = build_identity()
    active = database.connection.execute("PRAGMA user_version").fetchone()[0]
    return (f"Story Atlas {APPLICATION_VERSION}\n"
            f"Runtime: {mode}\n"
            f"Build identity: {fingerprint}\n"
            f"Supported database schema: {CURRENT_VERSION}\n"
            f"Active database schema: {active}\n"
            f"Active story: {database.path}")
