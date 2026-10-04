-- Separate forward facts: no original model/tool profile or historical ACK rewrite.
CREATE TABLE codex_artifact_records(workspace_id TEXT NOT NULL REFERENCES workspace(id),turn_id TEXT PRIMARY KEY,record_json TEXT NOT NULL CHECK(json_valid(record_json)),record_sha256 TEXT NOT NULL);
CREATE TABLE codex_artifact_members(workspace_id TEXT NOT NULL REFERENCES workspace(id),turn_id TEXT NOT NULL,ordinal INTEGER NOT NULL CHECK(ordinal>=0),artifact_id TEXT NOT NULL UNIQUE REFERENCES artifacts(id),entry_sha256 TEXT NOT NULL,PRIMARY KEY(turn_id,ordinal));
CREATE TRIGGER codex_artifact_records_update BEFORE UPDATE ON codex_artifact_records BEGIN SELECT RAISE(ABORT,'immutable Codex artifact'); END;
CREATE TRIGGER codex_artifact_records_delete BEFORE DELETE ON codex_artifact_records BEGIN SELECT RAISE(ABORT,'immutable Codex artifact'); END;
CREATE TRIGGER codex_artifact_records_replace BEFORE INSERT ON codex_artifact_records WHEN EXISTS(SELECT 1 FROM codex_artifact_records WHERE turn_id=NEW.turn_id) BEGIN SELECT RAISE(ABORT,'immutable Codex artifact'); END;
CREATE TRIGGER codex_artifact_members_update BEFORE UPDATE ON codex_artifact_members BEGIN SELECT RAISE(ABORT,'immutable Codex artifact'); END;
CREATE TRIGGER codex_artifact_members_delete BEFORE DELETE ON codex_artifact_members BEGIN SELECT RAISE(ABORT,'immutable Codex artifact'); END;
CREATE TRIGGER codex_artifact_members_replace BEFORE INSERT ON codex_artifact_members WHEN EXISTS(SELECT 1 FROM codex_artifact_members WHERE turn_id=NEW.turn_id AND ordinal=NEW.ordinal OR artifact_id=NEW.artifact_id) BEGIN SELECT RAISE(ABORT,'immutable Codex artifact'); END;
