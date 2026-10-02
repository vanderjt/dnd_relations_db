import React, { useEffect, useRef, useState } from "react";
type Data = Record<string, any>;
type Point = { x: number; y: number };
export function relationshipLabel(r: Data, id: number) {
  return r.semantics === "mutual" || r.source_id === id
    ? r.kind
    : r.inverse_label || `Incoming ${r.kind}`;
}
export function Graph({
  workspace,
  selected,
  onSelect,
  onProfile,
  onEdit,
  onAdd,
  onLayout,
}: {
  workspace: Data;
  selected: number;
  onSelect: (id: number) => void;
  onProfile: () => void;
  onEdit: (r: Data) => void;
  onAdd: () => void;
  onLayout: (layout: Data) => void;
}) {
  const [direct, setDirect] = useState(false),
    [positions, setPositions] = useState<Record<string, Point>>(
      workspace.graph,
    ),
    [view, setView] = useState({ x: 0, y: 0, k: 1 }),
    [baseScale, setBaseScale] = useState(1);
  const svg = useRef<SVGSVGElement>(null),
    viewRef = useRef(view),
    drag = useRef<any>(null);
  viewRef.current = view;
  const cast = [...workspace.characters].sort((a:Data,b:Data)=>a.name.localeCompare(b.name)),
    links = workspace.connections;
  const points: Record<string, Point> = {};
  cast.forEach((c: Data, i: number) => {
    const angle = (i / Math.max(1, cast.length)) * Math.PI * 2 - Math.PI / 2;
    points[c.id] = positions[c.id] || {
      x: 450 + Math.cos(angle) * 285,
      y: 340 + Math.sin(angle) * 245,
    };
  });
  const near = links.filter(
    (r: Data) => r.source_id === selected || r.target_id === selected,
  );
  const neighbors = new Set([
    selected,
    ...near.flatMap((r: Data) => [r.source_id, r.target_id]),
  ]);
  const shown = direct ? cast.filter((c: Data) => neighbors.has(c.id)) : cast;
  const shownIds = new Set(shown.map((c: Data) => c.id));
  const edges = links.filter(
    (r: Data) => shownIds.has(r.source_id) && shownIds.has(r.target_id),
  );
  const person = cast.find((c: Data) => c.id === selected);
  const name = (id: number) =>
    cast.find((c: Data) => c.id === id)?.name || "Unknown";
  function local(e: { clientX: number; clientY: number }) {
    const matrix = svg.current!.getScreenCTM()!.inverse();
    return new DOMPoint(e.clientX, e.clientY).matrixTransform(matrix);
  }
  useEffect(() => {
    const el = svg.current!;
    const observer = new ResizeObserver(() => {
      const rect = el.getBoundingClientRect();
      setBaseScale(
        Math.max(0.1, Math.min(rect.width / 900, rect.height / 680)),
      );
    });
    observer.observe(el);
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const p = local(e),
        v = viewRef.current,
        k = Math.min(4, Math.max(0.25, v.k * Math.exp(-e.deltaY * 0.0015)));
      setView({
        k,
        x: p.x - ((p.x - v.x) * k) / v.k,
        y: p.y - ((p.y - v.y) * k) / v.k,
      });
    };
    el.addEventListener("wheel", wheel, { passive: false });
    return () => {
      observer.disconnect();
      el.removeEventListener("wheel", wheel);
    };
  }, []);
  function fit() {
    if (!shown.length) return;
    const ps = shown.map((c: Data) => points[c.id]),
      minX = Math.min(...ps.map((p: Point) => p.x)) - 90,
      maxX = Math.max(...ps.map((p: Point) => p.x)) + 90,
      minY = Math.min(...ps.map((p: Point) => p.y)) - 70,
      maxY = Math.max(...ps.map((p: Point) => p.y)) + 70,
      k = Math.min(900 / (maxX - minX), 680 / (maxY - minY), 2);
    setView({
      k,
      x: 450 - ((minX + maxX) / 2) * k,
      y: 340 - ((minY + maxY) / 2) * k,
    });
  }
  function begin(e: React.PointerEvent, id?: number) {
    if ((e.target as Element).closest("[data-edge]")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const p = local(e);
    drag.current = {
      id,
      start: p,
      point: id ? points[id] : null,
      view,
      positions: { ...points },
      moved: false,
    };
  }
  function move(e: React.PointerEvent) {
    const d = drag.current;
    if (!d) return;
    const p = local(e),
      dx = p.x - d.start.x,
      dy = p.y - d.start.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
    if (d.id)
      setPositions({
        ...d.positions,
        [d.id]: { x: d.point.x + dx / view.k, y: d.point.y + dy / view.k },
      });
    else setView({ ...d.view, x: d.view.x + dx, y: d.view.y + dy });
  }
  function end() {
    const d = drag.current;
    drag.current = null;
    if (!d) return;
    if (d.id && d.moved) onLayout({ ...points });
    else if (d.id) onSelect(d.id);
  }
  return (
    <div className="relationships-view">
      <section className="graph-panel">
        <div className="graph-title">
          <div>
            <h1>Relationships</h1>
            <p>Explore the cast during {" "}
              {
                workspace.events.find((e: Data) => e.id === workspace.event_id)
                  ?.title
              }
            </p>
          </div>
          <div className="graph-selection">
          <label className="graph-character-label">Selected character
          <select
            aria-label="Graph character"
            value={selected}
            onChange={(e) => onSelect(Number(e.target.value))}
          >
            {cast.map((c: Data) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          </label>
          <div className="scope-control">
            <span>Full cast</span>
            <button id="graph-scope-toggle" role="switch" aria-label="Direct connections" aria-checked={direct} onClick={() => setDirect(!direct)}><span /></button>
            <span>Direct connections</span>
          </div>
          </div>
        </div>
        <div className="graph-canvas">
          <div className="graph-tools">
            <button aria-label="Zoom to fit" title="Zoom to fit" onClick={fit}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 8h8v8H8z" /></svg>
            </button>
            <button
              aria-label="Reset layout"
              title="Reset layout"
              onClick={() => {
                setPositions({});
                setView({ x: 0, y: 0, k: 1 });
                onLayout({});
              }}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 11 9-8 9 8M5 10v11h5v-7h4v7h5V10" /></svg>
            </button>
          </div>
          <svg
            ref={svg}
            viewBox="0 0 900 680"
            aria-label="Relationship graph"
            onPointerDown={(e) => begin(e)}
            onPointerMove={move}
            onPointerUp={end}
            onPointerCancel={end}
            style={{ touchAction: "none" }}
          >
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto"
              >
                <path d="M0 0 L10 5 L0 10z" fill="var(--muted)" />
              </marker>
            </defs>
            <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
              {edges.map((r: Data) => {
                const a = points[r.source_id],
                  b = points[r.target_id],
                  dx = b.x - a.x,
                  dy = b.y - a.y,
                  len = Math.hypot(dx, dy) || 1;
                const parallel = edges.filter(
                  (x: Data) =>
                    new Set([x.source_id, x.target_id]).has(r.source_id) &&
                    new Set([x.source_id, x.target_id]).has(r.target_id),
                );
                const offset =
                  (parallel.findIndex((x: Data) => x.id === r.id) -
                    (parallel.length - 1) / 2) *
                  38;
                const d = `M${a.x + ((dx / len) * 23) / Math.sqrt(baseScale)},${a.y + ((dy / len) * 23) / Math.sqrt(baseScale)} Q${(a.x + b.x) / 2 - (dy / len) * offset},${(a.y + b.y) / 2 + (dx / len) * offset} ${b.x - ((dx / len) * 26) / Math.sqrt(baseScale)},${b.y - ((dy / len) * 26) / Math.sqrt(baseScale)}`;
                return (
                  <g
                    key={r.id}
                    data-edge="true"
                    className="graph-edge"
                    role="button"
                    tabIndex={0}
                    aria-label={`Edit ${name(r.source_id)} ${r.kind} ${name(r.target_id)}`}
                    onClick={() => onEdit(r)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") onEdit(r);
                    }}
                  >
                    <title>
                      {name(r.source_id)}{" "}
                      {r.semantics === "mutual" ? "↔" : "→"}{" "}
                      {name(r.target_id)}: {r.kind}
                    </title>
                    <path
                      d={d}
                      fill="none"
                      stroke="transparent"
                      strokeWidth="16"
                    />
                    <path
                      d={d}
                      fill="none"
                      stroke="var(--muted)"
                      strokeWidth="1.5"
                      markerEnd={
                        r.semantics === "directional"
                          ? "url(#arrow)"
                          : undefined
                      }
                    />
                  </g>
                );
              })}
              {shown.map((c: Data) => (
                <g
                  className={
                    "graph-node " + (selected === c.id ? "selected" : "")
                  }
                  key={c.id}
                  transform={`translate(${points[c.id].x} ${points[c.id].y})`}
                  role="button"
                  tabIndex={0}
                  aria-label={`Select ${c.name}`}
                  onPointerDown={(e) => {
                    e.stopPropagation();
                    svg.current?.setPointerCapture(e.pointerId);
                    begin(e, c.id);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(c.id);
                    }
                    if (
                      [
                        "ArrowLeft",
                        "ArrowRight",
                        "ArrowUp",
                        "ArrowDown",
                      ].includes(e.key)
                    ) {
                      e.preventDefault();
                      const next = {
                        ...points,
                        [c.id]: {
                          x:
                            points[c.id].x +
                            (e.key === "ArrowLeft"
                              ? -12
                              : e.key === "ArrowRight"
                                ? 12
                                : 0),
                          y:
                            points[c.id].y +
                            (e.key === "ArrowUp"
                              ? -12
                              : e.key === "ArrowDown"
                                ? 12
                                : 0),
                        },
                      };
                      setPositions(next);
                      onLayout(next);
                    }
                  }}
                >
                  <circle r={22 / Math.sqrt(baseScale)} />
                  <text
                    className="node-initials"
                    textAnchor="middle"
                    y={4 / Math.sqrt(baseScale)}
                    style={{ fontSize: 10 / Math.sqrt(baseScale) }}
                  >
                    {c.name
                      .split(/\s+/)
                      .slice(0, 2)
                      .map((x: string) => x[0])
                      .join("")}
                  </text>
                  <text
                    className="node-name"
                    textAnchor="middle"
                    y={37 / Math.sqrt(baseScale)}
                    style={{ fontSize: 10 / Math.sqrt(baseScale) }}
                  >
                    {c.name}
                  </text>
                </g>
              ))}
            </g>
          </svg>
        </div>
        <div className="graph-caption">
          {shown.length} characters · {edges.length} connections{" "}
          <span>
            Drag nodes to arrange. Drag the background to pan. Scroll to zoom.
          </span>
        </div>
      </section>
      <aside className="graph-inspector">
        <div className="graph-inspector-heading">
          <div className="inspector-identity">
            <div className="inspector-portrait" aria-label="Portrait placeholder">{person?.name?.split(/\s+/).slice(0,2).map((s:string)=>s[0]).join("")}</div>
            <div><h2>{person?.name || "Your cast"}</h2>
              <dl><dt>Age</dt><dd>{person?.age || "Not set"}</dd><dt>Race</dt><dd>{person?.species || "Not set"}</dd><dt>Role</dt><dd>{person?.role || "Not set"}</dd></dl>
            </div>
          </div>
          <p className="inspector-summary">{person?.summary}</p>
        </div>
        <p className="muted">{near.length} connections during {workspace.events.find((e:Data)=>e.id===workspace.event_id)?.title}</p>
        <div className="graph-connection-list">
          {near.map((r: Data) => (
            <article className="graph-connection" key={r.id}>
              <button
                className="graph-person"
                onClick={() =>
                  onSelect(r.source_id === selected ? r.target_id : r.source_id)
                }
              >
                {name(r.source_id === selected ? r.target_id : r.source_id)}
              </button>
              <button className="relationship-kind" onClick={() => onEdit(r)}>
                {relationshipLabel(r, selected)} ⌄
              </button>
              <p>{r.notes}</p>
            </article>
          ))}
        </div>
        <div className="graph-inspector-actions">
          <button className="secondary" disabled={!person} onClick={onProfile}>
            Open profile
          </button>
          <button
            className="secondary"
            disabled={cast.length < 2}
            onClick={onAdd}
          >
            Add connection
          </button>
        </div>
      </aside>
    </div>
  );
}
