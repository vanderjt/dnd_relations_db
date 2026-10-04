"""Resolve character fields at an event from baseline and dated decisions."""

FIELDS = (
    'name', 'species', 'role', 'age', 'status', 'location', 'faction',
    'summary', 'health', 'armor', 'mana', 'inventory', 'skills', 'goals',
    'traits', 'backstory', 'notes', 'language', 'belief', 'title',
)

SCOPES = ('event_only', 'carry_forward')

def resolve_profile(baseline, changes, events, event_id):
    """Resolve exact overrides, then continuing decisions, then baseline.

    IDs identify moments; sequence determines order. Blank is an authored value.
    Changes passed here must belong to one character.
    """
    order = {event['id']: event['sequence'] for event in events}
    if event_id not in order:
        raise ValueError('Choose an existing event.')
    values = {key: str(baseline.get(key, '') or '') for key in FIELDS}
    sources = {key: None for key in FIELDS}
    for row in sorted(changes, key=lambda r: order[r['event_id']]):
        if row['field'] not in FIELDS or row['scope'] not in SCOPES:
            raise ValueError('Invalid stored profile decision.')
        if order[row['event_id']] > order[event_id]:
            continue
        if row['scope'] == 'carry_forward' or row['event_id'] == event_id:
            values[row['field']] = row['value']
            sources[row['field']] = {'event_id': row['event_id'], 'scope': row['scope']}
    return {'values': values, 'sources': sources}
