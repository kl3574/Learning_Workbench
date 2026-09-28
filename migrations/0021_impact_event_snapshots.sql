-- Content-owned immutable evidence for invalidation events published after this migration.
-- Existing outbox rows are deliberately not backfilled or promoted to verified history.
CREATE TABLE content_impact_legacy_events(
    event_id TEXT PRIMARY KEY REFERENCES outbox(id),
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
INSERT INTO content_impact_legacy_events(event_id,payload_json)
SELECT id,payload_json FROM outbox WHERE event_type='content.dependencies_invalidated';
CREATE TRIGGER content_impact_legacy_no_insert BEFORE INSERT ON content_impact_legacy_events
BEGIN SELECT RAISE(ABORT,'legacy impact registration is migration-only'); END;
CREATE TRIGGER content_impact_legacy_no_update BEFORE UPDATE ON content_impact_legacy_events
BEGIN SELECT RAISE(ABORT,'immutable legacy impact registration'); END;
CREATE TRIGGER content_impact_legacy_no_delete BEFORE DELETE ON content_impact_legacy_events
BEGIN SELECT RAISE(ABORT,'immutable legacy impact registration'); END;
CREATE TABLE content_impact_snapshots(
    event_id TEXT PRIMARY KEY REFERENCES outbox(id),
    workspace_id TEXT NOT NULL REFERENCES workspace(id),
    snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
    snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256)=64)
);
CREATE TRIGGER content_impact_snapshot_no_replace BEFORE INSERT ON content_impact_snapshots
WHEN EXISTS(SELECT 1 FROM content_impact_snapshots WHERE event_id=NEW.event_id)
BEGIN SELECT RAISE(ABORT,'immutable content impact snapshot'); END;
CREATE TRIGGER content_impact_snapshot_source BEFORE INSERT ON content_impact_snapshots
WHEN NOT EXISTS(SELECT 1 FROM outbox o WHERE o.id=NEW.event_id
                AND o.event_type='content.dependencies_invalidated'
                AND json_extract(o.payload_json,'$.workspace_id')=NEW.workspace_id)
BEGIN SELECT RAISE(ABORT,'content impact event owner mismatch'); END;
CREATE TRIGGER content_impact_snapshot_no_update BEFORE UPDATE ON content_impact_snapshots
BEGIN SELECT RAISE(ABORT,'immutable content impact snapshot'); END;
CREATE TRIGGER content_impact_snapshot_no_delete BEFORE DELETE ON content_impact_snapshots
BEGIN SELECT RAISE(ABORT,'immutable content impact snapshot'); END;
