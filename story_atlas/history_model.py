"""Pure timeline resolution: baseline followed by event-ordered full states."""
from .relationship_semantics import claims

STATE_FIELDS = ("source_id", "target_id", "kind", "notes", "semantics", "inverse_label", "category")


def resolve(relationships, history, events, event_id=None):
    order = {event["id"]: event["sequence"] for event in events}
    if event_id is not None and event_id != 0 and event_id not in order:
        raise ValueError("The selected story event no longer exists.")
    cutoff = float("inf") if event_id is None else 0 if event_id == 0 else order[event_id]
    states = {row["id"]: dict(row, active=row.get("baseline_active", 1)) for row in relationships}
    for change in sorted(history, key=lambda row: order[row["event_id"]]):
        ident = change["relationship_id"]
        if ident in states and order[change["event_id"]] <= cutoff:
            states[ident].update({key: change.get(key, "") if key == "category" else change[key] for key in (*STATE_FIELDS, "active")})
    return [row for row in states.values() if row.pop("active")]


def validate_timeline(relationships, history, events):
    for event_id in (0, *(event["id"] for event in events)):
        seen = set()
        for row in resolve(relationships, history, events, event_id):
            identities = claims(row)
            if seen & identities:
                where = "the undated starting state" if event_id == 0 else f"event #{event_id}"
                raise ValueError(f"Duplicate relationship perspectives at {where}. Correct the conflicting timeline first.")
            seen.update(identities)
