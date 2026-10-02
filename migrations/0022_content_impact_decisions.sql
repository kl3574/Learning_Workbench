-- Content-owned append-only object decisions. No other owner's rows are mutated.
CREATE TABLE content_impact_decisions(
  workspace_id TEXT NOT NULL REFERENCES workspace(id),
  event_id TEXT NOT NULL REFERENCES content_impact_snapshots(event_id),
  target_id TEXT NOT NULL REFERENCES objects(id),
  decision_revision INTEGER NOT NULL CHECK(decision_revision>=1),
  actor_session_id TEXT NOT NULL REFERENCES local_sessions(id),
  route TEXT NOT NULL,
  command_key TEXT NOT NULL,
  record_json TEXT NOT NULL CHECK(json_valid(record_json)),
  record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
  PRIMARY KEY(event_id,target_id,decision_revision),
  UNIQUE(workspace_id,actor_session_id,route,command_key)
);
CREATE TRIGGER content_impact_decision_no_replace BEFORE INSERT ON content_impact_decisions
WHEN EXISTS(SELECT 1 FROM content_impact_decisions WHERE
  (event_id=NEW.event_id AND target_id=NEW.target_id AND decision_revision=NEW.decision_revision)
  OR (workspace_id=NEW.workspace_id AND actor_session_id=NEW.actor_session_id
      AND route=NEW.route AND command_key=NEW.command_key))
BEGIN SELECT RAISE(ABORT,'content impact decisions cannot be replaced'); END;
CREATE TRIGGER content_impact_decision_no_update BEFORE UPDATE ON content_impact_decisions
BEGIN SELECT RAISE(ABORT,'content impact decisions are immutable'); END;
CREATE TRIGGER content_impact_decision_no_delete BEFORE DELETE ON content_impact_decisions
BEGIN SELECT RAISE(ABORT,'content impact decisions are append only'); END;

-- Independent current ledger head catches a missing/truncated immutable history.
CREATE TABLE content_impact_decision_heads(
  workspace_id TEXT NOT NULL REFERENCES workspace(id),
  event_id TEXT NOT NULL REFERENCES content_impact_snapshots(event_id),
  target_id TEXT NOT NULL REFERENCES objects(id),
  decision_revision INTEGER NOT NULL CHECK(decision_revision>=1),
  receipt_sha256 TEXT NOT NULL CHECK(length(receipt_sha256)=64),
  PRIMARY KEY(event_id,target_id),
  FOREIGN KEY(event_id,target_id,decision_revision) REFERENCES content_impact_decisions(event_id,target_id,decision_revision)
);
