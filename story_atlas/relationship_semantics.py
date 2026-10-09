"""Validate and identify current Story Atlas relationships."""


def mutual(row):
    """Treat rows without semantics as directional relationships."""
    return row.get("semantics", "directional") == "mutual"


def normalize(
    source,
    target,
    kind,
    notes="",
    semantics="directional",
    inverse_label="",
    category="",
):
    """Validate a relationship and canonicalize the endpoints of mutual links."""
    if type(source) is not int or type(target) is not int or source < 1 or target < 1:
        raise ValueError("Choose two existing characters.")
    if source == target:
        raise ValueError("Choose two different characters.")
    if semantics not in ("directional", "mutual"):
        raise ValueError("Choose Directional or Mutual.")
    if (
        not all(isinstance(value, str) for value in (kind, notes, inverse_label))
        or not kind.strip()
    ):
        raise ValueError("Enter a relationship type and text labels/notes.")
    if category not in ('', 'Support', 'Conflict', 'Personal', 'Other'):
        raise ValueError(
            "Choose Support, Conflict, Personal or Other as the link category."
        )
    if semantics == "mutual":
        if inverse_label.strip():
            raise ValueError(
                "Mutual uses the same type for both characters. Clear the inverse label or choose Directional."
            )
        source, target = sorted((source, target))
    return dict(
        source_id=source,
        target_id=target,
        kind=kind.strip(),
        notes=notes,
        semantics=semantics,
        inverse_label=inverse_label.strip(),
        category=category,
    )


def claims(row):
    """An inverse is another reading of this record, not a second stored link."""
    source, target, kind = row["source_id"], row["target_id"], row["kind"]
    result = {(source, target, kind)}
    inverse = kind if mutual(row) else row.get("inverse_label", "")
    if inverse:
        result.add((target, source, inverse))
    return result


def check_duplicate(candidate, rows, exclude=()):
    """Reject overlaps in either a forward label or an inverse reading."""
    for row in rows:
        if row.get("id") not in exclude and claims(candidate) & claims(row):
            raise ValueError(
                f"That relationship already exists (#{row.get('id', '?')}); its type or inverse reading overlaps."
            )
