-- Recommendation owns these projections and receipts. Existing exchange-format
-- recommendations remain untouched; no legacy row is labelled native evidence.
CREATE TABLE recommendation_legacy_snapshots AS SELECT * FROM recommendations;
CREATE TRIGGER recommendation_legacy_no_update BEFORE UPDATE ON recommendation_legacy_snapshots
 BEGIN SELECT RAISE(ABORT,'immutable legacy recommendation'); END;
CREATE TRIGGER recommendation_legacy_no_delete BEFORE DELETE ON recommendation_legacy_snapshots
 BEGIN SELECT RAISE(ABORT,'immutable legacy recommendation'); END;

CREATE TABLE recommendation_input_events(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 generation INTEGER NOT NULL CHECK(generation>=1),
 source TEXT NOT NULL CHECK(length(source)>0),
 occurred_at TEXT NOT NULL,
 PRIMARY KEY(workspace_id,generation)
);
CREATE TRIGGER recommendation_inputs_no_update BEFORE UPDATE ON recommendation_input_events
 BEGIN SELECT RAISE(ABORT,'immutable recommendation input event'); END;
CREATE TRIGGER recommendation_inputs_no_delete BEFORE DELETE ON recommendation_input_events
 BEGIN SELECT RAISE(ABORT,'immutable recommendation input event'); END;

CREATE TABLE recommendation_snapshots(
 id TEXT PRIMARY KEY,
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 sequence INTEGER NOT NULL CHECK(sequence>=1),
 generation INTEGER NOT NULL CHECK(generation>=1),
 basis_sha256 TEXT NOT NULL CHECK(length(basis_sha256)=64),
 snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256)=64),
 snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
 created_at TEXT NOT NULL,
 UNIQUE(workspace_id,sequence),
 FOREIGN KEY(workspace_id,generation) REFERENCES recommendation_input_events(workspace_id,generation)
);
CREATE TRIGGER recommendation_snapshots_no_update BEFORE UPDATE ON recommendation_snapshots
 BEGIN SELECT RAISE(ABORT,'immutable recommendation snapshot'); END;
CREATE TRIGGER recommendation_snapshots_no_delete BEFORE DELETE ON recommendation_snapshots
 BEGIN SELECT RAISE(ABORT,'immutable recommendation snapshot'); END;

CREATE TABLE recommendation_projection_state(
 workspace_id TEXT PRIMARY KEY REFERENCES workspace(id),
 generation INTEGER NOT NULL CHECK(generation>=1),
 completed_generation INTEGER NOT NULL DEFAULT 0 CHECK(completed_generation>=0 AND completed_generation<=generation),
 snapshot_id TEXT REFERENCES recommendation_snapshots(id),
 failure_json TEXT CHECK(failure_json IS NULL OR json_valid(failure_json)),
 retry_at TEXT,
 FOREIGN KEY(workspace_id,generation) REFERENCES recommendation_input_events(workspace_id,generation)
);

CREATE TABLE recommendation_decision_history(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 recommendation_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision>=1),
 snapshot_id TEXT NOT NULL REFERENCES recommendation_snapshots(id),
 decision TEXT NOT NULL CHECK(decision IN('pending','accepted','dismissed')),
 reason TEXT,
 decision_sha256 TEXT NOT NULL CHECK(length(decision_sha256)=64),
 previous_sha256 TEXT CHECK(previous_sha256 IS NULL OR length(previous_sha256)=64),
 created_at TEXT NOT NULL,
 PRIMARY KEY(workspace_id,recommendation_id,revision),
 CHECK((revision=1 AND decision='pending' AND reason IS NULL AND previous_sha256 IS NULL)
    OR (revision>1 AND decision!='pending' AND previous_sha256 IS NOT NULL))
);
CREATE TRIGGER recommendation_decisions_no_update BEFORE UPDATE ON recommendation_decision_history
 BEGIN SELECT RAISE(ABORT,'immutable recommendation decision'); END;
CREATE TRIGGER recommendation_decisions_no_delete BEFORE DELETE ON recommendation_decision_history
 BEGIN SELECT RAISE(ABORT,'immutable recommendation decision'); END;

CREATE TABLE recommendation_decision_heads(
 workspace_id TEXT NOT NULL,
 recommendation_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 decision_sha256 TEXT NOT NULL CHECK(length(decision_sha256)=64),
 PRIMARY KEY(workspace_id,recommendation_id),
 FOREIGN KEY(workspace_id,recommendation_id,revision)
  REFERENCES recommendation_decision_history(workspace_id,recommendation_id,revision)
);

-- Keep every completed command instance even when the shared idempotency row
-- expires and its key is reused. No cascade may erase the original receipt.
CREATE TABLE recommendation_command_receipts(
 actor TEXT NOT NULL,
 route TEXT NOT NULL,
 key TEXT NOT NULL,
 command_created_at TEXT NOT NULL,
 request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64),
 workspace_id TEXT NOT NULL,
 recommendation_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 decision_sha256 TEXT NOT NULL CHECK(length(decision_sha256)=64),
 result_json TEXT NOT NULL CHECK(json_valid(result_json)),
 PRIMARY KEY(actor,route,key,command_created_at),
 FOREIGN KEY(workspace_id,recommendation_id,revision)
  REFERENCES recommendation_decision_history(workspace_id,recommendation_id,revision)
);
CREATE TRIGGER recommendation_receipts_no_update BEFORE UPDATE ON recommendation_command_receipts
 BEGIN SELECT RAISE(ABORT,'immutable recommendation command receipt'); END;
CREATE TRIGGER recommendation_receipts_no_delete BEFORE DELETE ON recommendation_command_receipts
 BEGIN SELECT RAISE(ABORT,'immutable recommendation command receipt'); END;
