-- Learning-owned, append-only per evidence/event human applicability decisions.
-- Original evidence, grades, attempts and Content events remain unchanged.
CREATE TABLE learning_applicability_decisions(
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id TEXT NOT NULL REFERENCES workspace(id),
  evidence_id TEXT NOT NULL REFERENCES evidence(id),
  event_id TEXT NOT NULL REFERENCES content_impact_snapshots(event_id),
  decision_revision INTEGER NOT NULL CHECK(decision_revision>=1),
  actor_session_id TEXT NOT NULL REFERENCES local_sessions(id),
  route TEXT NOT NULL,
  command_key TEXT NOT NULL,
  request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64),
  record_json TEXT NOT NULL CHECK(json_valid(record_json)),
  record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
  created_at TEXT NOT NULL,
  UNIQUE(workspace_id,evidence_id,event_id,decision_revision),
  UNIQUE(workspace_id,actor_session_id,route,command_key)
);
CREATE TRIGGER learning_applicability_no_replace BEFORE INSERT ON learning_applicability_decisions
WHEN EXISTS(SELECT 1 FROM learning_applicability_decisions
  WHERE sequence=NEW.sequence OR (workspace_id=NEW.workspace_id AND
    ((evidence_id=NEW.evidence_id AND event_id=NEW.event_id AND decision_revision=NEW.decision_revision)
     OR (actor_session_id=NEW.actor_session_id AND route=NEW.route AND command_key=NEW.command_key))))
BEGIN SELECT RAISE(ABORT,'Learning applicability decisions are immutable'); END;
CREATE TRIGGER learning_applicability_no_update BEFORE UPDATE ON learning_applicability_decisions
BEGIN SELECT RAISE(ABORT,'Learning applicability decisions are append-only'); END;
CREATE TRIGGER learning_applicability_no_delete BEFORE DELETE ON learning_applicability_decisions
BEGIN SELECT RAISE(ABORT,'Learning applicability decisions are append-only'); END;

-- Independent heads detect a missing final receipt, including complete loss of
-- an event's decision rows. They are advanced only with the append transaction.
CREATE TABLE learning_applicability_heads(
  workspace_id TEXT NOT NULL REFERENCES workspace(id),
  evidence_id TEXT NOT NULL REFERENCES evidence(id),
  event_id TEXT NOT NULL REFERENCES content_impact_snapshots(event_id),
  decision_revision INTEGER NOT NULL CHECK(decision_revision>=1),
  receipt_sha256 TEXT NOT NULL CHECK(length(receipt_sha256)=64),
  PRIMARY KEY(workspace_id,evidence_id,event_id)
);
CREATE TRIGGER learning_applicability_head_no_replace BEFORE INSERT ON learning_applicability_heads
WHEN EXISTS(SELECT 1 FROM learning_applicability_heads WHERE workspace_id=NEW.workspace_id
  AND evidence_id=NEW.evidence_id AND event_id=NEW.event_id)
BEGIN SELECT RAISE(ABORT,'Learning applicability heads cannot be replaced'); END;
CREATE TRIGGER learning_applicability_head_no_delete BEFORE DELETE ON learning_applicability_heads
BEGIN SELECT RAISE(ABORT,'Learning applicability heads cannot be deleted'); END;
CREATE TRIGGER learning_applicability_head_cas BEFORE UPDATE ON learning_applicability_heads
WHEN NEW.workspace_id!=OLD.workspace_id OR NEW.evidence_id!=OLD.evidence_id OR NEW.event_id!=OLD.event_id
  OR NEW.decision_revision!=OLD.decision_revision+1
BEGIN SELECT RAISE(ABORT,'Learning applicability heads require consecutive revisions'); END;
