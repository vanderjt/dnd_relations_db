"""Resolve character fields at an event from baseline and dated decisions."""

FIELDS = (
    'name',
    'species',
    'role',
    'age',
    'status',
    'location',
    'faction',
    'summary',
    'health',
    'armor',
    'mana',
    'inventory',
    'skills',
    'goals',
    'traits',
    'backstory',
    'notes',
    'language',
    'belief',
    'title',
)

SCOPES = ('event_only', 'carry_forward')


def resolve_profile(baseline, changes, events, event_id):
    """Resolve exact overrides, then continuing decisions, then baseline.

    IDs identify moments; sequence determines order. Blank is an authored value.
    Changes passed here must belong to one character.
    """
    event_order = {event['id']: event['sequence'] for event in events}
    if event_id not in event_order:
        raise ValueError('Choose an existing event.')
    values = {key: str(baseline.get(key, '') or '') for key in FIELDS}
    sources = {key: None for key in FIELDS}
    for change in sorted(changes, key=lambda change: event_order[change['event_id']]):
        if change['field'] not in FIELDS or change['scope'] not in SCOPES:
            raise ValueError('Invalid stored profile decision.')
        if event_order[change['event_id']] > event_order[event_id]:
            continue
        if change['scope'] == 'carry_forward' or change['event_id'] == event_id:
            values[change['field']] = change['value']
            sources[change['field']] = {
                'event_id': change['event_id'],
                'scope': change['scope'],
            }
    return {'values': values, 'sources': sources}
