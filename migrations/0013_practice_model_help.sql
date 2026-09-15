-- Practice-owned model assistance. Existing rule levels and submission bytes stay fixed.
CREATE TABLE practice_model_help(
 run_id TEXT PRIMARY KEY REFERENCES runs(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 session_id TEXT NOT NULL REFERENCES practice_sessions(id),
 exposure_id TEXT NOT NULL UNIQUE REFERENCES exposures(id),
 receipt_json TEXT NOT NULL CHECK(json_valid(receipt_json)),
 receipt_sha256 TEXT NOT NULL CHECK(length(receipt_sha256)=64)
);
CREATE INDEX practice_model_help_session ON practice_model_help(workspace_id,session_id);
CREATE TRIGGER practice_model_help_no_update BEFORE UPDATE ON practice_model_help
 BEGIN SELECT RAISE(ABORT,'practice model help immutable'); END;
CREATE TRIGGER practice_model_help_no_delete BEFORE DELETE ON practice_model_help
 BEGIN SELECT RAISE(ABORT,'practice model help immutable'); END;
