-- Publication-owned terminal association. Original Authoring snapshots stay unchanged.
CREATE TABLE single_publication_bindings(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 draft_id TEXT NOT NULL,
 draft_revision INTEGER NOT NULL CHECK(draft_revision=1),
 candidate_sha256 TEXT NOT NULL CHECK(length(candidate_sha256)=64),
 publication_id TEXT NOT NULL UNIQUE REFERENCES draft_publication_results(publication_id),
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 PRIMARY KEY(workspace_id,draft_id,draft_revision)
);
CREATE TRIGGER single_publication_bindings_no_replace BEFORE INSERT ON single_publication_bindings
 WHEN EXISTS(SELECT 1 FROM single_publication_bindings WHERE publication_id=NEW.publication_id
 OR (workspace_id=NEW.workspace_id AND draft_id=NEW.draft_id AND draft_revision=NEW.draft_revision))
 BEGIN SELECT RAISE(ABORT,'single publication immutable'); END;
CREATE TRIGGER single_publication_bindings_no_update BEFORE UPDATE ON single_publication_bindings
 BEGIN SELECT RAISE(ABORT,'single publication immutable'); END;
CREATE TRIGGER single_publication_bindings_no_delete BEFORE DELETE ON single_publication_bindings
 BEGIN SELECT RAISE(ABORT,'single publication immutable'); END;
