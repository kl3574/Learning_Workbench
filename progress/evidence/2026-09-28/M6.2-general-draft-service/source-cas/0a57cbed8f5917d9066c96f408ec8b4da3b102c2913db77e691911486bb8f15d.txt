-- Authoring edit owner; preserve all historical bytes with FK enforcement enabled.

-- No original migration or producer records are changed.

CREATE TEMP TABLE edit_saved_draft_candidate_identities AS SELECT rowid AS saved_rowid,draft_id,workspace_id,owner,source_kind,entity FROM draft_candidate_identities;

CREATE TEMP TABLE edit_saved_draft_candidate_revisions AS SELECT rowid AS saved_rowid,draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256 FROM draft_candidate_revisions;

CREATE TEMP TABLE edit_saved_reviews AS SELECT rowid AS saved_rowid,id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity FROM reviews;

CREATE TEMP TABLE edit_saved_review_jobs AS SELECT rowid AS saved_rowid,review_id,workspace_id,job_kind,owner,source_kind,draft_id,draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at FROM review_jobs;

CREATE TEMP TABLE edit_saved_review_revisions AS SELECT rowid AS saved_rowid,review_id,revision,receipt_json,receipt_sha256,record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at FROM review_revisions;

CREATE TEMP TABLE edit_saved_review_artifact_bindings AS SELECT rowid AS saved_rowid,review_id,workspace_id,review_revision,ordinal,artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256 FROM review_artifact_bindings;

CREATE TEMP TABLE edit_saved_review_commands AS SELECT rowid AS saved_rowid,workspace_id,actor_id,route,command_key,command_kind,review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at FROM review_commands;

CREATE TEMP TABLE edit_saved_draft_publications AS SELECT rowid AS saved_rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at FROM draft_publications;

CREATE TEMP TABLE edit_saved_draft_publication_events AS SELECT rowid AS saved_rowid,publication_id,revision,event_json,sha256 FROM draft_publication_events;

CREATE TEMP TABLE edit_saved_draft_publication_results AS SELECT rowid AS saved_rowid,publication_id,record_json,sha256 FROM draft_publication_results;

CREATE TEMP TABLE edit_saved_draft_publication_commands AS SELECT rowid AS saved_rowid,workspace_id,actor_id,route,command_key,publication_id FROM draft_publication_commands;

DROP TRIGGER draft_candidate_identities_no_replace;

DROP TRIGGER draft_candidate_identities_no_update;

DROP TRIGGER draft_candidate_identities_no_delete;

DROP TRIGGER draft_candidate_revisions_no_replace;

DROP TRIGGER draft_candidate_revisions_no_update;

DROP TRIGGER draft_candidate_revisions_no_delete;

DROP TRIGGER review_revision_candidate;

DROP TRIGGER review_command_binding;

DROP TRIGGER review_jobs_no_replace;

DROP TRIGGER review_jobs_no_update;

DROP TRIGGER review_jobs_no_delete;

DROP TRIGGER review_revisions_no_replace;

DROP TRIGGER review_revisions_no_update;

DROP TRIGGER review_revisions_no_delete;

DROP TRIGGER review_artifacts_no_replace;

DROP TRIGGER review_artifacts_no_update;

DROP TRIGGER review_artifacts_no_delete;

DROP TRIGGER review_commands_no_replace;

DROP TRIGGER review_commands_no_update;

DROP TRIGGER review_commands_no_delete;

DROP TRIGGER draft_publication_initial;

DROP TRIGGER draft_publication_transition;

DROP TRIGGER draft_publications_no_delete;

DROP TRIGGER draft_publication_events_no_update;

DROP TRIGGER draft_publication_events_no_delete;

DROP TRIGGER draft_publication_results_no_update;

DROP TRIGGER draft_publication_results_no_delete;

DROP TRIGGER draft_publication_commands_no_update;

DROP TRIGGER draft_publication_commands_no_delete;

DROP TABLE review_commands;

DROP TABLE review_artifact_bindings;

DROP TABLE review_revisions;

DROP TABLE draft_publication_commands;

DROP TABLE draft_publication_events;

DROP TABLE draft_publication_results;

DROP TABLE draft_publications;

DROP TABLE reviews;

DROP TABLE review_jobs;

DROP TABLE draft_candidate_revisions;

DROP TABLE draft_candidate_identities;

CREATE TABLE draft_candidate_identities(
 draft_id TEXT PRIMARY KEY NOT NULL CHECK(length(draft_id) BETWEEN 1 AND 80 AND substr(draft_id,1,1) GLOB '[A-Za-z]' AND draft_id NOT GLOB '*[^A-Za-z0-9_-]*'),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 owner TEXT NOT NULL CHECK(owner IN ('import','authoring')),
 source_kind TEXT NOT NULL CHECK(source_kind IN ('import','authoring_single','authoring_group','authoring_edit')),
 entity TEXT NOT NULL CHECK(entity IN ('course','lesson','block','concept','route','question','practice_set','assessment','note')),
 CHECK((owner='import' AND source_kind='import') OR (owner='authoring' AND source_kind IN ('authoring_single','authoring_group','authoring_edit'))),
 CHECK(source_kind NOT IN ('authoring_single','authoring_edit') OR entity='block'),
 CHECK(source_kind<>'authoring_group' OR entity IN ('lesson','practice_set','assessment')),
 UNIQUE(draft_id,workspace_id,owner,entity)
);

CREATE TABLE draft_candidate_revisions(
 draft_id TEXT NOT NULL,
 workspace_id TEXT NOT NULL,
 owner TEXT NOT NULL,
 entity TEXT NOT NULL,
 draft_revision INTEGER NOT NULL CHECK(typeof(draft_revision)='integer' AND draft_revision>=1),
 candidate_sha256 TEXT NOT NULL CHECK(length(candidate_sha256)=64 AND candidate_sha256 NOT GLOB '*[^a-f0-9]*'),
 PRIMARY KEY(draft_id,draft_revision),
 FOREIGN KEY(draft_id,workspace_id,owner,entity) REFERENCES draft_candidate_identities(draft_id,workspace_id,owner,entity),
 UNIQUE(workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256)
);

CREATE TABLE reviews(
 id TEXT PRIMARY KEY NOT NULL,
 draft_id TEXT NOT NULL,
 draft_revision INTEGER NOT NULL CHECK(typeof(draft_revision)='integer' AND draft_revision>=1),
 candidate_sha256 TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision>=1),
 receipt_json TEXT NOT NULL CHECK(json_valid(receipt_json)),
 reviewer_session_id TEXT REFERENCES local_sessions(id),
 created_at TEXT NOT NULL,
 workspace_id TEXT NOT NULL,
 owner TEXT NOT NULL,
 entity TEXT NOT NULL,
 FOREIGN KEY(workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256)
  REFERENCES draft_candidate_revisions(workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256)
);

CREATE TABLE review_jobs(
 review_id TEXT PRIMARY KEY NOT NULL,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 job_kind TEXT NOT NULL DEFAULT 'draft_review' CHECK(job_kind='draft_review'),
 owner TEXT NOT NULL CHECK(owner IN ('import','authoring')),
 source_kind TEXT NOT NULL CHECK(source_kind IN ('import','authoring_single','authoring_group','authoring_edit')),
 draft_id TEXT NOT NULL,
 draft_revision INTEGER NOT NULL CHECK(typeof(draft_revision)='integer' AND draft_revision>=1),
 entity TEXT NOT NULL,
 candidate_sha256 TEXT NOT NULL CHECK(length(candidate_sha256)=64 AND candidate_sha256 NOT GLOB '*[^a-f0-9]*'),
 creator_actor_id TEXT NOT NULL CHECK(length(creator_actor_id)>0),
 input_json TEXT NOT NULL CHECK(json_valid(input_json)),
 input_sha256 TEXT NOT NULL CHECK(length(input_sha256)=64 AND input_sha256 NOT GLOB '*[^a-f0-9]*'),
 created_at TEXT NOT NULL,
 UNIQUE(review_id,workspace_id),
 FOREIGN KEY(review_id,workspace_id,job_kind) REFERENCES jobs(id,workspace_id,kind),
 FOREIGN KEY(draft_id,workspace_id,owner,source_kind,entity)
  REFERENCES draft_candidate_identities(draft_id,workspace_id,owner,source_kind,entity),
 FOREIGN KEY(workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256)
  REFERENCES draft_candidate_revisions(workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256)
);

CREATE TABLE review_revisions(
 review_id TEXT NOT NULL REFERENCES reviews(id),
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
 receipt_json TEXT NOT NULL CHECK(json_valid(receipt_json)),
 receipt_sha256 TEXT NOT NULL CHECK(length(receipt_sha256)=64 AND receipt_sha256 NOT GLOB '*[^a-f0-9]*'),
 record_kind TEXT NOT NULL CHECK(record_kind IN ('machine','human_decision')),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64 AND record_sha256 NOT GLOB '*[^a-f0-9]*'),
 previous_receipt_sha256 TEXT CHECK(previous_receipt_sha256 IS NULL OR
  (length(previous_receipt_sha256)=64 AND previous_receipt_sha256 NOT GLOB '*[^a-f0-9]*')),
 previous_revision INTEGER GENERATED ALWAYS AS (CASE WHEN revision>1 THEN revision-1 END) VIRTUAL,
 recorded_at TEXT NOT NULL,
 PRIMARY KEY(review_id,revision),
 UNIQUE(review_id,revision,receipt_sha256),
 FOREIGN KEY(review_id) REFERENCES review_jobs(review_id),
 FOREIGN KEY(review_id,previous_revision,previous_receipt_sha256)
  REFERENCES review_revisions(review_id,revision,receipt_sha256),
 CHECK((revision=1 AND record_kind='machine' AND previous_receipt_sha256 IS NULL)
    OR (revision>1 AND record_kind='human_decision' AND previous_receipt_sha256 IS NOT NULL))
);

CREATE TABLE review_artifact_bindings(
 review_id TEXT NOT NULL,
 workspace_id TEXT NOT NULL,
 review_revision INTEGER NOT NULL CHECK(typeof(review_revision)='integer' AND review_revision>=1),
 ordinal INTEGER NOT NULL CHECK(typeof(ordinal)='integer' AND ordinal>=0),
 artifact_id TEXT NOT NULL,
 artifact_owner TEXT NOT NULL CHECK(artifact_owner IN ('import','quality')),
 artifact_sha256 TEXT NOT NULL CHECK(length(artifact_sha256)=64 AND artifact_sha256 NOT GLOB '*[^a-f0-9]*'),
 manifest_sha256 TEXT NOT NULL CHECK(length(manifest_sha256)=64 AND manifest_sha256 NOT GLOB '*[^a-f0-9]*'),
 binding_json TEXT NOT NULL CHECK(json_valid(binding_json)),
 binding_sha256 TEXT NOT NULL CHECK(length(binding_sha256)=64 AND binding_sha256 NOT GLOB '*[^a-f0-9]*'),
 PRIMARY KEY(review_id,review_revision,ordinal),
 UNIQUE(review_id,review_revision,artifact_id),
 FOREIGN KEY(review_id,workspace_id) REFERENCES review_jobs(review_id,workspace_id),
 FOREIGN KEY(review_id,review_revision) REFERENCES review_revisions(review_id,revision),
 FOREIGN KEY(artifact_id,workspace_id,artifact_sha256) REFERENCES artifacts(id,workspace_id,blob_sha256)
);

CREATE TABLE review_commands(
 workspace_id TEXT NOT NULL,
 actor_id TEXT NOT NULL CHECK(length(actor_id)>0),
 route TEXT NOT NULL,
 command_key TEXT NOT NULL CHECK(length(command_key)>0),
 command_kind TEXT NOT NULL CHECK(command_kind IN ('create','decision','cancel')),
 review_id TEXT NOT NULL,
 request_json TEXT NOT NULL CHECK(json_valid(request_json)),
 request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64 AND request_sha256 NOT GLOB '*[^a-f0-9]*'),
 ack_json TEXT NOT NULL CHECK(json_valid(ack_json)),
 ack_sha256 TEXT NOT NULL CHECK(length(ack_sha256)=64 AND ack_sha256 NOT GLOB '*[^a-f0-9]*'),
 basis_revision INTEGER NOT NULL CHECK(typeof(basis_revision)='integer' AND basis_revision>=1),
 resulting_revision INTEGER NOT NULL CHECK(typeof(resulting_revision)='integer' AND resulting_revision>=1),
 job_basis_revision INTEGER GENERATED ALWAYS AS
  (CASE WHEN command_kind='cancel' THEN basis_revision END) VIRTUAL,
 job_resulting_revision INTEGER GENERATED ALWAYS AS
  (CASE WHEN command_kind IN ('create','cancel') THEN resulting_revision END) VIRTUAL,
 review_basis_revision INTEGER GENERATED ALWAYS AS
  (CASE WHEN command_kind='decision' THEN basis_revision END) VIRTUAL,
 review_resulting_revision INTEGER GENERATED ALWAYS AS
  (CASE WHEN command_kind='decision' THEN resulting_revision END) VIRTUAL,
 recorded_at TEXT NOT NULL,
 PRIMARY KEY(workspace_id,actor_id,route,command_key),
 FOREIGN KEY(review_id,workspace_id) REFERENCES review_jobs(review_id,workspace_id),
 FOREIGN KEY(review_id,job_basis_revision) REFERENCES job_events(job_id,seq),
 FOREIGN KEY(review_id,job_resulting_revision) REFERENCES job_events(job_id,seq),
 FOREIGN KEY(review_id,review_basis_revision) REFERENCES review_revisions(review_id,revision),
 FOREIGN KEY(review_id,review_resulting_revision) REFERENCES review_revisions(review_id,revision),
 CHECK((command_kind='create' AND resulting_revision=1)
    OR (command_kind='decision' AND resulting_revision=basis_revision+1)
    OR (command_kind='cancel' AND resulting_revision IN (basis_revision,basis_revision+1)))
);

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

CREATE UNIQUE INDEX review_candidate_source ON draft_candidate_identities(draft_id,workspace_id,owner,source_kind,entity);

-- EDIT_SCHEMA_REBUILT

INSERT INTO draft_candidate_identities(rowid,draft_id,workspace_id,owner,source_kind,entity) SELECT saved_rowid,draft_id,workspace_id,owner,source_kind,entity FROM edit_saved_draft_candidate_identities;

INSERT INTO draft_candidate_revisions(rowid,draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256) SELECT saved_rowid,draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256 FROM edit_saved_draft_candidate_revisions;

INSERT INTO reviews(rowid,id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity) SELECT saved_rowid,id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity FROM edit_saved_reviews;

INSERT INTO review_jobs(rowid,review_id,workspace_id,job_kind,owner,source_kind,draft_id,draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at) SELECT saved_rowid,review_id,workspace_id,job_kind,owner,source_kind,draft_id,draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at FROM edit_saved_review_jobs;

INSERT INTO review_revisions(rowid,review_id,revision,receipt_json,receipt_sha256,record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at) SELECT saved_rowid,review_id,revision,receipt_json,receipt_sha256,record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at FROM edit_saved_review_revisions ORDER BY review_id,revision;

INSERT INTO review_artifact_bindings(rowid,review_id,workspace_id,review_revision,ordinal,artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256) SELECT saved_rowid,review_id,workspace_id,review_revision,ordinal,artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256 FROM edit_saved_review_artifact_bindings;

INSERT INTO review_commands(rowid,workspace_id,actor_id,route,command_key,command_kind,review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at) SELECT saved_rowid,workspace_id,actor_id,route,command_key,command_kind,review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at FROM edit_saved_review_commands;

INSERT INTO draft_publications(rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at) SELECT saved_rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at FROM edit_saved_draft_publications;

INSERT INTO draft_publication_events(rowid,publication_id,revision,event_json,sha256) SELECT saved_rowid,publication_id,revision,event_json,sha256 FROM edit_saved_draft_publication_events;

INSERT INTO draft_publication_results(rowid,publication_id,record_json,sha256) SELECT saved_rowid,publication_id,record_json,sha256 FROM edit_saved_draft_publication_results;

INSERT INTO draft_publication_commands(rowid,workspace_id,actor_id,route,command_key,publication_id) SELECT saved_rowid,workspace_id,actor_id,route,command_key,publication_id FROM edit_saved_draft_publication_commands;

-- EDIT_HISTORY_RESTORED

CREATE TRIGGER draft_candidate_identities_no_replace BEFORE INSERT ON draft_candidate_identities
 WHEN EXISTS(SELECT 1 FROM draft_candidate_identities WHERE draft_id=NEW.draft_id)
 BEGIN SELECT RAISE(ABORT,'draft candidate identity immutable'); END;

CREATE TRIGGER draft_candidate_identities_no_update BEFORE UPDATE ON draft_candidate_identities
 BEGIN SELECT RAISE(ABORT,'draft candidate identity immutable'); END;

CREATE TRIGGER draft_candidate_identities_no_delete BEFORE DELETE ON draft_candidate_identities
 BEGIN SELECT RAISE(ABORT,'draft candidate identity immutable'); END;

CREATE TRIGGER draft_candidate_revisions_no_replace BEFORE INSERT ON draft_candidate_revisions
 WHEN EXISTS(SELECT 1 FROM draft_candidate_revisions WHERE draft_id=NEW.draft_id AND draft_revision=NEW.draft_revision)
 BEGIN SELECT RAISE(ABORT,'draft candidate revision immutable'); END;

CREATE TRIGGER draft_candidate_revisions_no_update BEFORE UPDATE ON draft_candidate_revisions
 BEGIN SELECT RAISE(ABORT,'draft candidate revision immutable'); END;

CREATE TRIGGER draft_candidate_revisions_no_delete BEFORE DELETE ON draft_candidate_revisions
 BEGIN SELECT RAISE(ABORT,'draft candidate revision immutable'); END;

CREATE TRIGGER review_revision_candidate BEFORE INSERT ON review_revisions
WHEN NOT EXISTS(
 SELECT 1 FROM reviews r JOIN review_jobs j ON r.id=j.review_id
 WHERE r.id=NEW.review_id AND r.workspace_id=j.workspace_id
  AND r.draft_id=j.draft_id AND r.draft_revision=j.draft_revision
  AND r.owner=j.owner AND r.entity=j.entity AND r.candidate_sha256=j.candidate_sha256
)
BEGIN SELECT RAISE(ABORT,'review projection candidate mismatch'); END;

CREATE TRIGGER review_command_binding BEFORE INSERT ON review_commands
WHEN NOT EXISTS(
 SELECT 1 FROM review_jobs j WHERE j.review_id=NEW.review_id AND j.workspace_id=NEW.workspace_id
 AND ((NEW.command_kind='create' AND NEW.route='POST /drafts/'||j.draft_id||'/review'
       AND NEW.actor_id=j.creator_actor_id AND NEW.basis_revision=j.draft_revision)
   OR (NEW.command_kind='decision' AND NEW.route='POST /reviews/'||j.review_id||'/decision'
       AND EXISTS(SELECT 1 FROM review_revisions r WHERE r.review_id=j.review_id
        AND r.revision=NEW.resulting_revision AND r.previous_revision=NEW.basis_revision
        AND r.record_kind='human_decision'))
   OR (NEW.command_kind='cancel' AND NEW.route='POST /jobs/'||j.review_id||'/cancel'))
)
BEGIN SELECT RAISE(ABORT,'review command binding mismatch'); END;

CREATE TRIGGER review_jobs_no_replace BEFORE INSERT ON review_jobs
WHEN EXISTS(SELECT 1 FROM review_jobs WHERE review_id=NEW.review_id)
BEGIN SELECT RAISE(ABORT,'review jobs append-only'); END;

CREATE TRIGGER review_jobs_no_update BEFORE UPDATE ON review_jobs
BEGIN SELECT RAISE(ABORT,'review jobs append-only'); END;

CREATE TRIGGER review_jobs_no_delete BEFORE DELETE ON review_jobs
BEGIN SELECT RAISE(ABORT,'review jobs append-only'); END;

CREATE TRIGGER review_revisions_no_replace BEFORE INSERT ON review_revisions
WHEN EXISTS(SELECT 1 FROM review_revisions WHERE review_id=NEW.review_id AND revision=NEW.revision)
BEGIN SELECT RAISE(ABORT,'review revisions append-only'); END;

CREATE TRIGGER review_revisions_no_update BEFORE UPDATE ON review_revisions
BEGIN SELECT RAISE(ABORT,'review revisions append-only'); END;

CREATE TRIGGER review_revisions_no_delete BEFORE DELETE ON review_revisions
BEGIN SELECT RAISE(ABORT,'review revisions append-only'); END;

CREATE TRIGGER review_artifacts_no_replace BEFORE INSERT ON review_artifact_bindings
WHEN EXISTS(SELECT 1 FROM review_artifact_bindings WHERE review_id=NEW.review_id
 AND review_revision=NEW.review_revision AND (ordinal=NEW.ordinal OR artifact_id=NEW.artifact_id))
BEGIN SELECT RAISE(ABORT,'review artifacts append-only'); END;

CREATE TRIGGER review_artifacts_no_update BEFORE UPDATE ON review_artifact_bindings
BEGIN SELECT RAISE(ABORT,'review artifacts append-only'); END;

CREATE TRIGGER review_artifacts_no_delete BEFORE DELETE ON review_artifact_bindings
BEGIN SELECT RAISE(ABORT,'review artifacts append-only'); END;

CREATE TRIGGER review_commands_no_replace BEFORE INSERT ON review_commands
WHEN EXISTS(SELECT 1 FROM review_commands WHERE workspace_id=NEW.workspace_id
 AND actor_id=NEW.actor_id AND route=NEW.route AND command_key=NEW.command_key)
BEGIN SELECT RAISE(ABORT,'review commands append-only'); END;

CREATE TRIGGER review_commands_no_update BEFORE UPDATE ON review_commands
BEGIN SELECT RAISE(ABORT,'review commands append-only'); END;

CREATE TRIGGER review_commands_no_delete BEFORE DELETE ON review_commands
BEGIN SELECT RAISE(ABORT,'review commands append-only'); END;

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

CREATE TEMP TABLE edit_migration_guard(ok INTEGER NOT NULL CHECK(ok=1));

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,draft_id,workspace_id,owner,source_kind,entity FROM edit_saved_draft_candidate_identities EXCEPT SELECT rowid,draft_id,workspace_id,owner,source_kind,entity FROM draft_candidate_identities) AND NOT EXISTS(SELECT rowid,draft_id,workspace_id,owner,source_kind,entity FROM draft_candidate_identities EXCEPT SELECT saved_rowid,draft_id,workspace_id,owner,source_kind,entity FROM edit_saved_draft_candidate_identities);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256 FROM edit_saved_draft_candidate_revisions EXCEPT SELECT rowid,draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256 FROM draft_candidate_revisions) AND NOT EXISTS(SELECT rowid,draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256 FROM draft_candidate_revisions EXCEPT SELECT saved_rowid,draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256 FROM edit_saved_draft_candidate_revisions);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity FROM edit_saved_reviews EXCEPT SELECT rowid,id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity FROM reviews) AND NOT EXISTS(SELECT rowid,id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity FROM reviews EXCEPT SELECT saved_rowid,id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity FROM edit_saved_reviews);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,review_id,workspace_id,job_kind,owner,source_kind,draft_id,draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at FROM edit_saved_review_jobs EXCEPT SELECT rowid,review_id,workspace_id,job_kind,owner,source_kind,draft_id,draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at FROM review_jobs) AND NOT EXISTS(SELECT rowid,review_id,workspace_id,job_kind,owner,source_kind,draft_id,draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at FROM review_jobs EXCEPT SELECT saved_rowid,review_id,workspace_id,job_kind,owner,source_kind,draft_id,draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at FROM edit_saved_review_jobs);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,review_id,revision,receipt_json,receipt_sha256,record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at FROM edit_saved_review_revisions EXCEPT SELECT rowid,review_id,revision,receipt_json,receipt_sha256,record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at FROM review_revisions) AND NOT EXISTS(SELECT rowid,review_id,revision,receipt_json,receipt_sha256,record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at FROM review_revisions EXCEPT SELECT saved_rowid,review_id,revision,receipt_json,receipt_sha256,record_kind,record_json,record_sha256,previous_receipt_sha256,recorded_at FROM edit_saved_review_revisions);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,review_id,workspace_id,review_revision,ordinal,artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256 FROM edit_saved_review_artifact_bindings EXCEPT SELECT rowid,review_id,workspace_id,review_revision,ordinal,artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256 FROM review_artifact_bindings) AND NOT EXISTS(SELECT rowid,review_id,workspace_id,review_revision,ordinal,artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256 FROM review_artifact_bindings EXCEPT SELECT saved_rowid,review_id,workspace_id,review_revision,ordinal,artifact_id,artifact_owner,artifact_sha256,manifest_sha256,binding_json,binding_sha256 FROM edit_saved_review_artifact_bindings);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,workspace_id,actor_id,route,command_key,command_kind,review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at FROM edit_saved_review_commands EXCEPT SELECT rowid,workspace_id,actor_id,route,command_key,command_kind,review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at FROM review_commands) AND NOT EXISTS(SELECT rowid,workspace_id,actor_id,route,command_key,command_kind,review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at FROM review_commands EXCEPT SELECT saved_rowid,workspace_id,actor_id,route,command_key,command_kind,review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at FROM edit_saved_review_commands);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at FROM edit_saved_draft_publications EXCEPT SELECT rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at FROM draft_publications) AND NOT EXISTS(SELECT rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at FROM draft_publications EXCEPT SELECT saved_rowid,id,workspace_id,draft_id,draft_revision,owner,entity,candidate_sha256,state,revision,adopted_at FROM edit_saved_draft_publications);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,publication_id,revision,event_json,sha256 FROM edit_saved_draft_publication_events EXCEPT SELECT rowid,publication_id,revision,event_json,sha256 FROM draft_publication_events) AND NOT EXISTS(SELECT rowid,publication_id,revision,event_json,sha256 FROM draft_publication_events EXCEPT SELECT saved_rowid,publication_id,revision,event_json,sha256 FROM edit_saved_draft_publication_events);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,publication_id,record_json,sha256 FROM edit_saved_draft_publication_results EXCEPT SELECT rowid,publication_id,record_json,sha256 FROM draft_publication_results) AND NOT EXISTS(SELECT rowid,publication_id,record_json,sha256 FROM draft_publication_results EXCEPT SELECT saved_rowid,publication_id,record_json,sha256 FROM edit_saved_draft_publication_results);

INSERT INTO edit_migration_guard SELECT NOT EXISTS(SELECT saved_rowid,workspace_id,actor_id,route,command_key,publication_id FROM edit_saved_draft_publication_commands EXCEPT SELECT rowid,workspace_id,actor_id,route,command_key,publication_id FROM draft_publication_commands) AND NOT EXISTS(SELECT rowid,workspace_id,actor_id,route,command_key,publication_id FROM draft_publication_commands EXCEPT SELECT saved_rowid,workspace_id,actor_id,route,command_key,publication_id FROM edit_saved_draft_publication_commands);

DROP TABLE edit_migration_guard;

DROP TABLE edit_saved_draft_candidate_identities;

DROP TABLE edit_saved_draft_candidate_revisions;

DROP TABLE edit_saved_reviews;

DROP TABLE edit_saved_review_jobs;

DROP TABLE edit_saved_review_revisions;

DROP TABLE edit_saved_review_artifact_bindings;

DROP TABLE edit_saved_review_commands;

DROP TABLE edit_saved_draft_publications;

DROP TABLE edit_saved_draft_publication_events;

DROP TABLE edit_saved_draft_publication_results;

DROP TABLE edit_saved_draft_publication_commands;

CREATE TABLE draft_edits(
 draft_id TEXT PRIMARY KEY NOT NULL,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 kind TEXT NOT NULL CHECK(kind='block'),
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
 base_ref_json TEXT NOT NULL CHECK(json_valid(base_ref_json)),
 created_at TEXT NOT NULL,
 UNIQUE(draft_id,workspace_id)
);
CREATE TABLE draft_edit_versions(
 draft_id TEXT NOT NULL,
 workspace_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>=1),
 candidate_sha256 TEXT NOT NULL CHECK(length(candidate_sha256)=64),
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 parent_sha256 TEXT,
 previous_revision INTEGER GENERATED ALWAYS AS (CASE WHEN revision>1 THEN revision-1 END) VIRTUAL,
 created_at TEXT NOT NULL,
 PRIMARY KEY(draft_id,revision),
 UNIQUE(draft_id,revision,record_sha256),
 FOREIGN KEY(draft_id,workspace_id) REFERENCES draft_edits(draft_id,workspace_id),
 FOREIGN KEY(draft_id,previous_revision,parent_sha256) REFERENCES draft_edit_versions(draft_id,revision,record_sha256),
 CHECK((revision=1 AND parent_sha256 IS NULL) OR (revision>1 AND length(parent_sha256)=64))
);
CREATE TABLE draft_edit_commands(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 actor_id TEXT NOT NULL,
 route TEXT NOT NULL,
 command_key TEXT NOT NULL,
 draft_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 record_json TEXT NOT NULL CHECK(json_valid(record_json)),
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64),
 PRIMARY KEY(workspace_id,actor_id,route,command_key),
 FOREIGN KEY(draft_id,revision) REFERENCES draft_edit_versions(draft_id,revision)
);
CREATE TRIGGER draft_edit_head_initial BEFORE INSERT ON draft_edits
 WHEN NEW.revision<>1 OR EXISTS(SELECT 1 FROM draft_edits WHERE draft_id=NEW.draft_id)
 BEGIN SELECT RAISE(ABORT,'invalid initial edit'); END;
CREATE TRIGGER draft_edit_head_transition BEFORE UPDATE ON draft_edits
 WHEN NEW.draft_id<>OLD.draft_id OR NEW.workspace_id<>OLD.workspace_id OR NEW.kind<>OLD.kind
 OR NEW.base_ref_json<>OLD.base_ref_json OR NEW.created_at<>OLD.created_at OR NEW.revision<>OLD.revision+1
 BEGIN SELECT RAISE(ABORT,'invalid edit head change'); END;
CREATE TRIGGER draft_edit_head_no_delete BEFORE DELETE ON draft_edits
 BEGIN SELECT RAISE(ABORT,'edit history immutable'); END;
CREATE TRIGGER draft_edit_version_no_replace BEFORE INSERT ON draft_edit_versions
 WHEN EXISTS(SELECT 1 FROM draft_edit_versions WHERE draft_id=NEW.draft_id AND revision=NEW.revision)
 BEGIN SELECT RAISE(ABORT,'edit version immutable'); END;
CREATE TRIGGER draft_edit_version_no_update BEFORE UPDATE ON draft_edit_versions
 BEGIN SELECT RAISE(ABORT,'edit version immutable'); END;
CREATE TRIGGER draft_edit_version_no_delete BEFORE DELETE ON draft_edit_versions
 BEGIN SELECT RAISE(ABORT,'edit version immutable'); END;
CREATE TRIGGER draft_edit_command_no_replace BEFORE INSERT ON draft_edit_commands
 WHEN EXISTS(SELECT 1 FROM draft_edit_commands WHERE workspace_id=NEW.workspace_id AND actor_id=NEW.actor_id AND route=NEW.route AND command_key=NEW.command_key)
 BEGIN SELECT RAISE(ABORT,'edit command immutable'); END;
CREATE TRIGGER draft_edit_command_no_update BEFORE UPDATE ON draft_edit_commands
 BEGIN SELECT RAISE(ABORT,'edit command immutable'); END;
CREATE TRIGGER draft_edit_command_no_delete BEFORE DELETE ON draft_edit_commands
 BEGIN SELECT RAISE(ABORT,'edit command immutable'); END;
