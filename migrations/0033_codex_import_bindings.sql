-- Import owns immutable Codex source membership; no defaults or rewrites of old Imports.
CREATE TABLE codex_import_batches (
    aggregate_job_id TEXT PRIMARY KEY REFERENCES jobs(id),
    workspace_id TEXT NOT NULL REFERENCES workspace(id),
    record_json TEXT NOT NULL,
    record_sha256 TEXT NOT NULL
);
CREATE TABLE codex_import_previews (
    import_id TEXT PRIMARY KEY REFERENCES codex_import_bindings(import_id),
    workspace_id TEXT NOT NULL REFERENCES workspace(id),
    record_json TEXT NOT NULL,
    record_sha256 TEXT NOT NULL
);
CREATE TABLE codex_import_bindings (
    import_id TEXT PRIMARY KEY REFERENCES ingestion_imports(id),
    workspace_id TEXT NOT NULL REFERENCES workspace(id),
    aggregate_job_id TEXT NOT NULL REFERENCES codex_import_batches(aggregate_job_id),
    ordinal INTEGER NOT NULL CHECK(ordinal >= 0 AND ordinal < 32),
    source_id TEXT NOT NULL UNIQUE REFERENCES sources(id),
    import_job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
    record_json TEXT NOT NULL,
    record_sha256 TEXT NOT NULL,
    UNIQUE(aggregate_job_id, ordinal)
);
