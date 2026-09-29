"""One current character type; legacy pairs remain lossless during upgrades."""
from .classification import CLASSIFICATIONS, COLORS

CHARACTER_TYPES = ('Minor NPC', 'Protagonist', 'Antagonist', *CLASSIFICATIONS)
LEGACY_TYPES = tuple(f'{label} · {role}' for label in CLASSIFICATIONS if label != 'Neutral'
                     for role in ('Protagonist', 'Antagonist'))
TYPE_COLORS = {**COLORS, 'Minor NPC': '#8294a8', 'Protagonist': '#269b9b', 'Antagonist': '#ba70b2'}


def from_legacy(classification='Neutral', narrative_role='neutral'):
    if narrative_role == 'neutral':
        return classification
    role = narrative_role.title()
    return role if classification == 'Neutral' else f'{classification} · {role}'


def validate(value):
    if value not in (*CHARACTER_TYPES, *LEGACY_TYPES):
        raise ValueError('Choose a character type from the list.')
    return value


def legacy_values(value):
    validate(value)
    if ' · ' in value:
        classification, role = value.split(' · ')
        return classification, role.lower()
    if value in ('Protagonist', 'Antagonist'):
        return 'Neutral', value.lower()
    return ('Neutral' if value == 'Minor NPC' else value), 'neutral'


def resolve(values, previous=None):
    previous = dict(previous or {})
    classification = values.get('classification') or previous.get('classification', 'Neutral')
    role = values.get('narrative_role') or previous.get('narrative_role', 'neutral')
    value = values.get('character_type')
    if value and value != previous.get('character_type', 'Neutral'):
        return validate(value)
    if (classification, role) != (previous.get('classification', 'Neutral'), previous.get('narrative_role', 'neutral')):
        return validate(from_legacy(classification, role))
    return validate(value or previous.get('character_type') or from_legacy(classification, role))


def label(row):
    return row.get('character_type') or from_legacy(row.get('classification', 'Neutral'), row.get('narrative_role', 'neutral'))


def color(row):
    value = label(row)
    return TYPE_COLORS.get(value.split(' · ')[0], COLORS['Neutral'])
