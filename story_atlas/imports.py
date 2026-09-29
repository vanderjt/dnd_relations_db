"""Validate portable Story Atlas JSON, then import only into a new database."""
import json
from pathlib import Path

from .backup import publish_database
from .database import Database
from .models import PROFILE_FIELDS
from .assets import valid_reference
from .relationship_semantics import normalize, claims
from .history_imports import timeline_payload


def positive_id(value):
    return type(value) is int and 0 < value <= 9223372036854775807


def validate_payload(payload):
    if not isinstance(payload, dict) or type(payload.get("format_version")) is not int or payload["format_version"] not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        raise ValueError("Expected a Story Atlas format_version 1, 2, 3, 4, 5, 6, 7, 8 or 9 export.")
    result = {}
    for table in ("characters", "relationships", "activity"):
        rows = payload.get(table, [] if table == "activity" else None)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"{table} must be a list of records.")
        ids = [row.get("id") for row in rows]
        if any(not positive_id(ident) for ident in ids) or len(set(ids)) != len(ids):
            raise ValueError(f"{table} contains invalid or duplicate IDs.")
        result[table] = rows
    character_ids = {row["id"] for row in result["characters"]}
    clean_characters = []
    for row in result["characters"]:
        if any(not isinstance(row.get(field, ""), str) for field in PROFILE_FIELDS):
            raise ValueError("Character fields must contain text.")
        if not row.get("name", "").strip():
            raise ValueError("Every character needs a name.")
        if not valid_reference(row.get("portrait", "")):
            raise ValueError("Portrait references must be managed image filenames, not paths.")
        clean = {"id": row["id"], **{field: row.get(field, "") for field in PROFILE_FIELDS}}
        from .classification import validate
        clean['classification'] = validate(row.get('classification', 'Neutral'))
        clean['narrative_role'] = row.get('narrative_role') or 'neutral'
        from .character_type import from_legacy, validate as validate_type, legacy_values
        clean['character_type'] = validate_type(row.get('character_type') or from_legacy(clean['classification'], clean['narrative_role']))
        old_class, old_role = legacy_values(row.get('character_type') or clean['character_type'])
        supplied_class = clean['classification'] if 'classification' in row else old_class
        supplied_role = clean['narrative_role'] if 'narrative_role' in row else old_role
        mapped = from_legacy(supplied_class, supplied_role)
        if mapped != clean['character_type'] and not (clean['character_type'] == 'Merchant' and mapped == 'Neutral NPC'):
            raise ValueError('Character type conflicts with legacy character labels.')
        clean['classification'], clean['narrative_role'] = supplied_class, supplied_role
        from .legacy_character_type import validate as validate_legacy_type
        clean['legacy_character_type'] = validate_legacy_type(row.get('legacy_character_type', 'Neutral'))
        # Graph snapshots deliberately import as static undated stories; the
        # original temporal scope remains in the snapshot metadata.
        clean['introduction_event_id'] = None if payload.get('snapshot_kind') == 'graph' else row.get('introduction_event_id')
        clean_characters.append(clean)
    clean_relationships, seen = [], set()
    for row in result["relationships"]:
        source, target = row.get("source_id"), row.get("target_id")
        if not positive_id(source) or not positive_id(target) or source not in character_ids or target not in character_ids:
            raise ValueError("A relationship references a missing or invalid character.")
        kind, notes = row.get("kind"), row.get("notes", "")
        if source == target or not isinstance(kind, str) or not kind.strip() or not isinstance(notes, str):
            raise ValueError("A relationship has invalid endpoints, type, or notes.")
        data = normalize(source, target, kind, notes, row.get("semantics", "directional"), row.get("inverse_label", ""), row.get("category", ""))
        active = row.get("baseline_active", 1)
        if type(active) is not int or active not in (0, 1):
            raise ValueError("Relationship baseline_active must be 0 or 1.")
        data["baseline_active"] = active
        identities = claims(data) if active else set()
        if identities & seen:
            raise ValueError("Duplicate relationship types or inverse perspectives for the same character pair.")
        seen.update(identities)
        clean_relationships.append(dict(id=row["id"], **data))
    clean_activity = []
    for row in result["activity"]:
        if any(not isinstance(row.get(field), str) for field in ("timestamp", "action", "details")):
            raise ValueError("Activity records need timestamp, action, and details text.")
        clean_activity.append({field: row[field] for field in ("id", "timestamp", "action", "details")})
    timeline = timeline_payload(payload, clean_characters, clean_relationships)
    from .introductions import validate_introductions
    validate_introductions(clean_characters, clean_relationships, timeline['relationship_history'], timeline['story_events'])
    metadata = payload.get('story_metadata', [])
    if not isinstance(metadata, list) or any(not isinstance(row, dict) or row.get('key') != 'title' or not isinstance(row.get('value'), str) for row in metadata) or len(metadata) > 1:
        raise ValueError('Invalid story title metadata.')
    return dict(story_metadata=metadata, characters=clean_characters, relationships=clean_relationships, activity=clean_activity, **timeline)


def read_export(path):
    try:
        return validate_payload(json.loads(Path(path).read_text(encoding="utf-8-sig")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("The selected file is not valid UTF-8 JSON.") from error


def import_payload(payload, destination):
    # Validate again at the write boundary, even if a preview already succeeded.
    data = validate_payload({"format_version": 1, **payload})

    def populate(path):
        database = Database(path)
        try:
            with database.connection:
                for table, rows in data.items():
                    for row in rows:
                        fields = ",".join(row)
                        placeholders = ",".join("?" for _ in row)
                        database.connection.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", tuple(row.values()))
                if database.connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Imported relationships failed reference validation.")
        finally:
            database.close()

    return publish_database(destination, populate)
