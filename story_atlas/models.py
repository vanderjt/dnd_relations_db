"""Shared field definitions keep forms and storage consistent."""
PROFILE_FIELDS = {
    "name": "Name", "role": "Role / occupation", "species": "Species / ancestry",
    "location": "Location", "faction": "Faction", "status": "Status",
    "backstory": "Backstory", "traits": "Traits", "skills": "Skills",
    "inventory": "Inventory", "notes": "Other notes",
}
LEGACY_PROFILE_FIELDS = tuple(PROFILE_FIELDS)
PROFILE_FIELDS.update({"summary": "Short summary", "portrait": "Portrait", "tags": "Tags (comma separated)", "goals": "Goals"})
PROFILE_FIELDS["narrative_role"] = "Narrative role (not morality)"
LONG_FIELDS = ("summary", "backstory", "traits", "skills", "inventory", "notes", "goals")
RELATIONSHIP_TYPES = ("Ally", "Friend", "Family", "Romance", "Rival", "Enemy", "Mentor", "Other")

PROFILE_FIELDS["classification"] = "Character classification"

PROFILE_FIELDS["character_type"] = "Character type"
