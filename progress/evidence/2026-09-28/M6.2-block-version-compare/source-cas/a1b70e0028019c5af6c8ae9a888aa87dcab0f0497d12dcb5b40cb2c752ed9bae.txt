-- Separate publication lifecycle; original producer snapshots and Review chains are unchanged.
CREATE TABLE draft_publications(
 id TEXT PRIMARY KEY NOT NULL,
 workspace_id TEXT NOT NULL,
 draft_id TEXT NOT NULL,
 draft_revision INTEGER NOT NULL CHECK(typeof(draft_revision)='integer' AND draft_revision>=1),
 owner TEXT NOT NULL CHECK(owner='import'),
 entity TEXT NOT NULL CHECK(entity='block'),
 candidate_sha256 TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('draft','in_review','approved','published')),
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision BETWEEN 1 AND 4),
 adopted_at TEXT NOT NULL,
 FOREIGN KEY(workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256)
  REFERENCES draft_candidate_revisions(workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256),
 UNIQUE(workspace_id,draft_id,draft_revision)
);
CREATE TABLE draft_publication_events(
 publication_id TEXT NOT NULL REFERENCES draft_publications(id),
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision BETWEEN 1 AND 4),
 event_json TEXT NOT NULL CHECK(json_valid(event_json)),
 sha256 TEXT NOT NULL CHECK(length(sha256)=64),
 PRIMARY KEY(publication_id,revision)
);
CREATE TABLE draft_publication_results(
 publication_id TEXT PRIMARY KEY NOT NULL REFERENCES draft_publications(id),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 sha256 TEXT NOT NULL CHECK(length(sha256)=64)
);
CREATE TABLE draft_publication_commands(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 actor_id TEXT NOT NULL REFERENCES local_sessions(id),
 route TEXT NOT NULL,
 command_key TEXT NOT NULL,
 publication_id TEXT NOT NULL UNIQUE REFERENCES draft_publication_results(publication_id),
 PRIMARY KEY(workspace_id,actor_id,route,command_key)
);
CREATE TRIGGER draft_publication_initial BEFORE INSERT ON draft_publications
 WHEN NEW.state<>'draft' OR NEW.revision<>1
 BEGIN SELECT RAISE(ABORT,'publication must start at current adoption'); END;
CREATE TRIGGER draft_publication_transition BEFORE UPDATE ON draft_publications
 WHEN OLD.id<>NEW.id OR OLD.workspace_id<>NEW.workspace_id OR OLD.draft_id<>NEW.draft_id
 OR OLD.draft_revision<>NEW.draft_revision OR OLD.owner<>NEW.owner OR OLD.entity<>NEW.entity
 OR OLD.candidate_sha256<>NEW.candidate_sha256 OR OLD.adopted_at<>NEW.adopted_at
 OR NEW.revision<>OLD.revision+1
 OR NOT ((OLD.state='draft' AND NEW.state='in_review') OR (OLD.state='in_review' AND NEW.state='approved')
 OR (OLD.state='approved' AND NEW.state='published'))
 BEGIN SELECT RAISE(ABORT,'immutable identity or invalid publication transition'); END;
CREATE TRIGGER draft_publications_no_delete BEFORE DELETE ON draft_publications
 BEGIN SELECT RAISE(ABORT,'publication history immutable'); END;
CREATE TRIGGER draft_publication_events_no_update BEFORE UPDATE ON draft_publication_events
 BEGIN SELECT RAISE(ABORT,'publication events immutable'); END;
CREATE TRIGGER draft_publication_events_no_delete BEFORE DELETE ON draft_publication_events
 BEGIN SELECT RAISE(ABORT,'publication events immutable'); END;
CREATE TRIGGER draft_publication_results_no_update BEFORE UPDATE ON draft_publication_results
 BEGIN SELECT RAISE(ABORT,'publication result immutable'); END;
CREATE TRIGGER draft_publication_results_no_delete BEFORE DELETE ON draft_publication_results
 BEGIN SELECT RAISE(ABORT,'publication result immutable'); END;
CREATE TRIGGER draft_publication_commands_no_update BEFORE UPDATE ON draft_publication_commands
 BEGIN SELECT RAISE(ABORT,'publication command immutable'); END;
CREATE TRIGGER draft_publication_commands_no_delete BEFORE DELETE ON draft_publication_commands
 BEGIN SELECT RAISE(ABORT,'publication command immutable'); END;
