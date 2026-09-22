-- Group candidates are new Authoring-owned records, never Import or published content.
CREATE TABLE authoring_content_plans(
 source_job_id TEXT PRIMARY KEY REFERENCES jobs(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL
);
CREATE TABLE authoring_group_candidates(
 draft_id TEXT PRIMARY KEY,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 source_job_id TEXT NOT NULL UNIQUE REFERENCES authoring_content_plans(source_job_id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL
);
CREATE TABLE authoring_group_numeric_checks(
 check_id TEXT PRIMARY KEY,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 draft_id TEXT NOT NULL REFERENCES authoring_group_candidates(draft_id),
 job_id TEXT UNIQUE REFERENCES jobs(id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL
);
