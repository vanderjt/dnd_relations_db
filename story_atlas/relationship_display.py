"""Read-only arrow labels; stored semantics and editing choices stay unchanged."""
from .relationship_semantics import mutual, type_label

LEGEND = "Arrows: → outgoing · ← incoming · ↔ mutual"


def centered_connection(row, character_id=None):
    """Keep the chosen character on the left without reversing semantic roles."""
    incoming = character_id == row['target_id'] and not mutual(row)
    left, right = ('target', 'source') if character_id == row['target_id'] else ('source', 'target')
    arrow = '↔' if mutual(row) else '←' if incoming else '→'
    return (f"{row[left + '_name']} (#{row[left + '_id']}) {arrow} "
            f"{row[right + '_name']} (#{row[right + '_id']})")


def relationship_list_label(row, character_id=None):
    """Return a compact, character-relative row without changing stored direction.

    The full connection remains available in :func:`relationship_details`.
    All-relationships views retain both endpoints, while a cast-scoped view
    already names its selected character in the heading and only needs the
    other character, an explicit arrow, and an ID for duplicate-name safety.
    """
    if character_id is None or character_id not in (row["source_id"], row["target_id"]):
        return centered_connection(row)
    incoming = character_id == row["target_id"] and not mutual(row)
    other = "source" if character_id == row["target_id"] else "target"
    arrow = "↔" if mutual(row) else "←" if incoming else "→"
    return f"{arrow} {row[other + '_name']} (#{row[other + '_id']})"


def relationship_list_type(row, character_id=None):
    """Put the selected character's inverse role first when one is explicit."""
    inverse = row.get("inverse_label", "")
    if character_id == row.get("target_id") and inverse and not mutual(row):
        return f"{inverse} / {row['kind']}"
    return type_label(row)


def relationship_details(row, character_id=None):
    text = f"{centered_connection(row, character_id)}: {type_label(row)}"
    if row.get('inverse_label'):
        text += (f"\n{row['source_name']}'s role: {row['kind']}; "
                 f"{row['target_name']}'s role: {row['inverse_label']}.")
    return text
