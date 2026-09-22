-- Identity catalog only: no review decision, owner authentication or publication.
-- Existing owner payloads stay in their own tables. Runtime owner ports must
-- recheck complete history and canonical hashes in the caller's transaction.
CREATE TABLE draft_candidate_identities(
 draft_id TEXT PRIMARY KEY NOT NULL CHECK(length(draft_id) BETWEEN 1 AND 80 AND substr(draft_id,1,1) GLOB '[A-Za-z]' AND draft_id NOT GLOB '*[^A-Za-z0-9_-]*'),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 owner TEXT NOT NULL CHECK(owner IN ('import','authoring')),
 source_kind TEXT NOT NULL CHECK(source_kind IN ('import','authoring_single','authoring_group')),
 entity TEXT NOT NULL CHECK(entity IN ('course','lesson','block','concept','route','question','practice_set','assessment','note')),
 CHECK((owner='import' AND source_kind='import') OR (owner='authoring' AND source_kind IN ('authoring_single','authoring_group'))),
 CHECK(source_kind<>'authoring_single' OR entity='block'),
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

-- Reject malformed or unbound existing identities before copying any reviews.
-- SQL validates relationships and shape; it does not claim to recompute SHA-256.
CREATE TEMP TABLE m62_candidate_migration_guard(ok INTEGER NOT NULL CHECK(ok=1));
INSERT INTO m62_candidate_migration_guard SELECT NOT EXISTS(
 SELECT 1 FROM drafts d WHERE
 json_type(d.candidate_json,'$.import_id') IS NOT 'text' OR
 json_type(d.candidate_json,'$.metadata') IS NOT 'object' OR
 json_extract(d.candidate_json,'$.metadata.entity') IS NOT d.kind OR
 NOT EXISTS(
  SELECT 1 FROM ingestion_imports i JOIN jobs j ON j.id=i.job_id JOIN sources s ON s.id=i.source_id
  WHERE i.id=json_extract(d.candidate_json,'$.import_id') AND i.workspace_id=d.workspace_id
   AND j.workspace_id=d.workspace_id AND j.kind='import' AND s.workspace_id=d.workspace_id
   AND json_type(i.preview_json,'$.draft_ids')='array'
   AND EXISTS(SELECT 1 FROM json_each(i.preview_json,'$.draft_ids') p WHERE p.type='text' AND p.value=d.id)
 )
);
INSERT INTO m62_candidate_migration_guard SELECT NOT EXISTS(
 SELECT 1 FROM authoring_candidates c WHERE
 json_extract(c.record_json,'$.version') IS NOT 'authoring-candidate-v1' OR
 json_extract(c.record_json,'$.workspace_id') IS NOT c.workspace_id OR
 json_extract(c.record_json,'$.source_job_id') IS NOT c.source_job_id OR
 json_extract(c.record_json,'$.candidate.draft_id') IS NOT c.draft_id OR
 json_type(c.record_json,'$.candidate.draft_revision') IS NOT 'integer' OR
 json_extract(c.record_json,'$.candidate.draft_revision') IS NOT 1 OR
 json_extract(c.record_json,'$.candidate.entity') IS NOT 'block' OR
 NOT EXISTS(SELECT 1 FROM jobs j WHERE j.id=c.source_job_id AND j.workspace_id=c.workspace_id AND j.kind='authoring' AND j.status='completed') OR
 NOT EXISTS(SELECT 1 FROM authoring_records a WHERE a.job_id=c.source_job_id AND a.workspace_id=c.workspace_id
  AND json_extract(a.record_json,'$.input.version')='authoring-job-v1'
  AND json_extract(a.record_json,'$.input.workspace_id')=c.workspace_id
  AND json_extract(a.record_json,'$.input.job_id')=c.source_job_id
  AND json_extract(a.record_json,'$.view.summary.candidate.draft_id')=c.draft_id
  AND json_extract(a.record_json,'$.view.summary.candidate.draft_revision')=1
  AND json_extract(a.record_json,'$.view.summary.candidate.entity')='block'
  AND json_extract(a.record_json,'$.view.summary.candidate.candidate_sha256')=json_extract(c.record_json,'$.candidate.candidate_sha256'))
);
INSERT INTO m62_candidate_migration_guard SELECT NOT EXISTS(
 SELECT 1 FROM authoring_group_candidates c WHERE
 json_extract(c.record_json,'$.version') IS NOT 'authoring-group-record-v1' OR
 json_extract(c.record_json,'$.workspace_id') IS NOT c.workspace_id OR
 json_extract(c.record_json,'$.source_job_id') IS NOT c.source_job_id OR
 json_extract(c.record_json,'$.candidate.draft_id') IS NOT c.draft_id OR
 json_type(c.record_json,'$.candidate.draft_revision') IS NOT 'integer' OR
 json_extract(c.record_json,'$.candidate.draft_revision') IS NOT 1 OR
 json_extract(c.record_json,'$.candidate.entity') NOT IN ('lesson','practice_set','assessment') OR
 json_type(c.record_json,'$.candidate.entity') IS NOT 'text' OR
 json_extract(c.record_json,'$.plan_ref.source_job_id') IS NOT c.source_job_id OR
 NOT EXISTS(SELECT 1 FROM jobs j WHERE j.id=c.source_job_id AND j.workspace_id=c.workspace_id AND j.kind='authoring' AND j.status='completed') OR
 NOT EXISTS(SELECT 1 FROM authoring_content_plans p WHERE p.source_job_id=c.source_job_id AND p.workspace_id=c.workspace_id
  AND json_extract(p.record_json,'$.version')='authoring-content-plan-record-v1'
  AND json_extract(p.record_json,'$.workspace_id')=c.workspace_id
  AND json_extract(p.record_json,'$.source_job_id')=c.source_job_id
  AND json_extract(p.record_json,'$.plan_ref.source_job_id')=c.source_job_id
  AND json_extract(p.record_json,'$.provider_receipt_id')=json_extract(c.record_json,'$.provider_receipt_id')
  AND json_extract(p.record_json,'$.plan_ref.plan_sha256')=json_extract(c.record_json,'$.plan_ref.plan_sha256')) OR
 NOT EXISTS(SELECT 1 FROM authoring_records a WHERE a.job_id=c.source_job_id AND a.workspace_id=c.workspace_id
  AND json_extract(a.record_json,'$.input.version')='authoring-group-job-v1'
  AND json_extract(a.record_json,'$.input.workspace_id')=c.workspace_id
  AND json_extract(a.record_json,'$.input.job_id')=c.source_job_id
  AND json_extract(a.record_json,'$.view.summary.candidate.draft_id')=c.draft_id
  AND json_extract(a.record_json,'$.view.summary.candidate.draft_revision')=1
  AND json_extract(a.record_json,'$.view.summary.candidate.entity')=json_extract(c.record_json,'$.candidate.entity')
  AND json_extract(a.record_json,'$.view.summary.candidate.candidate_sha256')=json_extract(c.record_json,'$.candidate.candidate_sha256'))
);

-- UNION ALL deliberately retains collisions so the global primary key rejects
-- every duplicate ID, including duplicates across different workspaces/owners.
INSERT INTO draft_candidate_identities(draft_id,workspace_id,owner,source_kind,entity)
 SELECT id,workspace_id,'import','import',kind FROM drafts
 UNION ALL SELECT draft_id,workspace_id,'authoring','authoring_single',json_extract(record_json,'$.candidate.entity') FROM authoring_candidates
 UNION ALL SELECT draft_id,workspace_id,'authoring','authoring_group',json_extract(record_json,'$.candidate.entity') FROM authoring_group_candidates;
INSERT INTO draft_candidate_revisions(draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256)
 SELECT id,workspace_id,'import',kind,revision,candidate_sha256 FROM drafts
 UNION ALL SELECT draft_id,workspace_id,'authoring',json_extract(record_json,'$.candidate.entity'),json_extract(record_json,'$.candidate.draft_revision'),json_extract(record_json,'$.candidate.candidate_sha256') FROM authoring_candidates
 UNION ALL SELECT draft_id,workspace_id,'authoring',json_extract(record_json,'$.candidate.entity'),json_extract(record_json,'$.candidate.draft_revision'),json_extract(record_json,'$.candidate.candidate_sha256') FROM authoring_group_candidates;

-- No source revision is reconstructed from a review's claims. An unmatched
-- historical review aborts the whole migration and retains the original DB.
INSERT INTO m62_candidate_migration_guard SELECT NOT EXISTS(
 SELECT 1 FROM reviews r LEFT JOIN drafts d ON d.id=r.draft_id WHERE
 d.id IS NULL OR r.draft_revision IS NOT d.revision OR r.candidate_sha256 IS NOT d.candidate_sha256 OR
 json_type(r.receipt_json,'$.id') IS NOT 'text' OR
 json_extract(r.receipt_json,'$.id') IS NOT r.id OR
 json_type(r.receipt_json,'$.revision') IS NOT 'integer' OR
 json_extract(r.receipt_json,'$.revision') IS NOT r.revision OR
 json_type(r.receipt_json,'$.created_at') IS NOT 'text' OR
 json_extract(r.receipt_json,'$.created_at') IS NOT r.created_at OR
 json_type(r.receipt_json,'$.candidate.draft_id') IS NOT 'text' OR
 json_extract(r.receipt_json,'$.candidate.draft_id') IS NOT r.draft_id OR
 json_type(r.receipt_json,'$.candidate.draft_revision') IS NOT 'integer' OR
 json_extract(r.receipt_json,'$.candidate.draft_revision') IS NOT r.draft_revision OR
 json_type(r.receipt_json,'$.candidate.entity') IS NOT 'text' OR
 json_extract(r.receipt_json,'$.candidate.entity') IS NOT d.kind OR
 json_type(r.receipt_json,'$.candidate.candidate_sha256') IS NOT 'text' OR
 json_extract(r.receipt_json,'$.candidate.candidate_sha256') IS NOT r.candidate_sha256 OR
 (r.reviewer_session_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM local_sessions s WHERE s.id=r.reviewer_session_id AND s.workspace_id=d.workspace_id))
);
CREATE TABLE reviews_m62(
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
INSERT INTO reviews_m62(id,draft_id,draft_revision,candidate_sha256,revision,receipt_json,reviewer_session_id,created_at,workspace_id,owner,entity)
 SELECT r.id,r.draft_id,r.draft_revision,r.candidate_sha256,r.revision,r.receipt_json,r.reviewer_session_id,r.created_at,d.workspace_id,'import',d.kind
 FROM reviews r LEFT JOIN drafts d ON d.id=r.draft_id;
DROP TABLE reviews;
ALTER TABLE reviews_m62 RENAME TO reviews;
DROP TABLE m62_candidate_migration_guard;

-- BEFORE INSERT also rejects REPLACE, whose implicit deletion need not fire a
-- DELETE trigger when recursive_triggers is OFF. Exact retries read first.
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
