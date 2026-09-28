"""Forward-only schema steps; each statement runs inside one transaction."""

# Also normalize old metadata snapshots imported into an already current catalog.
# Only legacy ownership with a matching project binding is eligible. Historical
# revisions and frozen builds stay intact; record the ownership change separately.
PIPELINE_PROJECT_OWNERSHIP = (
    """CREATE TEMP TABLE pipeline_project_owners AS
        SELECT object.id, object.owner_id AS old_owner, project.id AS project_id
        FROM objects AS object
        JOIN objects AS scope ON scope.id=object.owner_id AND scope.kind='global'
        JOIN objects AS project ON project.id=scope.owner_id AND project.kind='project'
        WHERE json_extract(object.data, '$.project_id')=project.id AND
            (object.kind='pipeline' OR (object.kind='pipeline_assignment' AND
                json_extract(object.data, '$.asset_id') IS NULL))""",
    """UPDATE relations SET target_id=(SELECT project_id FROM pipeline_project_owners
            WHERE id=relations.source_id)
        WHERE kind='belongs_to' AND source_id IN (SELECT id FROM pipeline_project_owners)
            AND target_id=(SELECT old_owner FROM pipeline_project_owners
                WHERE id=relations.source_id)""",
    """UPDATE objects SET owner_id=(SELECT project_id FROM pipeline_project_owners
            WHERE id=objects.id), revision_no=revision_no+1,
            updated_at=strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')
        WHERE id IN (SELECT id FROM pipeline_project_owners)""",
    """INSERT INTO revisions (object_id, revision_no, snapshot)
        SELECT id, revision_no, json_object(
            'id', id, 'kind', kind, 'title', title, 'owner_id', owner_id,
            'data', json(data), 'revision_no', revision_no,
            'archived', json(CASE WHEN archived=1 THEN 'true' ELSE 'false' END),
            'created_at', created_at, 'updated_at', updated_at)
        FROM objects WHERE id IN (SELECT id FROM pipeline_project_owners)""",
    "DROP TABLE pipeline_project_owners",
)

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
    4: (
        """CREATE TABLE jobs (
            id TEXT PRIMARY KEY, request TEXT NOT NULL, status TEXT NOT NULL,
            resource_key TEXT NOT NULL, owner_pid INTEGER NOT NULL, owner_stamp TEXT NOT NULL,
            result TEXT, created_at TEXT NOT NULL
        )""",
        """CREATE UNIQUE INDEX active_job_writer ON jobs(resource_key)
            WHERE status IN ('running','cancelling')""",
        """CREATE TABLE job_events (
            job_id TEXT NOT NULL REFERENCES jobs(id), seq INTEGER NOT NULL,
            data TEXT NOT NULL, PRIMARY KEY(job_id,seq)
        )""",
    ),
    5: (
        """CREATE TABLE build_cache (
            build_id TEXT PRIMARY KEY REFERENCES objects(id), node_key TEXT NOT NULL,
            input_fingerprint TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id)
        )""",
        "CREATE INDEX cache_fingerprint ON build_cache(input_fingerprint)",
    ),
    6: (
        """CREATE TABLE pipeline_plugins (
            identifier TEXT PRIMARY KEY, manifest TEXT NOT NULL CHECK(json_valid(manifest)),
            code_path TEXT NOT NULL, code_hash TEXT NOT NULL, approved_hash TEXT
        )""",
    ),
    7: PIPELINE_PROJECT_OWNERSHIP,
    8: (
        "CREATE TABLE card_paths (id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE)",
        "CREATE TABLE managed_files (owner_id TEXT NOT NULL, path TEXT NOT NULL, "
        "sha256 TEXT NOT NULL, PRIMARY KEY(owner_id,path))",
        "CREATE TABLE asset_publications (build_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, "
        "path TEXT NOT NULL)",
        "CREATE TABLE file_commits (id TEXT PRIMARY KEY)",
    ),
    9: (
        "CREATE TABLE document_files (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, "
        "path TEXT NOT NULL, sha256 TEXT NOT NULL, body TEXT NOT NULL)",
    ),
}

CURRENT_VERSION = max(MIGRATIONS)
