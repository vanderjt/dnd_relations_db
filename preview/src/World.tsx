import React, { useState } from "react";
type Data = Record<string, any>;
const hints: Record<string,string> = {species:"The peoples who inhabit your world.",role:"Occupations and callings for your cast.",faction:"The groups that shape your story.",location:"Places where your story unfolds.",language:"The languages spoken across your world.",belief:"Faiths and beliefs that guide your cast.",title:"Honors, ranks, and positions."};
export const worldLabels: Record<string, string> = {
  species: "Races & species",
  role: "Roles",
  faction: "Factions",
  location: "Locations",
  language: "Languages",
  belief: "Religions & beliefs",
  title: "Titles & ranks",
};
export function World({
  workspace,
  onEdit,
}: {
  workspace: Data;
  onEdit: (entry: Data) => void;
}) {
  const [category, setCategory] = useState("species"),
    [search, setSearch] = useState("");
  const rows = workspace.world.filter(
    (r: Data) =>
      r.category === category &&
      `${r.name} ${r.description}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="world-view">
      <div className="world-heading">
        <span className="eyebrow">YOUR STORY’S FOUNDATIONS</span>
        <h1>World of {workspace.title}</h1>
        <p>Define it once. Bring it into every character’s story.</p>
      </div>
      <div className="world-library">
        <nav className="world-categories" aria-label="World reference lists">
          {Object.entries(worldLabels).map(([key, label]) => (
            <button
              key={key}
              aria-current={category === key}
              onClick={() => {
                setCategory(key);
                setSearch("");
              }}
            >
              <span>{label}</span>
              <span className="count">
                {workspace.world.filter((r: Data) => r.category === key).length}
              </span>
            </button>
          ))}
        </nav>
        <section className="world-list">
          <div className="world-list-heading">
            <div><h2>{worldLabels[category]}</h2><p>{hints[category]}</p></div>
            <button
              className="primary"
              onClick={() => onEdit({ category, name: "", description: "" })}
            >
              + Add entry
            </button>
          </div>
          <p className="world-assignment">
            Available in character profile dropdowns at every event.
          </p>
          <input
            aria-label="Search world entries"
            placeholder="Find an entry…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="world-entries">
            {rows.map((r: Data) => (
              <button
                className="world-entry"
                key={r.id}
                onClick={() => onEdit(r)}
              >
                <strong>{r.name}</strong>
                <span>{r.description || "Add a description…"}</span>
                <span>↗</span>
              </button>
            ))}
            {!rows.length && (
              <p className="world-empty">
                {search ? "No entries match your search." : "No entries yet. Add the first one to start this list."}
              </p>
            )}
          </div>
        </section>
      </div>
      <section className="world-reserved">
        <div className="world-map-placeholder">
          <span className="eyebrow">WORLD MAP · PLANNED</span>
          <h2>A place for every journey</h2>
          <p>Map editing is not available in this preview.</p>
        </div>
        <div className="world-writing-placeholder">
          {["World summary", "Lore", "Author’s notes"].map((x) => (
            <div key={x}>
              <h2>{x}</h2>
              <span className="muted">Reserved for a future step</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
