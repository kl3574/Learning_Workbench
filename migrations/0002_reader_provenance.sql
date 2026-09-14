-- Derived M2.4 persistence: freeze exact public block provenance at import confirmation.
-- Source access permissions remain live and are never copied into this public snapshot.
CREATE TABLE block_provenance(
    workspace_id TEXT NOT NULL REFERENCES workspace(id),
    block_id TEXT NOT NULL,
    block_revision INTEGER NOT NULL CHECK(block_revision>=1),
    block_sha256 TEXT NOT NULL CHECK(length(block_sha256)=64),
    source_id TEXT NOT NULL REFERENCES sources(id),
    import_id TEXT NOT NULL REFERENCES ingestion_imports(id),
    snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
    snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256)=64),
    created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,block_id,block_revision,block_sha256),
    FOREIGN KEY(block_id,block_revision,block_sha256) REFERENCES revisions(object_id,revision,sha256)
);
CREATE TRIGGER block_provenance_no_update BEFORE UPDATE ON block_provenance BEGIN SELECT RAISE(ABORT,'published provenance immutable'); END;
CREATE TRIGGER block_provenance_workspace BEFORE INSERT ON block_provenance WHEN
    NOT EXISTS(SELECT 1 FROM objects WHERE id=NEW.block_id AND workspace_id=NEW.workspace_id AND kind='block') OR
    NOT EXISTS(SELECT 1 FROM sources WHERE id=NEW.source_id AND workspace_id=NEW.workspace_id) OR
    NOT EXISTS(SELECT 1 FROM ingestion_imports WHERE id=NEW.import_id AND workspace_id=NEW.workspace_id AND source_id=NEW.source_id)
BEGIN SELECT RAISE(ABORT,'provenance workspace or source mismatch'); END;
