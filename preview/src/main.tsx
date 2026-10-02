import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./preview.css";
import { Graph, relationshipLabel } from "./Graph";
import { World, worldLabels } from "./World";

type Data = Record<string, any>;
type Reply = {
  ok: boolean;
  data: any;
  revision: number;
  error?: { code: string; message: string };
};
declare global {
  interface Window {
    pywebview?: {
      api: { command: (name: string, args?: Data) => Promise<Reply> };
    };
    previewReady?: boolean;
  }
}
const labels: Record<string, string> = {
  name: "Name",
  species: "Race / species",
  role: "Role",
  age: "Age",
  status: "Status",
  location: "Location",
  faction: "Faction",
  summary: "Short summary",
  health: "Health",
  armor: "Armor",
  mana: "Mana",
  inventory: "Inventory",
  skills: "Skills & abilities",
  goals: "Goals",
  traits: "Personality traits",
  backstory: "Backstory",
  notes: "Author’s notes",
  language: "Language",
  belief: "Religion / belief",
  title: "Title / rank",
  purpose: "Purpose",
};
const themes = ["storybook", "gothic", "cyberpunk", "noir", "medieval"];
type Editor = {
  draft_id: string;
  command: string;
  key: string;
  payload: Data;
  original: Data;
  revision: number;
  scopes: Record<string, string>;
  sources?: Data;
};
const same = (a: any, b: any) => JSON.stringify(a) === JSON.stringify(b);
const initials = (s: string) =>
  s
    .split(/\s+/)
    .slice(0, 2)
    .map((x) => x[0])
    .join("");
async function api(name: string, args: Data = {}): Promise<Reply> {
  if (!window.pywebview)
    throw new Error(
      "The native bridge is unavailable. Launch Story Atlas Preview.cmd.",
    );
  const result = await window.pywebview.api.command(name, args);
  if (!result.ok)
    throw new Error(result.error?.message || "The operation failed.");
  return result;
}
function Modal({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog ref={ref} onCancel={(e) => e.preventDefault()} aria-label={title}>
      <div className="dialog-header">
        <h2>{title}</h2>
      </div>
      {children}
    </dialog>
  );
}
function App() {
  const [workspace, setWorkspace] = useState<Data | null>(null),
    [page, setPage] = useState("characters"),
    [eventId, setEventId] = useState(0),
    [character, setCharacter] = useState(0);
  const [editor, setEditor] = useState<Editor | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [draftState, setDraftState] = useState("");
  const [review, setReview] = useState(false),
    [closeRequested, setCloseRequested] = useState(false),
    [collapsedChapters, setCollapsedChapters] = useState<number[]>([]),
    [leave, setLeave] = useState(false),
    [create, setCreate] = useState(""),
    [recovery, setRecovery] = useState(false),
    [search, setSearch] = useState(""),
    [participantSearch, setParticipantSearch] = useState(""),
    [theme, setTheme] = useState("storybook");
  const editRef = useRef(editor),
    pending = useRef<null | (() => Promise<void>)>(null),
    queue = useRef(Promise.resolve()),
    draftFailure = useRef<Error | null>(null),
    busyRef = useRef(false),
    closeIntent = useRef(false),
    origin = useRef<{ page: string; event: number; character: number } | null>(
      null,
    ),
    retry = useRef<{ signature: string; id: string } | null>(null);
  editRef.current = editor;
  const dirty = !!editor && !same(editor.payload, editor.original);
  const selectedEvent = workspace?.events.find((x: Data) => x.id === eventId);
  const selectedCharacter = workspace?.characters.find(
    (x: Data) => x.id === character,
  );
  async function run(action: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  function persist(e: Editor) {
    setDraftState("Keeping draft…");
    queue.current = queue.current
      .catch(() => {})
      .then(async () => {
        try {
          if (same(e.payload, e.original))
            await api("discard_draft", { key: e.key });
          else
            await api("save_draft", {
              key: e.key,
              payload: { version: 1, editor: e },
            });
          draftFailure.current = null;
          setDraftState(
            same(e.payload, e.original) ? "" : "Draft kept on disk",
          );
        } catch (reason) {
          draftFailure.current = reason as Error;
          setDraftState("Draft not yet on disk");
          setError((reason as Error).message);
        }
      });
  }
  async function flush() {
    await queue.current;
    if (draftFailure.current) throw draftFailure.current;
  }
  function updateMany(values: Data) {
    const e = editRef.current;
    if (!e) return;
    const next = { ...e, payload: { ...e.payload, ...values } };
    editRef.current = next;
    setEditor(next);
    persist(next);
  }
  function update(field: string, value: any) {
    const e = editRef.current;
    if (!e) return;
    const next = { ...e, payload: { ...e.payload, [field]: value } };
    editRef.current = next;
    setEditor(next);
    persist(next);
    setNotice("");
  }
  function scope(field: string, value: boolean) {
    const e = editRef.current!;
    const next = {
      ...e,
      scopes: { ...e.scopes, [field]: value ? "carry_forward" : "event_only" },
    };
    editRef.current = next;
    setEditor(next);
    persist(next);
  }
  async function loadEditor(
    command: string,
    payload: Data,
    revision: number,
    sources?: Data,
  ) {
    const key =
      command === "save_profile"
        ? `profile:${payload.character_id}:${payload.event_id}`
        : command === "save_connection"
          ? `connection:${payload.id ?? "new"}:${payload.event_id}`
          : `${command}:${payload.id ?? "new"}`;
    const stored = (await api("get_draft", { key })).data;
    const fresh: Editor = {
      draft_id: crypto.randomUUID(),
      command,
      key,
      payload,
      original: structuredClone(payload),
      revision,
      scopes: {},
      sources,
    };
    const e = stored?.version === 1 ? stored.editor : fresh;
    if (stored) {
      setNotice(
        "Recovered pending edits. Review before saving or discard them.",
      );
    }
    editRef.current = e;
    setEditor(e);
    setDraftState(stored ? "Draft kept on disk" : "");
  }
  async function show(w: Data, pg = page, ev = w.event_id, id = character) {
    setWorkspace(w);
    setPage(pg);
    setEventId(ev);
    if (themes.includes(w.theme)) {
      setTheme(w.theme);
      document.documentElement.dataset.theme = w.theme;
      (document.getElementById("theme-stylesheet") as HTMLLinkElement).href =
        `themes/${w.theme}.css`;
    }
    id = w.characters.some((x: Data) => x.id === id)
      ? id
      : w.characters[0]?.id || 0;
    setCharacter(id);
    setCreate("");
    setReview(false);
    if (pg === "characters" && id) {
      const result = await api("profile", { character_id: id, event_id: ev });
      await loadEditor(
        "save_profile",
        { character_id: id, event_id: ev, ...result.data.raw_values },
        result.data.revision,
        result.data.sources,
      );
    } else if (pg === "story") {
      const e = w.events.find((x: Data) => x.id === ev);
      await loadEditor(
        "save_event",
        {
          ...e,
          participants: w.participants
            .filter((x: Data) => x.event_id === ev)
            .map((x: Data) => x.character_id),
        },
        w.revision,
      );
    } else {
      editRef.current = null;
      setEditor(null);
    }
    await api("preference", {
      key: "context",
      payload: { page: pg, event_id: ev, character_id: id },
    });
  }
  async function refresh(pg = page, ev = eventId, id = character) {
    const r = await api("workspace", { event_id: ev });
    await show(r.data, pg, ev, id);
  }
  async function discard() {
    await flush();
    if (editRef.current)
      await api("discard_draft", { key: editRef.current.key });
    setEditor(null);
    editRef.current = null;
    setDraftState("");
  }
  function navigate(action: () => Promise<void>) {
    if (busyRef.current) return;
    const e = editRef.current;
    if (e && !same(e.payload, e.original)) {
      pending.current = action;
      setLeave(true);
    } else
      void run(async () => {
        await flush();
        await action();
      });
  }
  async function finishNavigation() {
    const action = pending.current;
    pending.current = null;
    setLeave(false);
    if (action) await action();
  }
  async function closePreview() {
    await flush();
    if (workspace) {
      const scrolls: Data = {};
      for (const selector of [".sheet-scroll", ".story-detail", ".story-outline", ".cast-list", ".graph-connection-list"])
        scrolls[selector] = document.querySelector(selector)?.scrollTop || 0;
      await api("preference", {key:"context", payload:{page,event_id:eventId,character_id:character,
        resume:{scrolls,create,editorKey:editRef.current?.key || null,
          collapsedChapters,worldDetails:!!document.querySelector<HTMLDetailsElement>(".profile-world-details")?.open}}});
    }
    await api("close");
  }
  async function save() {
    const e = editRef.current;
    if (!e) return;
    await flush();
    let payload = e.payload;
    if (e.command === "save_profile") {
      payload = {
        character_id: e.payload.character_id,
        event_id: e.payload.event_id,
        changes: Object.keys(labels)
          .filter((k) => e.payload[k] !== e.original[k])
          .map((field) => ({
            field,
            value: e.payload[field],
            scope: e.scopes[field] || "event_only",
          })),
      };
    }
    const request = {
      command: e.command,
      payload,
      expected_revision: e.revision,
      draft_key: e.key,
      draft_id: e.draft_id,
    };
    const signature = JSON.stringify(request);
    if (retry.current?.signature !== signature)
      retry.current = { signature, id: crypto.randomUUID() };
    const result = await api("write", {
      ...request,
      request_id: retry.current!.id,
    });
    retry.current = null;
    setNotice("Saved to this story.");
    setReview(false);
    setCreate("");
    setDraftState("");
    editRef.current = null;
    setEditor(null);
    if (pending.current) {
      await finishNavigation();
      return;
    }
    const ev = e.command === "save_event" ? result.data.id : eventId;
    const id =
      e.command === "create_character" ? result.data.character_id : character;
    await refresh(
      e.command === "create_character" ? "characters" : page,
      ev,
      id,
    );
  }
  async function editConnection(row?: Data) {
    setCreate("connection");
    const payload = row
      ? {
          id: row.id,
          source_id: row.source_id,
          target_id: row.target_id,
          kind: row.kind,
          notes: row.notes,
          semantics: row.semantics,
          inverse_label: row.inverse_label,
          category: row.category || "",
          event_id: eventId,
          scope: "event_only",
        }
      : {
          source_id: character,
          target_id: workspace!.characters.find((c: Data) => c.id !== character)
            ?.id,
          kind: "Friend",
          notes: "",
          semantics: "mutual",
          inverse_label: "",
          category: "Support",
          event_id: eventId,
          scope: "event_only",
        };
    await loadEditor("save_connection", payload, workspace!.revision);
  }
  async function editWorld(entry: Data) {
    setCreate("world");
    await loadEditor("save_world", entry, workspace!.revision);
  }
  function display(value: any) {
    if (typeof value === "string" && value.startsWith("@world:"))
      return (
        workspace?.world.find((r: Data) => `@world:${r.id}` === value)?.name ||
        "Missing World entry"
      );
    return value;
  }
  async function startCreate(kind: string, chapterId?: number) {
    setCreate(kind);
    const rev = workspace!.revision;
    if (kind === "character")
      await loadEditor(
        "create_character",
        { name: "", summary: "", event_id: eventId },
        rev,
      );
    if (kind === "chapter")
      await loadEditor("save_chapter", { title: "", summary: "" }, rev);
    if (kind === "event")
      await loadEditor(
        "save_event",
        {
          chapter_id: chapterId ?? selectedEvent.chapter_id,
          title: "",
          summary: "",
          status: "Planned",
          purpose: "",
          notes: "",
          participants: [],
        },
        rev,
      );
    if (kind === "title")
      await loadEditor("save_title", { title: workspace!.title }, rev);
  }
  async function openStory(kind: string, title = "") {
    const r = await api(
      kind === "sample" ? "new_story" : kind,
      kind === "sample" ? { sample: true } : { title },
    );
    if (r.data) {
      const w = r.data;
      await show(
        w,
        w.context?.page || "story",
        w.event_id,
        w.context?.character_id || 0,
      );
      setNotice("Story opened.");
    }
  }
  useEffect(() => {
    const start = () => {
      window.previewReady = true;
      void run(async () => {
        const r = await api("bootstrap");
        if (r.data) {
          await show(
            r.data,
            r.data.context?.page || "story",
            r.data.event_id,
            r.data.context?.character_id || 0,
          );
          const resume = r.data.context?.resume;
          if (resume) {
            if (resume.editorKey && resume.create) {
              const stored = (await api("get_draft", {key:resume.editorKey})).data;
              if (stored?.version===1) {editRef.current=stored.editor;setEditor(stored.editor);setCreate(resume.create);setDraftState("Draft kept on disk");}
            }
            setCollapsedChapters(resume.collapsedChapters || []);
            requestAnimationFrame(()=>requestAnimationFrame(()=>{
              for (const [selector,top] of Object.entries(resume.scrolls || {})) {
                const element=document.querySelector(selector);if(element) element.scrollTop=Number(top);
              }
              const details=document.querySelector<HTMLDetailsElement>(".profile-world-details");if(details) details.open=!!resume.worldDetails;
            }));
          }
        }
      });
    };
    if (window.pywebview) start();
    else window.addEventListener("pywebviewready", start, { once: true });
    return () => window.removeEventListener("pywebviewready", start);
  }, []);
  useEffect(() => {
    const handler = () => {
      setCloseRequested(true);
    };
    window.addEventListener("preview-close", handler);
    return () => window.removeEventListener("preview-close", handler);
  });
  useEffect(()=>{
    if (!closeRequested || busy) return;
    setCloseRequested(false);
    closeIntent.current=true;
    navigate(closePreview);
  },[closeRequested,busy]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        if (dirty && !busy) {
          if (
            editor?.command === "save_profile" ||
            editor?.command === "save_connection"
          )
            setReview(true);
          else void run(save);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });
  function applyTheme(value: string) {
    setTheme(value);
    document.documentElement.dataset.theme = value;
    (document.getElementById("theme-stylesheet") as HTMLLinkElement).href =
      `themes/${value}.css`;
    if (workspace)
      void api("preference", { key: "theme", payload: value }).catch((e) =>
        setError(e.message),
      );
  }
  function field(key: string, area = false, label = labels[key] || key) {
    const value = editor?.payload[key] ?? "";
    const changed = editor && value !== editor.original[key];
    const source = editor?.sources?.[key];
    return (
      <label className={"field " + (changed ? "dirty" : "")} key={key}>
        <span className="field-label">
          {label}
          {changed && <small> · Pending</small>}
        </span>
        {editor?.command === "save_profile" && key in worldLabels ? (
          <select
            aria-label={label}
            value={value}
            onChange={(e) => update(key, e.target.value)}
          >
            <option value="">Not set</option>
            {workspace?.world
              .filter((r: Data) => r.category === key)
              .map((r: Data) => (
                <option key={r.id} value={`@world:${r.id}`}>
                  {r.name}
                </option>
              ))}
          </select>
        ) : area ? (
          <textarea
            rows={key === "summary" ? 3 : 4}
            aria-label={label}
            value={value}
            onChange={(e) => update(key, e.target.value)}
          />
        ) : (
          <input
            aria-label={label}
            value={value}
            onChange={(e) => update(key, e.target.value)}
          />
        )}
        <span className="field-source">
          {source
            ? `${source.scope === "event_only" ? "This event only" : "Carries forward"} · ${workspace?.events.find((e: Data) => e.id === source.event_id)?.title}`
            : ""}
        </span>
      </label>
    );
  }
  const banner = (
    <>
      {error && (
        <div className="error-banner" role="alert">
          {error}
          <button
            onClick={() =>
              void run(async () => {
                if (editRef.current) persist(editRef.current);
                await flush();
                setError("");
              })
            }
          >
            Retry draft
          </button>
          {workspace && (
            <button
              onClick={() =>
                void run(async () => {
                  await flush();
                  const w = (await api("workspace", { event_id: eventId }))
                    .data;
                  setWorkspace(w);
                  if (editRef.current) {
                    let e = { ...editRef.current, revision: w.revision };
                    if (e.command === "save_profile") {
                      const r = await api("profile", {
                        character_id: e.payload.character_id,
                        event_id: e.payload.event_id,
                      });
                      const original = {
                        character_id: e.payload.character_id,
                        event_id: e.payload.event_id,
                        ...r.data.raw_values,
                      };
                      const changed = Object.keys(labels).filter(
                        (k) => e.payload[k] !== e.original[k],
                      );
                      e = {
                        ...e,
                        original,
                        payload: {
                          ...original,
                          ...Object.fromEntries(
                            changed.map((k) => [k, e.payload[k]]),
                          ),
                        },
                        sources: r.data.sources,
                      };
                    }
                    editRef.current = e;
                    setEditor(e);
                    persist(e);
                  }
                  setNotice(
                    "Current revision loaded. Pending values remain; review them before saving.",
                  );
                })
              }
            >
              Reload saved values
            </button>
          )}
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
    </>
  );
  return (
    <>
      <fieldset className="app-lock" disabled={busy}>
        <div
          className={
            "app preview-app " +
            (page !== "characters" ? "story-page" : "") +
            (!workspace ? " welcome-app" : "")
          }
          data-page={page}
        >
          <header className="masthead">
            <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
              <span className="brand-mark">
                S<span>A</span>
              </span>
              <span>
                Story Atlas<small>THE CHARACTER STUDIO</small>
              </span>
            </a>
            <button
              className="book-title quiet"
              disabled={!workspace}
              onClick={() => navigate(() => startCreate("title"))}
            >
              {workspace?.title || "Your next story"}
            </button>
            {workspace && <span className="edition">A STORY IN {workspace.chapters.length} CHAPTERS</span>}
            <nav className="page-nav" aria-label="Workspace">
              {["world", "story", "characters", "relationships"].map((pg) => (
                <button
                  key={pg}
                  disabled={!workspace}
                  aria-current={page === pg ? "page" : "false"}
                  onClick={() =>
                    navigate(async () => {
                      if (pg === "relationships" && page !== "relationships")
                        origin.current = { page, event: eventId, character };
                      else origin.current = null;
                      await refresh(pg);
                    })
                  }
                >
                  {pg[0].toUpperCase() + pg.slice(1)}
                </button>
              ))}
            </nav>
            <label className="theme-picker">
              Theme
              <select
                aria-label="Theme"
                value={theme}
                onChange={(e) => applyTheme(e.target.value)}
              >
                {themes.map((x) => (
                  <option key={x} value={x}>
                    {x[0].toUpperCase() + x.slice(1)}
                  </option>
                ))}
              </select>
            </label>
            <details className="file-menu">
              <summary>Story file</summary>
              <div>
                <button
                  onClick={() =>
                    navigate(async () => {
                      setWorkspace(null);
                      setEditor(null);
                      editRef.current = null;
                    })
                  }
                >
                  New / open…
                </button>
                <button
                  disabled={!workspace}
                  onClick={() =>
                    void run(async () => {
                      await flush();
                      const r = await api("backup");
                      setNotice(`Backup created: ${r.data.path}`);
                    })
                  }
                >
                  Back up story
                </button>
                <button
                  onClick={() => navigate(() => openStory("restore"))}
                >
                  Restore backup as a copy…
                </button>
                <button
                  disabled={!workspace}
                  onClick={() =>
                    navigate(async () => {
                      await refresh();
                      setRecovery(true);
                    })
                  }
                >
                  Recover pending edits
                </button>
                {workspace&&<p className="current-story-path">{workspace.path}</p>}
              </div>
            </details>
          </header>
          {!workspace ? (
            <main className="welcome">
              <span className="eyebrow">A PLACE FOR YOUR STORY</span>
              <h1>Begin a new chapter.</h1>
              <p>
                Characters, events, and their changing lives. Saved locally in a
                separate preview story.
              </p>
              {banner}
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const title = new FormData(e.currentTarget).get(
                    "title",
                  ) as string;
                  void run(() => openStory("new_story", title));
                }}
              >
                <label className="field">
                  Story title
                  <input name="title" required autoComplete="off" />
                </label>
                <button className="primary">Create story</button>
              </form>
              <div className="welcome-actions">
                <button
                  className="secondary"
                  onClick={() =>
                    void run(async () => {
                      const r = await api("bootstrap");
                      if (r.data)
                        await show(
                          r.data,
                          r.data.context?.page || "story",
                          r.data.event_id,
                          r.data.context?.character_id || 0,
                        );
                    })
                  }
                >
                  Reopen last story
                </button>
                <button
                  className="secondary"
                  onClick={() => void run(() => openStory("open_story"))}
                >
                  Open preview story…
                </button>
                <button
                  className="secondary"
                  onClick={() => void run(() => openStory("sample"))}
                >
                  Try Greyhaven sample
                </button>
              </div>
              <p className="muted">
                Existing Tkinter stories and browser prototype edits stay
                separate. Legacy import is not available in this preview.
              </p>
            </main>
          ) : (
            <>
              {page === "characters" && (
                <aside className="sidebar" aria-label="Cast">
                  <div className="sidebar-heading">
                    <span className="eyebrow">YOUR STORY’S PEOPLE</span>
                    <div>
                      <h1>The cast</h1>
                      <span className="count">
                        {workspace.characters.length}
                      </span>
                    </div>
                  </div>
                  <label className="search">
                    <input
                      aria-label="Search cast"
                      placeholder="Find a character…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                  <button
                    className="new-character-button"
                    onClick={() => navigate(() => startCreate("character"))}
                  >
                    + New character
                  </button>
                  <div className="cast-caption"><span>CHARACTER</span><span>{workspace.characters.length} CHARACTERS</span></div>
                  <nav className="cast-list">
                    {workspace.characters
                      .filter((c: Data) =>
                        [c.name, c.role, c.faction]
                          .join(" ")
                          .toLowerCase()
                          .includes(search.toLowerCase()),
                      )
                      .sort((a:Data,b:Data)=>a.name.localeCompare(b.name))
                      .map((c: Data) => (
                        <button
                          className="cast-row"
                          key={c.id}
                          aria-current={character === c.id}
                          onClick={() =>
                            navigate(() => refresh("characters", eventId, c.id))
                          }
                        >
                          <span className="avatar">{initials(c.name)}</span>
                          <span>
                            <strong className="cast-name">{c.name}</strong>
                            <small className="cast-role">
                              {c.role}
                            </small>
                          </span>
                          <span className="cast-arrow" aria-hidden="true">↗</span>
                        </button>
                      ))}
                  </nav>
                  <div className="sidebar-foot">
                    <span className="live-dot"/><span>A place to develop every character.<small>Saved on this computer</small></span>
                  </div>
                </aside>
              )}
              <main className="workspace">
                <div className="workspace-toolbar">
                  <div>
                    {origin.current && (
                      <button
                        className="secondary"
                        onClick={() =>
                          navigate(async () => {
                            const previous = origin.current!;
                            origin.current = null;
                            await refresh(
                              previous.page,
                              previous.event,
                              previous.character,
                            );
                          })
                        }
                      >
                        ← Back to{" "}
                        {origin.current.page === "story"
                          ? "event"
                          : origin.current.page}
                      </button>
                    )}
                    <div className="eyebrow">
                      {page.toUpperCase()} WORKSPACE
                    </div>
                    <button
                      className="context-button"
                      onClick={() => navigate(() => refresh("story"))}
                    >
                      {workspace.chapters.find((c:Data)=>c.id===selectedEvent?.chapter_id)?.title} · {selectedEvent?.title} ↗
                    </button>
                  </div>
                  {(page === "characters" || page === "story") && (
                    <div className="save-actions">
                      <span role="status">
                        {busy
                          ? "Working…"
                          : dirty
                            ? draftState
                            : "All changes saved"}
                      </span>
                      {dirty && (
                        <button
                          className="secondary"
                          onClick={() =>
                            void run(async () => {
                              await discard();
                              await refresh();
                            })
                          }
                        >
                          Discard edits
                        </button>
                      )}
                      <button
                        className="primary"
                        disabled={!dirty || !!create}
                        onClick={() =>
                          editor?.command === "save_profile"
                            ? setReview(true)
                            : void run(save)
                        }
                      >
                        {page === "characters"
                          ? "Review changes"
                          : "Save event"}
                      </button>
                    </div>
                  )}
                </div>
                {banner}
                {page === "world" ? (
                  <div className="sheet-scroll">
                    <World
                      workspace={workspace}
                      onEdit={(e) => navigate(() => editWorld(e))}
                    />
                  </div>
                ) : page === "relationships" ? (
                  <div className="preview-graph">
                    <Graph
                      workspace={{ ...workspace, event_id: eventId }}
                      selected={character}
                      onSelect={(id) => {
                        setCharacter(id);
                        void api("preference", {
                          key: "context",
                          payload: {
                            page,
                            event_id: eventId,
                            character_id: id,
                          },
                        }).catch((e) => setError(e.message));
                      }}
                      onProfile={() =>
                        navigate(async () => {
                          origin.current = {
                            page: "relationships",
                            event: eventId,
                            character,
                          };
                          await refresh("characters");
                        })
                      }
                      onEdit={(r) => navigate(() => editConnection(r))}
                      onAdd={() => navigate(() => editConnection())}
                      onLayout={(layout) =>
                        void run(async () => {
                          await api("preference", {
                            key: "graph",
                            payload: layout,
                          });
                          setWorkspace({ ...workspace, graph: layout });
                        })
                      }
                    />
                  </div>
                ) : page === "characters" ? (
                  <div className="sheet-scroll">
                    <div className="sheet">
                      {editor?.command === "save_profile" && !create ? (
                        <>
                          <div className="sheet-eyebrow">
                            <span>THE CAST / {selectedCharacter?.name}</span>
                            <span>Click a field to edit</span>
                          </div>
                          <section className="hero">
                            <div className="portrait">
                              <span className="portrait-initials">
                                {initials(selectedCharacter?.name || "")}
                              </span>
                              <small className="portrait-caption">
                                PORTRAIT TO COME
                              </small>
                            </div>
                            <div className="identity">
                              <div className="identity-top">
                                <span className="eyebrow">
                                  A PERSON IN YOUR STORY
                                </span>
                              </div>
                              {field("name")}
                              <div className="identity-grid">
                                {["species", "role", "age"].map((k) =>
                                  field(k),
                                )}
                              </div>
                              <div className="identity-grid secondary-info">
                                {["status", "location", "faction"].map((k) =>
                                  field(k),
                                )}
                              </div>
                            </div>
                          </section>
                          <div className="summary-field">
                            {field("summary", true)}
                          </div>
                          <div className="panels">
                            <section className="card">
                              <div className="card-heading">
                                <h2>At this moment</h2>
                                <span>STATISTICS</span>
                              </div>
                              <div className="stat-grid">
                                {["health", "armor", "mana"].map((k) =>
                                  field(k),
                                )}
                              </div>
                            </section>
                            <section className="card">
                              <div className="card-heading">
                                <h2>What they carry</h2>
                              </div>
                              {field("inventory", true)}
                            </section>
                          </div>
                          <section className="section-block">
                            <div className="section-top">
                              <span className="section-number">01</span>
                              <h2>Skills & abilities</h2>
                            </div>
                            {field("skills", true)}
                          </section>
                          <section className="section-block">
                            <div className="section-top">
                              <span className="section-number">02</span>
                              <h2>Character details</h2>
                            </div>
                            <div className="story-grid">
                              {["goals", "traits", "backstory", "notes"].map(
                                (k) => (
                                  <div className="detail-card" key={k}>
                                    {field(k, true)}
                                  </div>
                                ),
                              )}
                            </div>
                          </section>
                          <details className="profile-world-details">
                            <summary>
                              World details{" "}
                              <small>Language · Belief · Title</small>
                            </summary>
                            <p className="muted">
                              Choose one entry from each shared World list. Add
                              or describe entries on the World page.
                            </p>
                            <div className="profile-world-grid">
                              {["language", "belief", "title"].map((k) =>
                                field(k),
                              )}
                            </div>
                          </details>
                          <section className="section-block">
                            <div className="section-top">
                              <span className="section-number">03</span>
                              <h2>Connections at this event</h2>
                            </div>
                            <div className="connections">
                              <table className="connections-table">
                                <tbody>
                                  {workspace.connections
                                    .filter(
                                      (r: Data) =>
                                        r.source_id === character ||
                                        r.target_id === character,
                                    )
                                    .map((r: Data) => (
                                      <tr key={r.id}>
                                        <td>
                                          {
                                            workspace.characters.find(
                                              (c: Data) =>
                                                c.id ===
                                                (r.source_id === character
                                                  ? r.target_id
                                                  : r.source_id),
                                            )?.name
                                          }
                                        </td>
                                        <td>
                                          <button
                                            className="relationship-kind"
                                            onClick={() =>
                                              navigate(() => editConnection(r))
                                            }
                                          >
                                            {relationshipLabel(r, character)} ⌄
                                          </button>
                                        </td>
                                        <td>{r.notes}</td>
                                      </tr>
                                    ))}
                                </tbody>
                              </table>
                              <button
                                className="secondary"
                                disabled={workspace.characters.length < 2}
                                onClick={() => navigate(() => editConnection())}
                              >
                                Add connection
                              </button>
                              <button
                                className="quiet"
                                onClick={() =>
                                  navigate(async () => {
                                    origin.current = {
                                      page,
                                      event: eventId,
                                      character,
                                    };
                                    await refresh("relationships");
                                  })
                                }
                              >
                                Explore relationships ↗
                              </button>
                            </div>
                          </section>
                          <p className="provenance">
                            Explore who they are at this moment in the story.
                          </p>
                          <div className="sheet-actions">
                            <span className="muted" role="status">{dirty ? draftState : "All changes saved"}</span>
                            <button
                              className="primary"
                              disabled={!dirty}
                              onClick={() => setReview(true)}
                            >
                              Review changes
                            </button>
                          </div>
                        </>
                      ) : (
                        <div className="empty-state">
                          <h2>Your cast starts here.</h2>
                          <p>
                            Create a character, then develop their profile
                            through the story.
                          </p>
                          <button
                            className="primary"
                            onClick={() =>
                              navigate(() => startCreate("character"))
                            }
                          >
                            New character
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="story-layout">
                    <aside className="story-outline">
                      <div className="story-outline-heading">
                        <h2>Outline</h2>
                      <button
                        className="secondary"
                        onClick={() => navigate(() => startCreate("chapter"))}
                      >
                        + Chapter
                      </button>
                      </div>
                      {workspace.chapters.map((ch: Data, chapterIndex: number) => (
                        <section key={ch.id} className="outline-chapter">
                          <div className="outline-chapter-heading">
                          <button className="chapter-collapse" aria-label={`Toggle ${ch.title}`} aria-expanded={!collapsedChapters.includes(ch.id)} onClick={()=>setCollapsedChapters(old=>old.includes(ch.id)?old.filter(id=>id!==ch.id):[...old,ch.id])}>{collapsedChapters.includes(ch.id)?"›":"⌄"}</button>
                          <button
                            className="chapter-heading"
                            onClick={() =>
                              navigate(async () => {
                                setCreate("chapter");
                                await loadEditor(
                                  "save_chapter",
                                  {
                                    id: ch.id,
                                    title: ch.title,
                                    summary: ch.summary,
                                  },
                                  workspace.revision,
                                );
                              })
                            }
                          >
                            <small>CHAPTER {chapterIndex+1}</small>{ch.title}
                          </button>
                          </div>
                          {!collapsedChapters.includes(ch.id) && <div>
                          {workspace.events
                            .filter((e: Data) => e.chapter_id === ch.id)
                            .map((e: Data) => (
                              <button
                                key={e.id}
                                className="outline-event"
                                aria-current={e.id === eventId}
                                onClick={() =>
                                  navigate(() => refresh("story", e.id))
                                }
                              >
                                <span>{e.title}</span>
                                <small>{e.status || "Unclassified"}</small>
                              </button>
                            ))}
                          <button className="story-add-event" onClick={()=>navigate(()=>startCreate("event",ch.id))}>+ Add event</button>
                          </div>}
                        </section>
                      ))}
                    </aside>
                    <div className="story-page-heading world-heading"><span className="eyebrow">THE SHAPE OF YOUR STORY</span><h1>Story of {workspace.title}</h1><p>Plan what happens. Follow the people it changes.</p></div>
                    <div className="story-detail">
                      {editor?.command === "save_event" && !create && (
                        <>
                          <span className="eyebrow">
                            Develop this event · {" "}
                            {
                              workspace.chapters.find(
                                (x: Data) => x.id === selectedEvent?.chapter_id,
                              )?.title
                            }
                          </span>
                          <h1>{selectedEvent?.title}</h1>
                          {field("title", false, "Event title")}
                          <label className="field">
                            Status
                            <select
                              aria-label="Event status"
                              value={editor.payload.status}
                              onChange={(e) => update("status", e.target.value)}
                            >
                              <option value="">Unclassified</option>
                              <option>Planned</option>
                              <option>Happened</option>
                            </select>
                          </label>
                          {field("purpose", true)}
                          {field("summary", true, "Summary")}
                          <label className="field">
                            Location
                            <select
                              aria-label="Event location"
                              value={editor.payload.location_id ?? ""}
                              onChange={(e) =>
                                update(
                                  "location_id",
                                  e.target.value
                                    ? Number(e.target.value)
                                    : null,
                                )
                              }
                            >
                              <option value="">Not set</option>
                              {workspace.world
                                .filter((r: Data) => r.category === "location")
                                .map((r: Data) => (
                                  <option key={r.id} value={r.id}>
                                    {r.name}
                                  </option>
                                ))}
                            </select>
                          </label>
                          <section className="participants">
                            <h2>Characters involved</h2>
                            {!editor.payload.participants.length && <p className="muted">No characters added yet.</p>}
                            <div className="participant-tags">
                              {editor.payload.participants.map((id: number) => (
                                <span className="participant-tag" key={id}>
                                  <button
                                    onClick={() =>
                                      navigate(async () => {
                                        origin.current = {
                                          page: "story",
                                          event: eventId,
                                          character,
                                        };
                                        await refresh(
                                          "characters",
                                          eventId,
                                          id,
                                        );
                                      })
                                    }
                                  >
                                    {
                                      workspace.characters.find(
                                        (c: Data) => c.id === id,
                                      )?.name
                                    }
                                  </button>
                                  <button
                                    aria-label={`Remove ${workspace.characters.find((c: Data) => c.id === id)?.name}`}
                                    onClick={() =>
                                      update(
                                        "participants",
                                        editor.payload.participants.filter(
                                          (x: number) => x !== id,
                                        ),
                                      )
                                    }
                                  >
                                    ×
                                  </button>
                                </span>
                              ))}
                            </div>
                            <input
                              aria-label="Find participants"
                              placeholder="Search the cast by name…"
                              value={participantSearch}
                              onChange={(e) =>
                                setParticipantSearch(e.target.value)
                              }
                            />
                            {participantSearch.trim() && <div className="participant-options">
                              {workspace.characters
                                .filter(
                                  (c: Data) =>
                                    !editor.payload.participants.includes(
                                      c.id,
                                    ) &&
                                    c.name
                                      .toLowerCase()
                                      .includes(
                                        participantSearch.toLowerCase(),
                                      ),
                                )
                                .map((c: Data) => (
                                  <button
                                    className="secondary"
                                    key={c.id}
                                    onClick={() => {
                                      update("participants", [
                                        ...editor.payload.participants,
                                        c.id,
                                      ]); setParticipantSearch("");
                                    }}
                                  >
                                    + {c.name}
                                  </button>
                                ))}
                            </div>}
                            <button className="quiet participant-relationships" onClick={()=>navigate(async()=>{origin.current={page:"story",event:eventId,character};await refresh("relationships");})}>View relationships at this event ↗</button>
                          </section>
                          {field("notes", true)}
                          <div className="story-form-actions">
                          <button className="secondary" disabled={!dirty} onClick={()=>void run(async()=>{await discard();await refresh();})}>Discard edits</button>
                          <button
                            className="primary"
                            disabled={!dirty}
                            onClick={() => void run(save)}
                          >
                            Save event
                          </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </main>
              {(page === "characters" || page === "relationships") && <footer className="timeline" aria-label="Story timeline">
                <div className="timeline-heading">
                  <span className="eyebrow">Story Time Line</span>
                  <div className="timeline-nav">
                    <button
                      className="square"
                      aria-label="Previous event"
                      disabled={workspace.events[0]?.id === eventId}
                      onClick={() =>
                        navigate(() =>
                          refresh(
                            page,
                            workspace.events[
                              workspace.events.findIndex(
                                (x: Data) => x.id === eventId,
                              ) - 1
                            ].id,
                          ),
                        )
                      }
                    >
                      ←
                    </button>
                    <span>
                      {workspace.events.findIndex(
                        (x: Data) => x.id === eventId,
                      ) + 1}{" "}
                      / {workspace.events.length}
                    </span>
                    <button
                      className="square"
                      aria-label="Next event"
                      disabled={workspace.events.at(-1)?.id === eventId}
                      onClick={() =>
                        navigate(() =>
                          refresh(
                            page,
                            workspace.events[
                              workspace.events.findIndex(
                                (x: Data) => x.id === eventId,
                              ) + 1
                            ].id,
                          ),
                        )
                      }
                    >
                      →
                    </button>
                  </div>
                </div>
                <div className="timeline-track">
                <div className="chapter-labels" style={{gridTemplateColumns:`repeat(${workspace.events.length},minmax(0,1fr))`}}>
                  {workspace.chapters.map((ch:Data,i:number)=>{const count=workspace.events.filter((e:Data)=>e.chapter_id===ch.id).length;return count?<span key={ch.id} style={{gridColumn:`span ${count}`}}>{i+1} · {ch.title}</span>:null;})}
                </div>
                <div className="timeline-events" style={{gridTemplateColumns:`repeat(${workspace.events.length},minmax(0,1fr))`}}>
                  {workspace.events.map((e: Data, i: number) => (
                    <button
                      key={e.id}
                      className="event-step"
                      aria-current={eventId === e.id ? "step" : "false"}
                      onClick={() => navigate(() => refresh(page, e.id))}
                    >
                      <span className="event-dot">{i + 1}</span>
                      <span className="event-name">{e.title}</span>
                    </button>
                  ))}
                </div>
                </div>
              </footer>}
            </>
          )}
        </div>
      </fieldset>
      {create && editor && (
        <Modal
          title={
            create === "title"
              ? "Story title"
              : `${editor.payload.id ? "Edit" : "New"} ${create}`
          }
        >
          <fieldset disabled={busy}>
            {error && banner}
            <div className="connection-form-fields">
              {create === "connection" ? (
                <>
                  <p>
                    At <strong>{selectedEvent?.title}</strong>
                  </p>
                  <div className="identity-grid">
                    {["source_id", "target_id"].map((key, i) => (
                      <label className="field" key={key}>
                        {i ? "To" : "From"}
                        <select
                          aria-label={
                            i ? "Connection target" : "Connection source"
                          }
                          value={editor.payload[key]}
                          onChange={(e) => update(key, Number(e.target.value))}
                        >
                          {workspace!.characters
                            .filter(
                              (c: Data) =>
                                !editor.payload.id ||
                                [
                                  editor.original.source_id,
                                  editor.original.target_id,
                                ].includes(c.id),
                            )
                            .map((c: Data) => (
                              <option key={c.id} value={c.id}>
                                {c.name} · #{c.id}
                              </option>
                            ))}
                        </select>
                      </label>
                    ))}
                  </div>
                  <label className="field">
                    Connection type
                    <select
                      aria-label="Connection type"
                      value={editor.payload.kind}
                      onChange={(e) => {
                        const kind = e.target.value;
                        const inverse: Record<string, string> = {
                          Mentor: "Student",
                          Employer: "Employee",
                          Distrusts: "Distrusted by",
                          "Hostile toward": "Target of hostility",
                        };
                        updateMany({
                          kind,
                          semantics: inverse[kind] ? "directional" : "mutual",
                          inverse_label: inverse[kind] || "",
                        });
                      }}
                    >
                      {Array.from(
                        new Set([
                          "Friend",
                          "Ally",
                          "Enemy",
                          "Rival",
                          "Mentor",
                          "Employer",
                          "Distrusts",
                          "Hostile toward",
                          editor.payload.kind,
                        ]),
                      ).map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </label>
                  <p className="scope-note">
                    {
                      workspace!.characters.find(
                        (c: Data) => c.id === editor.payload.source_id,
                      )?.name
                    }{" "}
                    {editor.payload.semantics === "mutual" ? "↔" : "→"}{" "}
                    {
                      workspace!.characters.find(
                        (c: Data) => c.id === editor.payload.target_id,
                      )?.name
                    }
                    : {editor.payload.kind}
                    {editor.payload.inverse_label
                      ? ` / ${editor.payload.inverse_label}`
                      : ""}
                  </p>
                  {field("notes", true, "Connection notes")}
                  <label className="carry-toggle">
                    <input
                      type="checkbox"
                      checked={editor.payload.scope === "carry_forward"}
                      onChange={(e) =>
                        update(
                          "scope",
                          e.target.checked ? "carry_forward" : "event_only",
                        )
                      }
                    />
                    Carry forward from this event
                  </label>
                  <p className="muted">
                    Unchecked applies only here. The previous continuing state
                    resumes at the next event. Later authored decisions remain
                    authoritative.
                  </p>
                </>
              ) : create === "world" ? (
                <>
                  {field("name", false, "Entry name")}
                  {field("description", true, "Description")}
                  <p className="muted">
                    {worldLabels[editor.payload.category]}. Renaming preserves
                    every assignment’s identity. Deletion is unavailable.
                  </p>
                </>
              ) : create === "character" ? (
                <>
                  {field("name")}
                  {field("summary", true)}
                </>
              ) : (
                <>
                  {field(
                    "title",
                    false,
                    `${create === "title" ? "Story" : create[0].toUpperCase() + create.slice(1)} title`,
                  )}
                  {create !== "title" && field("summary", true, "Summary")}
                  {create === "event" && (
                    <label className="field">
                      Chapter
                      <select
                        aria-label="Chapter"
                        value={editor.payload.chapter_id}
                        onChange={(e) =>
                          update("chapter_id", Number(e.target.value))
                        }
                      >
                        {workspace!.chapters.map((ch: Data) => (
                          <option key={ch.id} value={ch.id}>
                            {ch.title}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </>
              )}
              <p className="muted">{draftState}</p>
            </div>
            <div className="dialog-actions">
              <button
                className="secondary"
                onClick={() => navigate(() => refresh())}
              >
                Cancel
              </button>
              <button
                className="primary"
                onClick={() =>
                  create === "connection" ? setReview(true) : void run(save)
                }
              >
                {create === "connection"
                  ? "Review connection"
                  : `Save ${create}`}
              </button>
            </div>
          </fieldset>
        </Modal>
      )}
      {review && editor && (
        <Modal title="What continues from here?">
          <fieldset disabled={busy}>
            {error && banner}
            <p className="review-explainer">
              All listed changes will be saved at{" "}
              <strong>{selectedEvent?.title}</strong>. Checked changes also
              carry forward until a later explicit decision. Unchecked changes
              apply only at this event.
            </p>
            <div className="change-list">
              {editor.command === "save_connection" ? (
                <div className="change-row">
                  <div className="change-heading">
                    <strong>Connection</strong>
                    <label className="carry-toggle">
                      <input
                        type="checkbox"
                        checked={editor.payload.scope === "carry_forward"}
                        onChange={(e) =>
                          update(
                            "scope",
                            e.target.checked ? "carry_forward" : "event_only",
                          )
                        }
                      />
                      Carry forward
                    </label>
                  </div>
                  <div className="change-values">
                    <div>
                      <span>BEFORE</span>
                      <p>
                        {editor.payload.id
                          ? `${editor.original.kind}${editor.original.inverse_label ? ` / ${editor.original.inverse_label}` : ""} · ${editor.original.notes || "No notes"}`
                          : "No connection"}
                      </p>
                    </div>
                    <div>
                      <span>AFTER</span>
                      <p>
                        {
                          workspace!.characters.find(
                            (c: Data) => c.id === editor.payload.source_id,
                          )?.name
                        }{" "}
                        {editor.payload.semantics === "mutual" ? "↔" : "→"}{" "}
                        {
                          workspace!.characters.find(
                            (c: Data) => c.id === editor.payload.target_id,
                          )?.name
                        }
                        : {editor.payload.kind}
                        {editor.payload.inverse_label
                          ? ` / ${editor.payload.inverse_label}`
                          : ""}
                      </p>
                      <p>{editor.payload.notes || "No notes"}</p>
                    </div>
                  </div>
                </div>
              ) : (
                Object.keys(labels)
                  .filter((k) => editor.payload[k] !== editor.original[k])
                  .map((k) => (
                    <div className="change-row" key={k}>
                      <div className="change-heading">
                        <strong>{labels[k]}</strong>
                        <label className="carry-toggle">
                          <input
                            type="checkbox"
                            checked={editor.scopes[k] === "carry_forward"}
                            onChange={(e) => scope(k, e.target.checked)}
                          />
                          Carry forward
                        </label>
                      </div>
                      <div className="change-values">
                        <div>
                          <span>BEFORE</span>
                          <p>{display(editor.original[k]) || "Blank"}</p>
                        </div>
                        <div>
                          <span>AFTER</span>
                          <p>{display(editor.payload[k]) || "Clear field"}</p>
                        </div>
                      </div>
                    </div>
                  ))
              )}
            </div>
            <div className="dialog-actions">
              <button
                className="secondary"
                onClick={() => {
                  setReview(false);
                  pending.current = null;
                  closeIntent.current = false;
                }}
              >
                Back to editing
              </button>
              <button className="primary" onClick={() => void run(save)}>
                Save changes
              </button>
            </div>
          </fieldset>
        </Modal>
      )}
      {leave && (
        <Modal title="Keep these changes?">
          <fieldset disabled={busy}>
            <p className="scope-note">
              {closeIntent.current ? "Save your changes, or keep a draft and close. Your story will reopen where you left off." : "You have pending edits. Save them, discard them, or stay here."}
            </p>
            {error && <p role="alert">{error}</p>}
            <div className="dialog-actions">
              <button
                className="secondary"
                onClick={() => {
                  pending.current = null;
                  setLeave(false);
                  closeIntent.current = false;
                }}
              >
                Stay
              </button>
              <button
                className="secondary"
                onClick={() =>
                  void run(async () => {
                    await discard();
                    await finishNavigation();
                  })
                }
              >
                Discard edits
              </button>
              {closeIntent.current && (
                <button
                  className="secondary"
                  onClick={() =>
                    void run(async () => {
                      if (editRef.current) persist(editRef.current);
                      await flush();
                      await closePreview();
                    })
                  }
                >
                  Keep draft & close
                </button>
              )}
              <button
                className="primary"
                onClick={() => {
                  setLeave(false);
                  if (
                    editor?.command === "save_profile" ||
                    editor?.command === "save_connection"
                  )
                    setReview(true);
                  else void run(save);
                }}
              >
                Save
              </button>
            </div>
          </fieldset>
        </Modal>
      )}
      {recovery && (
        <Modal title="Pending edits">
          <p className="scope-note">
            Open a draft to review it. Nothing is saved automatically.
          </p>
          <div className="change-list">
            {workspace?.drafts.length ? (
              workspace.drafts.map((d: Data) => (
                <div className="change-row" key={d.key}>
                  <span>
                    {(() => {
                      const e = JSON.parse(d.payload).editor;
                      return e.command === "save_profile"
                        ? `${workspace.characters.find((c: Data) => c.id === e.payload.character_id)?.name || "Character"} · ${workspace.events.find((x: Data) => x.id === e.payload.event_id)?.title || "Event"}`
                        : e.command === "save_connection"
                          ? "Connection edits"
                          : e.command === "save_world"
                            ? `World entry: ${e.payload.name || "New entry"}`
                            : e.payload.title || e.payload.name || "New item";
                    })()}
                  </span>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        const saved = JSON.parse(d.payload).editor as Editor;
                        setRecovery(false);
                        if (saved.command === "save_profile")
                          await refresh(
                            "characters",
                            saved.payload.event_id,
                            saved.payload.character_id,
                          );
                        else if (
                          saved.command === "save_event" &&
                          saved.payload.id
                        )
                          await refresh("story", saved.payload.id);
                        else {
                          if (saved.command === "save_connection")
                            await refresh(
                              "relationships",
                              saved.payload.event_id,
                              saved.payload.source_id,
                            );
                          if (saved.command === "create_character")
                            await refresh("characters", saved.payload.event_id);
                          editRef.current = saved;
                          setEditor(saved);
                          setCreate(
                            saved.command === "create_character"
                              ? "character"
                              : saved.command === "save_chapter"
                                ? "chapter"
                                : saved.command === "save_title"
                                  ? "title"
                                  : saved.command === "save_connection"
                                    ? "connection"
                                    : saved.command === "save_world"
                                      ? "world"
                                      : "event",
                          );
                        }
                      })
                    }
                  >
                    Recover
                  </button>
                  <button
                    className="quiet"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await api("discard_draft", { key: d.key });
                        await refresh();
                      })
                    }
                  >
                    Discard
                  </button>
                </div>
              ))
            ) : (
              <p>No pending edits.</p>
            )}
          </div>
          <div className="dialog-actions">
            <button className="primary" onClick={() => setRecovery(false)}>
              Done
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
