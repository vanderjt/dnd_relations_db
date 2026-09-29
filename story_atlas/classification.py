"""Explicit current labels; deliberately independent of narrative roles and links."""
CLASSIFICATIONS = ('NPC Enemy', 'Player Enemy', 'Neutral', 'NPC Ally', 'Player Ally')
COLORS = dict(zip(CLASSIFICATIONS, ('#d46b55', '#db9b45', '#9299a3', '#548fc7', '#48aaa5')))


def validate(value):
    if value not in CLASSIFICATIONS:
        raise ValueError('Choose a character classification from the five available labels.')
    return value
