-- New Restore owner only. No old approvals, Reviews, content or Jobs are rewritten.
CREATE TABLE restore_numeric_materials(
 draft_id TEXT PRIMARY KEY NOT NULL REFERENCES content_restore_drafts(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 material_json TEXT NOT NULL CHECK(json_valid(material_json)),
 material_sha256 TEXT NOT NULL CHECK(length(material_sha256)=64)
);
CREATE TABLE restore_numeric_heads(
 draft_id TEXT PRIMARY KEY NOT NULL REFERENCES restore_numeric_materials(draft_id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 sequence INTEGER NOT NULL CHECK(typeof(sequence)='integer' AND sequence>=0),
 check_count INTEGER NOT NULL CHECK(typeof(check_count)='integer' AND check_count BETWEEN 0 AND 100),
 event_sha256 TEXT NOT NULL CHECK(length(event_sha256)=64)
);
CREATE TABLE restore_numeric_events(
 draft_id TEXT NOT NULL REFERENCES restore_numeric_materials(draft_id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 sequence INTEGER NOT NULL CHECK(typeof(sequence)='integer' AND sequence>=1),
 check_id TEXT NOT NULL,
 event_json TEXT NOT NULL CHECK(json_valid(event_json)),
 event_sha256 TEXT NOT NULL CHECK(length(event_sha256)=64),
 PRIMARY KEY(draft_id,sequence)
);
CREATE TABLE restore_numeric_checks(
 check_id TEXT PRIMARY KEY NOT NULL,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 draft_id TEXT NOT NULL REFERENCES restore_numeric_materials(draft_id),
 ordinal INTEGER NOT NULL CHECK(typeof(ordinal)='integer' AND ordinal BETWEEN 1 AND 100),
 preview_sequence INTEGER NOT NULL,
 UNIQUE(draft_id,ordinal),
 FOREIGN KEY(draft_id,preview_sequence) REFERENCES restore_numeric_events(draft_id,sequence)
);
CREATE TABLE restore_numeric_commands(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 actor_id TEXT NOT NULL REFERENCES local_sessions(id),
 route TEXT NOT NULL,
 command_key TEXT NOT NULL,
 draft_id TEXT NOT NULL,
 sequence INTEGER NOT NULL,
 PRIMARY KEY(workspace_id,actor_id,route,command_key),
 UNIQUE(draft_id,sequence),
 FOREIGN KEY(draft_id,sequence) REFERENCES restore_numeric_events(draft_id,sequence)
);
CREATE TABLE restore_numeric_jobs(
 job_id TEXT PRIMARY KEY NOT NULL REFERENCES jobs(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 check_id TEXT NOT NULL UNIQUE REFERENCES restore_numeric_checks(check_id),
 actor_id TEXT NOT NULL REFERENCES local_sessions(id),
 input_json TEXT NOT NULL CHECK(json_valid(input_json)),
 input_sha256 TEXT NOT NULL CHECK(length(input_sha256)=64)
);

CREATE TRIGGER restore_numeric_materials_no_replace BEFORE INSERT ON restore_numeric_materials
 WHEN EXISTS(SELECT 1 FROM restore_numeric_materials WHERE draft_id=NEW.draft_id)
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_materials_no_delete BEFORE DELETE ON restore_numeric_materials
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_materials_no_update BEFORE UPDATE ON restore_numeric_materials
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;

CREATE TRIGGER restore_numeric_heads_no_replace BEFORE INSERT ON restore_numeric_heads
 WHEN EXISTS(SELECT 1 FROM restore_numeric_heads WHERE draft_id=NEW.draft_id)
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_heads_no_delete BEFORE DELETE ON restore_numeric_heads
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;

CREATE TRIGGER restore_numeric_events_no_replace BEFORE INSERT ON restore_numeric_events
 WHEN EXISTS(SELECT 1 FROM restore_numeric_events WHERE draft_id=NEW.draft_id AND sequence=NEW.sequence)
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_events_no_delete BEFORE DELETE ON restore_numeric_events
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_events_no_update BEFORE UPDATE ON restore_numeric_events
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;

CREATE TRIGGER restore_numeric_checks_no_replace BEFORE INSERT ON restore_numeric_checks
 WHEN EXISTS(SELECT 1 FROM restore_numeric_checks WHERE check_id=NEW.check_id OR (draft_id=NEW.draft_id AND ordinal=NEW.ordinal))
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_checks_no_delete BEFORE DELETE ON restore_numeric_checks
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_checks_no_update BEFORE UPDATE ON restore_numeric_checks
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;

CREATE TRIGGER restore_numeric_commands_no_replace BEFORE INSERT ON restore_numeric_commands
 WHEN EXISTS(SELECT 1 FROM restore_numeric_commands WHERE (workspace_id=NEW.workspace_id AND actor_id=NEW.actor_id AND route=NEW.route AND command_key=NEW.command_key) OR (draft_id=NEW.draft_id AND sequence=NEW.sequence))
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_commands_no_delete BEFORE DELETE ON restore_numeric_commands
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_commands_no_update BEFORE UPDATE ON restore_numeric_commands
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;

CREATE TRIGGER restore_numeric_jobs_no_replace BEFORE INSERT ON restore_numeric_jobs
 WHEN EXISTS(SELECT 1 FROM restore_numeric_jobs WHERE job_id=NEW.job_id OR check_id=NEW.check_id)
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_jobs_no_delete BEFORE DELETE ON restore_numeric_jobs
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;
CREATE TRIGGER restore_numeric_jobs_no_update BEFORE UPDATE ON restore_numeric_jobs
 BEGIN SELECT RAISE(ABORT,'restore numeric immutable'); END;

CREATE TRIGGER restore_numeric_head_initial BEFORE INSERT ON restore_numeric_heads
 WHEN NEW.sequence<>0 OR NEW.check_count<>0 OR NEW.event_sha256<>printf('%064d',0)
 BEGIN SELECT RAISE(ABORT,'restore numeric head initial'); END;
CREATE TRIGGER restore_numeric_head_cas BEFORE UPDATE ON restore_numeric_heads
 WHEN NEW.draft_id<>OLD.draft_id OR NEW.workspace_id<>OLD.workspace_id
 OR NEW.sequence<>OLD.sequence+1 OR NEW.check_count NOT IN (OLD.check_count,OLD.check_count+1)
 OR NOT EXISTS(SELECT 1 FROM restore_numeric_events e WHERE e.draft_id=NEW.draft_id
  AND e.workspace_id=NEW.workspace_id AND e.sequence=NEW.sequence AND e.event_sha256=NEW.event_sha256)
 BEGIN SELECT RAISE(ABORT,'restore numeric head CAS'); END;
