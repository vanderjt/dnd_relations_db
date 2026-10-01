export const FIELDS = {
  name: 'Name', species: 'Race / species', role: 'Class / role', age: 'Age',
  status: 'Status', location: 'Location', faction: 'Affiliation',
  health: 'Health', armor: 'Armor', mana: 'Mana', inventory: 'Inventory',
  summary: 'Character in a sentence', goals: 'Motivation', traits: 'Personality',
  skills: 'Skills', backstory: 'Lore / story', notes: 'Author’s notes',
};

// An event-only record overlays one point; it never changes the continuing value.
// Explicit later records always win, even when an earlier event is edited later.
export function resolveField(base, records, character, field, event) {
  const relevant = records.filter(r => r.character === character && r.field === field && r.event <= event);
  const exact = relevant.find(r => r.event === event);
  if (exact) return {value: exact.value, source: exact};
  const continuing = relevant.filter(r => r.persist).sort((a, b) => b.event - a.event)[0];
  return {value: continuing ? continuing.value : String(base[field] ?? ''), source: continuing || null};
}

export function resolveProfile(base, records, event) {
  return Object.fromEntries(Object.keys(FIELDS).map(field => [field, resolveField(base, records, base.id, field, event).value]));
}

export function changesBetween(saved, draft) {
  return Object.keys(FIELDS).filter(field => draft[field] !== saved[field]).map(field => ({
    field, before: saved[field], after: draft[field],
  }));
}

export function commitChanges(records, character, event, changes, carry) {
  const replaced = new Set(changes.map(c => c.field));
  return [
    ...records.filter(r => !(r.character === character && r.event === event && replaced.has(r.field))),
    ...changes.map(c => ({character, event, field: c.field, value: c.after, persist: carry.has(c.field)})),
  ];
}

export function validRecords(value, characters, eventCount) {
  if (!Array.isArray(value)) return [];
  const ids = new Set(characters.map(c => c.id));
  const unique = new Map();
  for (const r of value) {
    if (r && ids.has(r.character) && Number.isInteger(r.event) && r.event >= 1 && r.event <= eventCount &&
        Object.hasOwn(FIELDS, r.field) && typeof r.value === 'string' && typeof r.persist === 'boolean') {
      unique.set([r.character, r.event, r.field].join(':'), r);
    }
  }
  return [...unique.values()];
}
