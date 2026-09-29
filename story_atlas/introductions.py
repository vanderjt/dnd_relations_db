"""Stable introduction references and whole-chronology cast validation."""
from .history_model import resolve

NARRATIVE_ROLES = ('neutral', 'protagonist', 'antagonist')


def validate_introductions(characters, relationships, history, events):
    orders = {row['id']: row['sequence'] for row in events}
    cast = {row['id']: row for row in characters}
    for row in characters:
        intro = row.get('introduction_event_id')
        if intro is not None and (type(intro) is not int or intro not in orders):
            raise ValueError(f"{row['name']} has a missing introduction event. Reassign its introduction before removing the event.")
        if row.get('narrative_role', 'neutral') not in NARRATIVE_ROLES:
            raise ValueError('Narrative role must be neutral, protagonist, or antagonist.')
    for event in [None, *sorted(events, key=lambda row: row['sequence'])]:
        boundary = event['sequence'] if event else 0
        for connection in resolve(relationships, history, events, event['id'] if event else 0):
            for ident in (connection['source_id'], connection['target_id']):
                row = cast[ident]
                intro = row.get('introduction_event_id')
                if intro is not None and orders[intro] > boundary:
                    when = event['title'] if event else 'Before first event'
                    raise ValueError(f"Connection #{connection['id']} is active at {when}, before {row['name']} (#{ident}) is introduced. "
                                     'Choose a later relationship event, explicitly reassign the character introduction, or cancel this chronology change.')


def visible_cast(database, event_id, planned=False):
    orders = {row['id']: row['sequence'] for row in database.events.list()}
    boundary = float('inf') if event_id is None else orders.get(event_id, 0)
    result = []
    for row in database.characters():
        future = orders.get(row.get('introduction_event_id'), 0) > boundary
        if not future or planned:
            result.append(dict(row, planned=future))
    return result
