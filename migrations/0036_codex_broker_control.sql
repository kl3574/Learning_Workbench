-- Private Broker history, with independent v7 witnesses in the existing turn chain.
CREATE TABLE codex_broker_records(workspace_id TEXT NOT NULL REFERENCES workspace(id),turn_id TEXT NOT NULL,ordinal INTEGER NOT NULL CHECK(ordinal>=1),record_json TEXT NOT NULL CHECK(json_valid(record_json)),record_sha256 TEXT NOT NULL,PRIMARY KEY(turn_id,ordinal));
CREATE TABLE codex_broker_members(workspace_id TEXT NOT NULL REFERENCES workspace(id),turn_id TEXT NOT NULL,ordinal INTEGER NOT NULL CHECK(ordinal>=1),record_sha256 TEXT NOT NULL,PRIMARY KEY(turn_id,ordinal));
CREATE TABLE codex_broker_heads(workspace_id TEXT NOT NULL REFERENCES workspace(id),turn_id TEXT PRIMARY KEY,event_count INTEGER NOT NULL CHECK(event_count>=1),head_sha256 TEXT NOT NULL);
CREATE TRIGGER codex_broker_records_update BEFORE UPDATE ON codex_broker_records BEGIN SELECT RAISE(ABORT,'immutable Codex Broker'); END;
CREATE TRIGGER codex_broker_records_delete BEFORE DELETE ON codex_broker_records BEGIN SELECT RAISE(ABORT,'immutable Codex Broker'); END;
CREATE TRIGGER codex_broker_records_replace BEFORE INSERT ON codex_broker_records WHEN EXISTS(SELECT 1 FROM codex_broker_records WHERE turn_id=NEW.turn_id AND ordinal=NEW.ordinal) BEGIN SELECT RAISE(ABORT,'immutable Codex Broker'); END;
CREATE TRIGGER codex_broker_members_update BEFORE UPDATE ON codex_broker_members BEGIN SELECT RAISE(ABORT,'immutable Codex Broker'); END;
CREATE TRIGGER codex_broker_members_delete BEFORE DELETE ON codex_broker_members BEGIN SELECT RAISE(ABORT,'immutable Codex Broker'); END;
CREATE TRIGGER codex_broker_members_replace BEFORE INSERT ON codex_broker_members WHEN EXISTS(SELECT 1 FROM codex_broker_members WHERE turn_id=NEW.turn_id AND ordinal=NEW.ordinal) BEGIN SELECT RAISE(ABORT,'immutable Codex Broker'); END;
CREATE TRIGGER codex_broker_heads_delete BEFORE DELETE ON codex_broker_heads BEGIN SELECT RAISE(ABORT,'immutable Codex Broker head'); END;
CREATE TRIGGER codex_broker_heads_replace BEFORE INSERT ON codex_broker_heads WHEN EXISTS(SELECT 1 FROM codex_broker_heads WHERE turn_id=NEW.turn_id) BEGIN SELECT RAISE(ABORT,'immutable Codex Broker head'); END;
CREATE TRIGGER codex_broker_heads_update BEFORE UPDATE ON codex_broker_heads WHEN NEW.workspace_id!=OLD.workspace_id OR NEW.turn_id!=OLD.turn_id OR NEW.event_count!=OLD.event_count+1 OR NOT EXISTS(SELECT 1 FROM codex_broker_records WHERE turn_id=NEW.turn_id AND workspace_id=NEW.workspace_id AND ordinal=NEW.event_count AND record_sha256=NEW.head_sha256) BEGIN SELECT RAISE(ABORT,'invalid Codex Broker head'); END;
