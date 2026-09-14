-- New submissions freeze non-score prerequisites before their first grading.
-- Existing submissions are explicitly historical; this is classification, not approval.
CREATE TABLE learning_submission_bases(
 attempt_id TEXT PRIMARY KEY REFERENCES attempts(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 basis TEXT NOT NULL CHECK(basis IN ('submission_frozen','history_not_frozen')),
 rule_version TEXT NOT NULL,
 prerequisites_json TEXT CHECK(prerequisites_json IS NULL OR json_valid(prerequisites_json)),
 prerequisites_sha256 TEXT,
 recorded_at TEXT NOT NULL,
 legacy_migration TEXT,
 CHECK((basis='submission_frozen' AND prerequisites_json IS NOT NULL AND length(prerequisites_sha256)=64 AND legacy_migration IS NULL)
    OR (basis='history_not_frozen' AND prerequisites_json IS NULL AND prerequisites_sha256 IS NULL AND legacy_migration='0007_learning_evidence'))
);
CREATE TRIGGER evidence_basis_workspace BEFORE INSERT ON learning_submission_bases WHEN NOT EXISTS(SELECT 1 FROM attempts WHERE id=NEW.attempt_id AND workspace_id=NEW.workspace_id) BEGIN SELECT RAISE(ABORT,'submission evidence workspace mismatch'); END;
INSERT INTO learning_submission_bases(attempt_id,workspace_id,basis,rule_version,recorded_at,legacy_migration)
 SELECT a.id,a.workspace_id,'history_not_frozen','eligibility-v1',strftime('%Y-%m-%dT%H:%M:%fZ','now'),'0007_learning_evidence'
 FROM attempts a WHERE a.status IN ('submitted','grading','graded','needs_review') OR a.submitted_responses_json IS NOT NULL OR EXISTS(SELECT 1 FROM grades g WHERE g.attempt_id=a.id);
CREATE TRIGGER evidence_basis_no_update BEFORE UPDATE ON learning_submission_bases BEGIN SELECT RAISE(ABORT,'submission evidence basis immutable'); END;
CREATE TRIGGER evidence_basis_no_delete BEFORE DELETE ON learning_submission_bases BEGIN SELECT RAISE(ABORT,'submission evidence basis immutable'); END;
CREATE TABLE learning_grade_bindings(
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 attempt_id TEXT NOT NULL,
 grading_revision INTEGER NOT NULL CHECK(grading_revision>0),
 event_id TEXT NOT NULL UNIQUE REFERENCES learning_events(event_id),
 result_sha256 TEXT NOT NULL CHECK(length(result_sha256)=64),
 basis TEXT NOT NULL CHECK(basis IN ('submission_frozen','history_not_frozen')),
 prerequisites_sha256 TEXT,
 qualification_version TEXT NOT NULL,
 binding_json TEXT NOT NULL CHECK(json_valid(binding_json)),
 binding_sha256 TEXT NOT NULL CHECK(length(binding_sha256)=64),
 recorded_at TEXT NOT NULL,
 UNIQUE(attempt_id,grading_revision),
 FOREIGN KEY(attempt_id,grading_revision) REFERENCES grades(attempt_id,grading_revision),
 FOREIGN KEY(attempt_id) REFERENCES learning_submission_bases(attempt_id)
);
CREATE TRIGGER evidence_binding_workspace BEFORE INSERT ON learning_grade_bindings WHEN NOT EXISTS(SELECT 1 FROM learning_submission_bases b JOIN learning_events e ON e.event_id=NEW.event_id WHERE b.attempt_id=NEW.attempt_id AND b.workspace_id=NEW.workspace_id AND b.basis=NEW.basis AND b.prerequisites_sha256 IS NEW.prerequisites_sha256 AND e.workspace_id=NEW.workspace_id AND e.kind='grade_finalized' AND e.origin='native') BEGIN SELECT RAISE(ABORT,'grade evidence binding mismatch'); END;
CREATE TRIGGER evidence_binding_no_update BEFORE UPDATE ON learning_grade_bindings BEGIN SELECT RAISE(ABORT,'grade evidence binding immutable'); END;
CREATE TRIGGER evidence_binding_no_delete BEFORE DELETE ON learning_grade_bindings BEGIN SELECT RAISE(ABORT,'grade evidence binding immutable'); END;
CREATE TABLE learning_evidence_refs(
 evidence_id TEXT PRIMARY KEY REFERENCES evidence(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 attempt_id TEXT NOT NULL,
 grading_revision INTEGER NOT NULL,
 question_id TEXT NOT NULL,
 question_revision INTEGER NOT NULL,
 question_sha256 TEXT NOT NULL,
 concept_id TEXT NOT NULL,
 concept_revision INTEGER NOT NULL,
 concept_sha256 TEXT NOT NULL,
 skill TEXT NOT NULL CHECK(skill IN ('recall','explain','compute','derive','transfer')),
 evidence_sha256 TEXT NOT NULL CHECK(length(evidence_sha256)=64),
 UNIQUE(attempt_id,grading_revision,question_id,question_revision,question_sha256,concept_id,concept_revision,concept_sha256,skill),
 FOREIGN KEY(attempt_id,grading_revision) REFERENCES learning_grade_bindings(attempt_id,grading_revision),
 FOREIGN KEY(question_id,question_revision,question_sha256) REFERENCES revisions(object_id,revision,sha256),
 FOREIGN KEY(concept_id,concept_revision,concept_sha256) REFERENCES revisions(object_id,revision,sha256)
);
CREATE TRIGGER evidence_ref_workspace BEFORE INSERT ON learning_evidence_refs WHEN NOT EXISTS(SELECT 1 FROM learning_grade_bindings b JOIN evidence e ON e.id=NEW.evidence_id JOIN objects q ON q.id=NEW.question_id JOIN objects c ON c.id=NEW.concept_id WHERE b.attempt_id=NEW.attempt_id AND b.grading_revision=NEW.grading_revision AND b.workspace_id=NEW.workspace_id AND e.workspace_id=NEW.workspace_id AND e.event_id=b.event_id AND e.attempt_id=b.attempt_id AND e.grading_revision=b.grading_revision AND q.workspace_id=NEW.workspace_id AND q.kind='question' AND c.workspace_id=NEW.workspace_id AND c.kind='concept') BEGIN SELECT RAISE(ABORT,'evidence reference mismatch'); END;
CREATE TRIGGER evidence_ref_no_update BEFORE UPDATE ON learning_evidence_refs BEGIN SELECT RAISE(ABORT,'evidence reference immutable'); END;
CREATE TRIGGER evidence_ref_no_delete BEFORE DELETE ON learning_evidence_refs BEGIN SELECT RAISE(ABORT,'evidence reference immutable'); END;
CREATE TRIGGER evidence_no_update BEFORE UPDATE ON evidence BEGIN SELECT RAISE(ABORT,'learning evidence immutable'); END;
CREATE TRIGGER evidence_no_delete BEFORE DELETE ON evidence BEGIN SELECT RAISE(ABORT,'learning evidence immutable'); END;
CREATE INDEX learning_binding_projection ON learning_grade_bindings(workspace_id,attempt_id,grading_revision);
CREATE INDEX learning_evidence_filter ON learning_evidence_refs(workspace_id,concept_id,skill,evidence_id);
CREATE TABLE learning_evidence_recovery_failures(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 attempt_id TEXT NOT NULL,
 grading_revision INTEGER NOT NULL,
 code TEXT NOT NULL CHECK(code='EVIDENCE_HISTORY_INVALID'),
 source_fingerprint TEXT NOT NULL CHECK(length(source_fingerprint)=64),
 detected_at TEXT NOT NULL,
 PRIMARY KEY(attempt_id,grading_revision),
 FOREIGN KEY(attempt_id,grading_revision) REFERENCES grades(attempt_id,grading_revision)
);
