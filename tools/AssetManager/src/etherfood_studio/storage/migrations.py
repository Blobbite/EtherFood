"""Forward-only schema steps; each statement runs inside one transaction."""

MIGRATIONS = {
    1: (
        "CREATE TABLE schema_version (version INTEGER NOT NULL)",
        "INSERT INTO schema_version VALUES (0)",
        """CREATE TABLE objects (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
            owner_id TEXT REFERENCES objects(id) DEFERRABLE INITIALLY DEFERRED,
            data TEXT NOT NULL CHECK(json_valid(data)),
            revision_no INTEGER NOT NULL CHECK(revision_no > 0),
            archived INTEGER NOT NULL CHECK(archived IN (0,1)),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE relations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES objects(id),
            target_id TEXT NOT NULL REFERENCES objects(id),
            kind TEXT NOT NULL CHECK(kind IN ('belongs_to','uses','depends_on')),
            UNIQUE(source_id,target_id,kind), CHECK(source_id != target_id)
        )""",
        """CREATE UNIQUE INDEX one_parent ON relations(source_id)
            WHERE kind='belongs_to'""",
        """CREATE TABLE revisions (
            object_id TEXT NOT NULL REFERENCES objects(id),
            revision_no INTEGER NOT NULL, snapshot TEXT NOT NULL,
            PRIMARY KEY(object_id, revision_no)
        )""",
    ),
    2: (
        """CREATE TABLE layouts (
            object_id TEXT PRIMARY KEY REFERENCES objects(id), data TEXT NOT NULL
        )""",
        """CREATE TABLE blobs (
            sha256 TEXT PRIMARY KEY CHECK(length(sha256)=64),
            length INTEGER NOT NULL CHECK(length>=0), media_type TEXT NOT NULL
        )""",
        """CREATE TABLE operations (
            id TEXT PRIMARY KEY, state TEXT NOT NULL, data TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
    ),
    3: (
        """CREATE TABLE inventory_roots (
            id TEXT PRIMARY KEY, local_path TEXT NOT NULL UNIQUE
        )""",
    ),
}

CURRENT_VERSION = max(MIGRATIONS)
