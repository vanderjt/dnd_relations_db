"""Relationship meaning, canonical identity, validation, and readable perspectives."""


def mutual(row):
    return row.get("semantics", "directional") == "mutual"


def normalize(source, target, kind, notes="", semantics="directional", inverse_label="", category=""):
    if type(source) is not int or type(target) is not int or source < 1 or target < 1:
        raise ValueError("Choose two existing characters.")
    if source == target:
        raise ValueError("Choose two different characters.")
    if semantics not in ("directional", "mutual"):
        raise ValueError("Choose Directional or Mutual.")
    if not all(isinstance(value, str) for value in (kind, notes, inverse_label)) or not kind.strip():
        raise ValueError("Enter a relationship type and text labels/notes.")
    if category not in ('', 'Support', 'Conflict', 'Personal', 'Other'):
        raise ValueError("Choose Support, Conflict, Personal or Other as the link category.")
    if semantics == "mutual":
        if inverse_label.strip():
            raise ValueError("Mutual uses the same type for both characters. Clear the inverse label or choose Directional.")
        source, target = sorted((source, target))
    return dict(source_id=source, target_id=target, kind=kind.strip(), notes=notes,
                semantics=semantics, inverse_label=inverse_label.strip(), category=category)


def claims(row):
    """An inverse is another reading of this record, not a second stored link."""
    source, target, kind = row["source_id"], row["target_id"], row["kind"]
    result = {(source, target, kind)}
    inverse = kind if mutual(row) else row.get("inverse_label", "")
    if inverse:
        result.add((target, source, inverse))
    return result


def check_duplicate(candidate, rows, exclude=()):
    for row in rows:
        if row.get("id") not in exclude and claims(candidate) & claims(row):
            raise ValueError(f"That relationship already exists (#{row.get('id', '?')}); its type or inverse reading overlaps.")


def type_label(row):
    inverse = row.get("inverse_label", "")
    return row["kind"] + (f" / {inverse}" if inverse else "")


def connection_label(row):
    arrow = "↔" if mutual(row) else "→"
    return f"{row.get('source_name', row['source_id'])} {arrow} {row.get('target_name', row['target_id'])}: {type_label(row)}"


def perspectives(source, target, kind, semantics, inverse=""):
    if semantics == "mutual":
        return f"{source} ↔ {target}: {kind}.\n{source} and {target} share {kind}; both profiles show this one connection."
    if semantics != "directional":
        return "Choose Mutual or Directional to preview both perspectives."
    reverse = (f"{target}'s role toward {source}: {inverse} (the inverse of this same connection)." if inverse
               else f"{target} sees an incoming {kind} connection from {source}; no reciprocal relationship is implied.")
    return f"{source} → {target}: {kind}.\n{source}'s role toward {target}: {kind}.\n{reverse}"


def profile_connections(rows, character_id):
    """One display entry per record on either endpoint's profile."""
    result = {"Outgoing": [], "Incoming": [], "Mutual": []}
    for row in rows:
        if character_id not in (row["source_id"], row["target_id"]):
            continue
        source = row["source_id"] == character_id
        other = "target" if source else "source"
        group = "Mutual" if mutual(row) else "Outgoing" if source else "Incoming"
        label = row["kind"] if source or mutual(row) else (row.get("inverse_label") or f"Incoming {row['kind']}")
        result[group].append((row, row[f"{other}_id"], row[f"{other}_name"], label))
    return result
