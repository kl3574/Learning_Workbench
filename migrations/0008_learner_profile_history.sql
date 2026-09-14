-- Preserve legacy bytes without claiming a checksum existed before this migration.
CREATE TABLE learner_profile_legacy_snapshots(
 workspace_id TEXT PRIMARY KEY REFERENCES workspace(id),
 revision INTEGER NOT NULL CHECK(revision>=1),
 profile_json TEXT NOT NULL CHECK(json_valid(profile_json)),
 updated_at TEXT NOT NULL
);
INSERT INTO learner_profile_legacy_snapshots(workspace_id,revision,profile_json,updated_at)
 SELECT workspace_id,revision,profile_json,updated_at FROM learner_profiles;
CREATE TRIGGER learner_profile_legacy_no_update BEFORE UPDATE ON learner_profile_legacy_snapshots
 BEGIN SELECT RAISE(ABORT,'immutable legacy profile'); END;
CREATE TRIGGER learner_profile_legacy_no_delete BEFORE DELETE ON learner_profile_legacy_snapshots
 BEGIN SELECT RAISE(ABORT,'immutable legacy profile'); END;

CREATE TABLE learner_profile_history(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 revision INTEGER NOT NULL CHECK(revision>=1),
 profile_json TEXT NOT NULL CHECK(json_valid(profile_json)),
 profile_sha256 TEXT NOT NULL CHECK(length(profile_sha256)=64),
 updated_at TEXT NOT NULL,
 record_kind TEXT NOT NULL CHECK(record_kind IN ('native','legacy_preserved')),
 expected_revision INTEGER,
 request_sha256 TEXT,
 PRIMARY KEY(workspace_id,revision),
 CHECK((record_kind='native' AND revision>=2 AND expected_revision IS NOT NULL
        AND expected_revision=revision-1 AND request_sha256 IS NOT NULL AND length(request_sha256)=64)
    OR (record_kind='legacy_preserved' AND expected_revision IS NULL AND request_sha256 IS NULL))
);
CREATE TRIGGER learner_profile_history_no_update BEFORE UPDATE ON learner_profile_history
 BEGIN SELECT RAISE(ABORT,'immutable profile history'); END;
CREATE TRIGGER learner_profile_history_no_delete BEFORE DELETE ON learner_profile_history
 BEGIN SELECT RAISE(ABORT,'immutable profile history'); END;

CREATE TABLE learner_profile_command_receipts(
 actor TEXT NOT NULL,
 route TEXT NOT NULL,
 key TEXT NOT NULL,
 command_created_at TEXT NOT NULL,
 request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64),
 workspace_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 profile_sha256 TEXT NOT NULL CHECK(length(profile_sha256)=64),
 PRIMARY KEY(actor,route,key),
 FOREIGN KEY(actor,route,key) REFERENCES idempotency(actor,route,key) ON DELETE CASCADE,
 FOREIGN KEY(workspace_id,revision) REFERENCES learner_profile_history(workspace_id,revision)
);
CREATE TRIGGER learner_profile_receipts_no_update BEFORE UPDATE ON learner_profile_command_receipts
 BEGIN SELECT RAISE(ABORT,'immutable profile receipt'); END;
