"""Validation of optional event/history tables in portable story exports."""
from .relationship_semantics import normalize
from .history_model import STATE_FIELDS, validate_timeline


def timeline_payload(payload, characters, relationships):
    chapters = payload.get('chapters', [])
    if not isinstance(chapters, list):
        raise ValueError('Invalid chapters records.')
    clean_chapters, chapter_ids, chapter_orders = [], set(), set()
    for row in chapters:
        if not isinstance(row, dict):
            raise ValueError('Invalid chapter record.')
        ident, order = row.get('id'), row.get('sequence')
        if (type(ident) is not int or not 0 < ident <= 9223372036854775807 or ident in chapter_ids
                or type(order) is not int or not 0 < order <= 1000000000 or order in chapter_orders
                or not isinstance(row.get('title'), str) or not row['title'].strip()
                or not isinstance(row.get('summary', ''), str)):
            raise ValueError('Invalid chapter title, ID or order.')
        chapter_ids.add(ident)
        chapter_orders.add(order)
        clean_chapters.append(dict(id=ident, title=row['title'], summary=row.get('summary', ''), sequence=order))
    tables = {}
    for name in ("story_events", "event_participants", "relationship_history"):
        rows = payload.get(name, [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Invalid {name} records.")
        tables[name] = rows
    events, event_ids, sequences = [], set(), set()
    for row in tables["story_events"]:
        ident, sequence = row.get("id"), row.get("sequence")
        if type(ident) is not int or not 0 < ident <= 9223372036854775807 or ident in event_ids:
            raise ValueError("Invalid or duplicate event ID.")
        if type(sequence) is not int or not 1 <= sequence <= 1000000000 or sequence in sequences:
            raise ValueError("Invalid or duplicate event sequence.")
        if not isinstance(row.get("title"), str) or not row["title"].strip() or not isinstance(row.get("summary", ""), str):
            raise ValueError("Events need a title and text summary.")
        event_ids.add(ident)
        sequences.add(sequence)
        chapter_id = row.get('chapter_id')
        if chapter_id is not None and (type(chapter_id) is not int or chapter_id not in chapter_ids):
            raise ValueError('Event references a missing chapter.')
        events.append(dict(id=ident, title=row["title"], summary=row.get("summary", ""), sequence=sequence, chapter_id=chapter_id))
    characters = {row["id"] for row in characters}
    participants, seen = [], set()
    for row in tables["event_participants"]:
        pair = row.get("event_id"), row.get("character_id")
        if any(type(value) is not int for value in pair) or pair[0] not in event_ids or pair[1] not in characters or pair in seen:
            raise ValueError("Invalid event participant reference or duplicate participant.")
        seen.add(pair)
        participants.append(dict(event_id=pair[0], character_id=pair[1]))
    history, seen_ids, seen_pairs = [], set(), set()
    bases = {row["id"]: row for row in relationships}
    for row in tables["relationship_history"]:
        ident, relationship_id, event_id = (row.get(key) for key in ("id", "relationship_id", "event_id"))
        if any(type(value) is not int for value in (ident, relationship_id, event_id)) or not 0 < ident <= 9223372036854775807 or ident in seen_ids:
            raise ValueError("Invalid relationship history ID.")
        if relationship_id not in bases or event_id not in event_ids or (relationship_id, event_id) in seen_pairs:
            raise ValueError("Invalid or duplicate relationship/event reference.")
        if type(row.get("active")) is not int or row["active"] not in (0, 1):
            raise ValueError("History active flag must be 0 or 1.")
        data = normalize(row.get("source_id"), row.get("target_id"), row.get("kind"), row.get("notes", ""),
                         row.get("semantics", "directional"), row.get("inverse_label", ""), row.get("category", ""))
        base = bases[relationship_id]
        if {data["source_id"], data["target_id"]} != {base["source_id"], base["target_id"]}:
            raise ValueError("History must keep the relationship's character pair.")
        seen_ids.add(ident)
        seen_pairs.add((relationship_id, event_id))
        history.append(dict(id=ident, relationship_id=relationship_id, event_id=event_id, active=row["active"], **data))
    validate_timeline(relationships, history, events)
    ranks = {row['id']: i for i, row in enumerate(sorted(clean_chapters, key=lambda row: row['sequence']))}
    ordering = [ranks.get(row['chapter_id'], len(ranks)) for row in sorted(events, key=lambda row: row['sequence'])]
    if ordering != sorted(ordering):
        raise ValueError('Event chronology must follow chapter order.')
    return dict(chapters=clean_chapters, story_events=events, event_participants=participants, relationship_history=history)
