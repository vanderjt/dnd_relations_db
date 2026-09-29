"""Consistent SQLite snapshots and restoration into a separate database."""
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import tempfile
from uuid import uuid4
from .paths import validate_writable_location


def backup_directory(path):
    path = Path(path)
    return path.parent / "backups" / path.name


def snapshot(connection, path, reason="manual", retention=7):
    directory = backup_directory(path)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = directory / f"{reason}-{stamp}-{uuid4().hex[:8]}.db"
    try:
        with sqlite3.connect(target) as destination:
            connection.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed.")
        destination.close()
    except Exception:
        if 'destination' in locals():
            destination.close()
        target.unlink(missing_ok=True)
        raise
    # Only automatic backups are pruned. Manual and migration backups are kept.
    if reason == "auto":
        for old in sorted(directory.glob("auto-*.db"), reverse=True)[max(1, retention):]:
            old.unlink()
    return target


def publish_database(destination, populate):
    """Build privately, then publish with an exclusive link (never overwrite)."""
    destination = validate_writable_location(destination)
    if destination.exists():
        raise ValueError("Choose a NEW database filename; existing files are never overwritten.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix=".story-atlas-", suffix=".db", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(filename)
    try:
        populate(temporary)
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def restore_backup(source, destination):
    """Validate and migrate a restored copy without altering its source."""
    from .database import Database

    def populate(temporary):
        original = sqlite3.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True)
        try:
            if original.execute("PRAGMA user_version").fetchone()[0] < 1:
                raise ValueError("This file is not a versioned Story Atlas backup.")
            if original.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("This backup failed its integrity check.")
            copy = sqlite3.connect(temporary)
            try:
                original.backup(copy)
            finally:
                copy.close()
        finally:
            original.close()
        restored = Database(temporary, migration_backup=False)
        try:
            if restored.connection.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("The backup contains invalid character references.")
        finally:
            restored.close()

    return publish_database(destination, populate)
