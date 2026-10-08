-- Independent membership and the original internal Jobs command, bound to v4.
CREATE TABLE codex_turn_interrupts(session_id TEXT NOT NULL,workspace_id TEXT NOT NULL REFERENCES workspace(id),seq INTEGER NOT NULL CHECK(seq>0),turn_id TEXT NOT NULL,stop_command_json TEXT NOT NULL CHECK(json_valid(stop_command_json)),stop_command_sha256 TEXT NOT NULL,event_sha256 TEXT NOT NULL,PRIMARY KEY(session_id,seq));
CREATE TRIGGER codex_turn_interrupts_insert BEFORE INSERT ON codex_turn_interrupts WHEN EXISTS(SELECT 1 FROM codex_turn_interrupts WHERE session_id=NEW.session_id AND seq=NEW.seq) BEGIN SELECT RAISE(ABORT,'immutable codex interrupt'); END;
CREATE TRIGGER codex_turn_interrupts_update BEFORE UPDATE ON codex_turn_interrupts BEGIN SELECT RAISE(ABORT,'immutable codex interrupt'); END;
CREATE TRIGGER codex_turn_interrupts_delete BEFORE DELETE ON codex_turn_interrupts BEGIN SELECT RAISE(ABORT,'immutable codex interrupt'); END;
