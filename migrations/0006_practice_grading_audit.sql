-- Keep old M3.1 submission bytes unchanged. New deterministic grades receive a
-- private, immutable audit bound to that same submission and its existing outbox.
CREATE TABLE practice_grading_audits (
    session_id TEXT PRIMARY KEY REFERENCES practice_sessions(id),
    workspace_id TEXT NOT NULL REFERENCES workspace(id),
    outbox_id TEXT NOT NULL UNIQUE REFERENCES outbox(id),
    audit_json TEXT NOT NULL CHECK(json_valid(audit_json)),
    audit_sha256 TEXT NOT NULL CHECK(length(audit_sha256)=64),
    created_at TEXT NOT NULL
);
CREATE TRIGGER practice_grading_audit_no_update BEFORE UPDATE ON practice_grading_audits
BEGIN SELECT RAISE(ABORT,'practice grading audit immutable'); END;
