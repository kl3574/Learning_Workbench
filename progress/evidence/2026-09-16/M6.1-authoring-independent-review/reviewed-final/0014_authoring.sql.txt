-- Authoring records and immutable command ACKs do not reuse Import drafts.
CREATE TABLE authoring_records(
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 actor_id TEXT NOT NULL,
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL
);
CREATE INDEX authoring_records_workspace ON authoring_records(workspace_id,sequence);
CREATE TABLE authoring_authorizations(
 consent_id TEXT PRIMARY KEY,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 job_id TEXT NOT NULL REFERENCES jobs(id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL
);
CREATE TABLE authoring_candidates(
 draft_id TEXT PRIMARY KEY,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 source_job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL
);
CREATE TABLE authoring_numeric_checks(
 check_id TEXT PRIMARY KEY,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 draft_id TEXT NOT NULL REFERENCES authoring_candidates(draft_id),
 job_id TEXT UNIQUE REFERENCES jobs(id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL
);
CREATE TABLE authoring_numeric_executions(
 job_id TEXT PRIMARY KEY REFERENCES jobs(id),
 start_json TEXT NOT NULL CHECK(json_valid(start_json)),
 start_sha256 TEXT NOT NULL,
 end_json TEXT CHECK(end_json IS NULL OR json_valid(end_json)),
 end_sha256 TEXT
);
CREATE TABLE authoring_commands(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 actor_id TEXT NOT NULL,
 route TEXT NOT NULL,
 key TEXT NOT NULL,
 owner_id TEXT NOT NULL,
 request_json TEXT NOT NULL CHECK(json_valid(request_json)),
 request_sha256 TEXT NOT NULL,
 ack_json TEXT NOT NULL CHECK(json_valid(ack_json)),
 ack_sha256 TEXT NOT NULL,
 job_revision INTEGER,
 created_at TEXT NOT NULL,
 basis_revision INTEGER,
 PRIMARY KEY(workspace_id,actor_id,route,key)
);
