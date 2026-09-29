"""Optional vocabulary, combined without normalizing user spelling."""
STARTERS = {
    'role': ('Adventurer', 'Guard', 'Merchant', 'Healer', 'Scholar', 'Noble', 'Criminal', 'Artisan', 'Guide'),
    'species': ('Human', 'Elf', 'Dwarf', 'Halfling', 'Gnome', 'Orc', 'Goblin', 'Dragonborn', 'Tiefling'),
    'status': ('Alive', 'Dead', 'Missing', 'Unknown', 'Captured', 'Injured'),
    'tags': ('Main cast', 'Supporting cast', 'Quest giver', 'Contact', 'Witness', 'Suspect', 'Recurring', 'Secret keeper'),
}


def choices(database, field):
    from .retrieval import suggestions
    return tuple(dict.fromkeys((*STARTERS.get(field, ()), *suggestions(database, field))))
