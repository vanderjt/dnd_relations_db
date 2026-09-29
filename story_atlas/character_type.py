"""The five current character types and compatibility with older story labels."""
from . import legacy_character_type as legacy

CHARACTER_TYPES = ('Player', 'Merchant', 'Allied NPC', 'Neutral NPC', 'Enemy NPC')
TYPE_COLORS = dict(zip(CHARACTER_TYPES, ('#48aaa5', '#db9b45', '#548fc7', '#9299a3', '#d46b55')))


def validate(value):
    if value in CHARACTER_TYPES:
        return value
    legacy.validate(value)
    base = value.split(' · ')[0]
    return {'Player Ally': 'Player', 'Player Enemy': 'Player',
            'NPC Ally': 'Allied NPC', 'NPC Enemy': 'Enemy NPC',
            'Protagonist': 'Player', 'Antagonist': 'Enemy NPC'}.get(base, 'Neutral NPC')


def from_legacy(classification='Neutral', narrative_role='neutral'):
    return validate(legacy.from_legacy(classification, narrative_role))


def legacy_values(value):
    if value not in CHARACTER_TYPES:
        return legacy.legacy_values(value)
    return {'Player': 'Player Ally', 'Merchant': 'Neutral', 'Allied NPC': 'NPC Ally',
            'Neutral NPC': 'Neutral', 'Enemy NPC': 'NPC Enemy'}[value], 'neutral'


def resolve(values, previous=None):
    previous = dict(previous or {})
    value = values.get('character_type')
    if value and value != previous.get('character_type'):
        return validate(value)
    classification = values.get('classification') or previous.get('classification', 'Neutral')
    role = values.get('narrative_role') or previous.get('narrative_role', 'neutral')
    if (classification, role) != (previous.get('classification', 'Neutral'), previous.get('narrative_role', 'neutral')):
        return from_legacy(classification, role)
    return validate(value or previous.get('character_type') or legacy.from_legacy(classification, role))


def label(row):
    return validate(row.get('character_type') or legacy.from_legacy(row.get('classification', 'Neutral'), row.get('narrative_role', 'neutral')))


def color(row):
    return TYPE_COLORS[label(row)]
