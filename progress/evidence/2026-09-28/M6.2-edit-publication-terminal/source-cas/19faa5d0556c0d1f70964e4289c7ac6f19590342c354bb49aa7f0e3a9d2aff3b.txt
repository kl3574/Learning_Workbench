-- Edit publications share the existing real lifecycle; preserve all original Import rows.

CREATE TEMP TABLE edit_publication_saved_draft_publications AS SELECT rowid AS saved_rowid,* FROM draft_publications;

CREATE TEMP TABLE edit_publication_saved_draft_publication_events AS SELECT rowid AS saved_rowid,* FROM draft_publication_events;

CREATE TEMP TABLE edit_publication_saved_draft_publication_results AS SELECT rowid AS saved_rowid,* FROM draft_publication_results;

CREATE TEMP TABLE edit_publication_saved_draft_publication_commands AS SELECT rowid AS saved_rowid,* FROM draft_publication_commands;

DROP TRIGGER draft_publication_initial;

DROP TRIGGER draft_publication_transition;

DROP TRIGGER draft_publications_no_delete;

DROP TRIGGER draft_publication_events_no_update;

DROP TRIGGER draft_publication_events_no_delete;

DROP TRIGGER draft_publication_results_no_update;

DROP TRIGGER draft_publication_results_no_delete;

DROP TRIGGER draft_publication_commands_no_update;

DROP TRIGGER draft_publication_commands_no_delete;

DROP TABLE draft_publication_commands;

DROP TABLE draft_publication_events;

DROP TABLE draft_publication_results;

DROP TABLE draft_publications;

-- Separate publication lifecycle; original producer snapshots and Review chains are unchanged.
CREATE TABLE draft_publications(
 id TEXT PRIMARY KEY NOT NULL,
 workspace_id TEXT NOT NULL,
 draft_id TEXT NOT NULL,
 draft_revision INTEGER NOT NULL CHECK(typeof(draft_revision)='integer' AND draft_revision>=1),
 owner TEXT NOT NULL CHECK(owner IN ('import','authoring')),
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

INSERT INTO draft_publications(rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at) SELECT * FROM edit_publication_saved_draft_publications;

INSERT INTO draft_publication_events(rowid,publication_id,revision,event_json,sha256) SELECT * FROM edit_publication_saved_draft_publication_events;

INSERT INTO draft_publication_results(rowid,publication_id,record_json,sha256) SELECT * FROM edit_publication_saved_draft_publication_results;

INSERT INTO draft_publication_commands(rowid,workspace_id,actor_id,route,command_key,publication_id) SELECT * FROM edit_publication_saved_draft_publication_commands;

CREATE TEMP TABLE edit_publication_copy_check(ok INTEGER NOT NULL CHECK(ok=1));

INSERT INTO edit_publication_copy_check SELECT NOT EXISTS(SELECT rowid,* FROM draft_publications EXCEPT SELECT * FROM edit_publication_saved_draft_publications) AND NOT EXISTS(SELECT * FROM edit_publication_saved_draft_publications EXCEPT SELECT rowid,* FROM draft_publications);

DROP TABLE edit_publication_saved_draft_publications;

INSERT INTO edit_publication_copy_check SELECT NOT EXISTS(SELECT rowid,* FROM draft_publication_events EXCEPT SELECT * FROM edit_publication_saved_draft_publication_events) AND NOT EXISTS(SELECT * FROM edit_publication_saved_draft_publication_events EXCEPT SELECT rowid,* FROM draft_publication_events);

DROP TABLE edit_publication_saved_draft_publication_events;

INSERT INTO edit_publication_copy_check SELECT NOT EXISTS(SELECT rowid,* FROM draft_publication_results EXCEPT SELECT * FROM edit_publication_saved_draft_publication_results) AND NOT EXISTS(SELECT * FROM edit_publication_saved_draft_publication_results EXCEPT SELECT rowid,* FROM draft_publication_results);

DROP TABLE edit_publication_saved_draft_publication_results;

INSERT INTO edit_publication_copy_check SELECT NOT EXISTS(SELECT rowid,* FROM draft_publication_commands EXCEPT SELECT * FROM edit_publication_saved_draft_publication_commands) AND NOT EXISTS(SELECT * FROM edit_publication_saved_draft_publication_commands EXCEPT SELECT rowid,* FROM draft_publication_commands);

DROP TABLE edit_publication_saved_draft_publication_commands;

DROP TABLE edit_publication_copy_check;
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
