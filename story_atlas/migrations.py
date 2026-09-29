"""Ordered migrations: backup first, then apply all pending steps atomically."""
from .models import LEGACY_PROFILE_FIELDS
from .backup import snapshot


class SchemaError(ValueError):
    """An unsupported or unrecognized database must not be modified."""


def initial_schema(connection):
    columns = ", ".join(f"{field} TEXT NOT NULL DEFAULT ''" for field in LEGACY_PROFILE_FIELDS)
    connection.execute(f"CREATE TABLE characters (id INTEGER PRIMARY KEY, {columns})")
    connection.execute("""CREATE TABLE relationships (
        id INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
        target_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
        kind TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
        CHECK(source_id != target_id), UNIQUE(source_id,target_id,kind))""")
    connection.execute("""CREATE TABLE activity (id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
        action TEXT NOT NULL, details TEXT NOT NULL)""")


def recovery_schema(connection):
    connection.execute("ALTER TABLE characters ADD COLUMN deleted_at TEXT")
    # Rebuild to allow recreating a trashed relationship without losing its history.
    connection.execute("ALTER TABLE relationships RENAME TO relationships_v1")
    connection.execute("""CREATE TABLE relationships (
        id INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL REFERENCES characters(id),
        target_id INTEGER NOT NULL REFERENCES characters(id),
        kind TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
        deleted_at TEXT, deletion_group TEXT, CHECK(source_id != target_id))""")
    connection.execute("""INSERT INTO relationships (id,source_id,target_id,kind,notes)
        SELECT id,source_id,target_id,kind,notes FROM relationships_v1""")
    connection.execute("DROP TABLE relationships_v1")
    connection.execute("""CREATE UNIQUE INDEX active_relationships
        ON relationships(source_id,target_id,kind) WHERE deleted_at IS NULL""")
    connection.execute("""CREATE TABLE drafts (key TEXT PRIMARY KEY, payload TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))""")


def profile_schema(connection):
    connection.execute("ALTER TABLE characters ADD COLUMN summary TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE characters ADD COLUMN portrait TEXT NOT NULL DEFAULT ''")
    # Image bytes live in SQLite too, making snapshots self-contained. The
    # managed assets folder contains reusable display copies of these bytes.
    connection.execute("CREATE TABLE portrait_assets (filename TEXT PRIMARY KEY, content BLOB NOT NULL)")


def graph_views_schema(connection):
    connection.execute("CREATE TABLE graph_views (name TEXT PRIMARY KEY, payload TEXT NOT NULL)")


def organization_schema(connection):
    connection.execute("ALTER TABLE characters ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
    connection.execute("CREATE TABLE saved_filters (name TEXT PRIMARY KEY, payload TEXT NOT NULL)")


def relationship_semantics_schema(connection):
    connection.execute("ALTER TABLE relationships ADD COLUMN semantics TEXT NOT NULL DEFAULT 'directional' CHECK(semantics IN ('directional','mutual'))")
    connection.execute("ALTER TABLE relationships ADD COLUMN inverse_label TEXT NOT NULL DEFAULT ''")
    # Enforce the same directed-label claims as relationship_semantics.claims,
    # including imports and Trash restoration that write SQL directly.
    for event in ("INSERT", "UPDATE"):
        connection.execute(f"""CREATE TRIGGER semantic_relationship_{event.lower()}
        BEFORE {event} ON relationships WHEN NEW.deleted_at IS NULL BEGIN
            SELECT RAISE(ABORT, 'Mutual relationships require canonical endpoints and no inverse label')
            WHERE NEW.semantics='mutual' AND (NEW.source_id>=NEW.target_id OR NEW.inverse_label!='');
            SELECT RAISE(ABORT, 'Duplicate relationship perspective') WHERE EXISTS (
                WITH incoming(a,b,label) AS (
                    SELECT NEW.source_id,NEW.target_id,NEW.kind UNION ALL
                    SELECT NEW.target_id,NEW.source_id,CASE WHEN NEW.semantics='mutual' THEN NEW.kind ELSE NEW.inverse_label END
                    WHERE NEW.semantics='mutual' OR NEW.inverse_label!=''),
                existing(a,b,label) AS (
                    SELECT source_id,target_id,kind FROM relationships WHERE deleted_at IS NULL AND id!=NEW.id UNION ALL
                    SELECT target_id,source_id,CASE WHEN semantics='mutual' THEN kind ELSE inverse_label END
                    FROM relationships WHERE deleted_at IS NULL AND id!=NEW.id AND (semantics='mutual' OR inverse_label!=''))
                SELECT 1 FROM incoming JOIN existing USING(a,b,label));
        END""")


def narrative_schema(connection):
    connection.execute("ALTER TABLE relationships ADD COLUMN baseline_active INTEGER NOT NULL DEFAULT 1 CHECK(baseline_active IN (0,1))")
    connection.execute("CREATE TABLE story_events (id INTEGER PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', sequence INTEGER NOT NULL UNIQUE CHECK(sequence>0))")
    connection.execute("CREATE TABLE event_participants (event_id INTEGER NOT NULL REFERENCES story_events(id), character_id INTEGER NOT NULL REFERENCES characters(id), PRIMARY KEY(event_id,character_id))")
    connection.execute("""CREATE TABLE relationship_history (
        id INTEGER PRIMARY KEY, relationship_id INTEGER NOT NULL REFERENCES relationships(id),
        event_id INTEGER NOT NULL REFERENCES story_events(id), active INTEGER NOT NULL CHECK(active IN (0,1)),
        source_id INTEGER NOT NULL REFERENCES characters(id), target_id INTEGER NOT NULL REFERENCES characters(id),
        kind TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', semantics TEXT NOT NULL CHECK(semantics IN ('directional','mutual')),
        inverse_label TEXT NOT NULL DEFAULT '', CHECK(source_id!=target_id), UNIQUE(relationship_id,event_id))""")
    # The base table now describes the undated starting state. Temporal
    # duplicates are checked at every event boundary by history_model.
    for event in ("insert", "update"):
        name = f"semantic_relationship_{event}"
        sql = connection.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()[0]
        connection.execute(f"DROP TRIGGER {name}")
        sql = sql.replace("NEW.deleted_at IS NULL", "NEW.deleted_at IS NULL AND NEW.baseline_active=1")
        sql = sql.replace("WHERE deleted_at IS NULL", "WHERE deleted_at IS NULL AND baseline_active=1")
        connection.execute(sql)
    connection.execute("DROP INDEX active_relationships")
    connection.execute("CREATE UNIQUE INDEX active_relationships ON relationships(source_id,target_id,kind) WHERE deleted_at IS NULL AND baseline_active=1")


def chapters_schema(connection):
    connection.execute("ALTER TABLE characters ADD COLUMN goals TEXT NOT NULL DEFAULT ''")
    connection.execute("CREATE TABLE chapters (id INTEGER PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', sequence INTEGER NOT NULL UNIQUE CHECK(sequence>0))")
    connection.execute("ALTER TABLE story_events ADD COLUMN chapter_id INTEGER REFERENCES chapters(id)")


def simple_schema(connection):
    connection.execute("ALTER TABLE characters ADD COLUMN introduction_event_id INTEGER REFERENCES story_events(id) DEFERRABLE INITIALLY DEFERRED")
    connection.execute("ALTER TABLE characters ADD COLUMN narrative_role TEXT NOT NULL DEFAULT 'neutral' CHECK(narrative_role IN ('neutral','protagonist','antagonist'))")
    connection.execute("CREATE TABLE story_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")


def classification_schema(connection):
    connection.execute("ALTER TABLE characters ADD COLUMN classification TEXT NOT NULL DEFAULT 'Neutral' CHECK(classification IN ('NPC Enemy','Player Enemy','Neutral','NPC Ally','Player Ally'))")


def character_type_schema(connection):
    from .legacy_character_type import CHARACTER_TYPES, LEGACY_TYPES, from_legacy
    options = ','.join("'" + value + "'" for value in (*CHARACTER_TYPES, *LEGACY_TYPES))
    connection.execute(f"ALTER TABLE characters ADD COLUMN character_type TEXT NOT NULL DEFAULT 'Neutral' CHECK(character_type IN ({options}))")
    for ident, classification, role in connection.execute('SELECT id,classification,narrative_role FROM characters').fetchall():
        connection.execute('UPDATE characters SET character_type=? WHERE id=?', (from_legacy(classification, role), ident))


def five_character_types_schema(connection):
    from .character_type import validate
    # Keep the exact pre-upgrade label for recovery without offering it in editors.
    connection.execute('ALTER TABLE characters RENAME COLUMN character_type TO legacy_character_type')
    connection.execute("ALTER TABLE characters ADD COLUMN character_type TEXT NOT NULL DEFAULT 'Neutral NPC' CHECK(character_type IN ('Player','Merchant','Allied NPC','Neutral NPC','Enemy NPC'))")
    for ident, value in connection.execute('SELECT id,legacy_character_type FROM characters').fetchall():
        connection.execute('UPDATE characters SET character_type=? WHERE id=?', (validate(value), ident))


def link_category_schema(connection):
    for table in ('relationships', 'relationship_history'):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN category TEXT NOT NULL DEFAULT '' CHECK(category IN ('','Support','Conflict','Personal','Other'))")


MIGRATIONS = (initial_schema, recovery_schema, profile_schema, graph_views_schema, organization_schema, relationship_semantics_schema, narrative_schema, chapters_schema, simple_schema, classification_schema, character_type_schema, five_character_types_schema, link_category_schema)
CURRENT_VERSION = len(MIGRATIONS)


def migrate(connection, path, make_backup=True):
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > CURRENT_VERSION:
        raise SchemaError(f"Database version {version} is newer than supported version {CURRENT_VERSION}. "
                          "Open it with a newer Story Atlas. No changes were made.")
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if version == 0 and tables:
        raise SchemaError("Unrecognized unversioned database. No changes were made.")
    if version:
        required = {"characters": {"id", *LEGACY_PROFILE_FIELDS},
                    "relationships": {"id", "source_id", "target_id", "kind", "notes"},
                    "activity": {"id", "timestamp", "action", "details"}}
        if version >= 2:
            required["characters"].add("deleted_at")
            required["relationships"].update(("deleted_at", "deletion_group"))
            required["drafts"] = {"key", "payload", "updated_at"}
        if version >= 3:
            required["characters"].update(("summary", "portrait"))
            required["portrait_assets"] = {"filename", "content"}
        if version >= 4:
            required["graph_views"] = {"name", "payload"}
        if version >= 5:
            required["characters"].add("tags")
            required["saved_filters"] = {"name", "payload"}
        if version >= 6:
            required["relationships"].update(("semantics", "inverse_label"))
        if version >= 7:
            required["relationships"].add("baseline_active")
            required["story_events"] = {"id", "title", "summary", "sequence"}
            required["event_participants"] = {"event_id", "character_id"}
            required["relationship_history"] = {"id", "relationship_id", "event_id", "active", "source_id", "target_id", "kind", "notes", "semantics", "inverse_label"}
        if version >= 8:
            required["characters"].add("goals")
            required["chapters"] = {"id", "title", "summary", "sequence"}
            required["story_events"].add("chapter_id")
        if version >= 9:
            required["characters"].update(("introduction_event_id", "narrative_role"))
            required["story_metadata"] = {"key", "value"}
        if version >= 10:
            required['characters'].add('classification')
        if version >= 11:
            required['characters'].add('character_type')
        if version >= 12:
            required['characters'].add('legacy_character_type')
        if version >= 13:
            required['relationships'].add('category')
            required['relationship_history'].add('category')
        for table, columns in required.items():
            actual = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            if not columns <= actual:
                raise SchemaError(f"Invalid Story Atlas schema: missing fields in {table}.")
    if version == CURRENT_VERSION:
        return
    if version and make_backup:
        snapshot(connection, path, reason=f"pre-migration-v{version}")
    # executescript commits implicitly, so each migration uses execute instead.
    connection.execute("BEGIN IMMEDIATE")
    try:
        for index in range(version, CURRENT_VERSION):
            MIGRATIONS[index](connection)
            connection.execute(f"PRAGMA user_version = {index + 1}")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise SchemaError("Migration found invalid character references.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
