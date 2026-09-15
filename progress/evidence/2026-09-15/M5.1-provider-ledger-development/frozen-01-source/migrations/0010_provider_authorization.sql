-- Provider-owned native history. Baseline legacy rows are not native grants.
CREATE TABLE provider_command_history(
 id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id),
 actor TEXT NOT NULL, route TEXT NOT NULL, command_key TEXT NOT NULL,
 command_json TEXT NOT NULL CHECK(json_valid(command_json)),
 result_json TEXT NOT NULL CHECK(json_valid(result_json)),
 created_at TEXT NOT NULL, integrity_sha256 TEXT NOT NULL CHECK(length(integrity_sha256)=64),
 UNIQUE(workspace_id,actor,command_key)
);
CREATE TABLE provider_private_commands(
 command_id TEXT PRIMARY KEY REFERENCES provider_command_history(id),
 fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64),
 integrity_sha256 TEXT NOT NULL CHECK(length(integrity_sha256)=64)
);
CREATE TABLE provider_config_history(
 provider_id TEXT NOT NULL, workspace_id TEXT NOT NULL REFERENCES workspace(id),
 revision INTEGER NOT NULL CHECK(revision>=1),
 config_json TEXT NOT NULL CHECK(json_valid(config_json)),
 config_sha256 TEXT NOT NULL CHECK(length(config_sha256)=64),
 previous_sha256 TEXT, history_sha256 TEXT NOT NULL CHECK(length(history_sha256)=64),
 command_id TEXT NOT NULL UNIQUE REFERENCES provider_command_history(id) DEFERRABLE INITIALLY DEFERRED,
 created_at TEXT NOT NULL, PRIMARY KEY(provider_id,revision), UNIQUE(workspace_id,provider_id,revision)
);
CREATE TABLE provider_config_heads(
 provider_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id),
 revision INTEGER NOT NULL, FOREIGN KEY(workspace_id,provider_id,revision)
 REFERENCES provider_config_history(workspace_id,provider_id,revision)
);
CREATE TABLE provider_private_references(
 provider_id TEXT NOT NULL, revision INTEGER NOT NULL, locator TEXT NOT NULL,
 integrity_sha256 TEXT NOT NULL CHECK(length(integrity_sha256)=64),
 PRIMARY KEY(provider_id,revision), FOREIGN KEY(provider_id,revision) REFERENCES provider_config_history(provider_id,revision)
);
CREATE TABLE provider_proposals(
 id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id),
 proposal_sha256 TEXT NOT NULL CHECK(length(proposal_sha256)=64),
 summary_json TEXT NOT NULL CHECK(json_valid(summary_json)),
 material_json TEXT NOT NULL CHECK(json_valid(material_json)),
 request_body BLOB NOT NULL, command_id TEXT NOT NULL UNIQUE REFERENCES provider_command_history(id) DEFERRABLE INITIALLY DEFERRED,
 created_at TEXT NOT NULL
);
CREATE TABLE provider_consent_history(
 id TEXT NOT NULL, workspace_id TEXT NOT NULL REFERENCES workspace(id), revision INTEGER NOT NULL CHECK(revision>=1),
 proposal_id TEXT NOT NULL REFERENCES provider_proposals(id), status TEXT NOT NULL CHECK(status IN('active','revoked')),
 created_at TEXT NOT NULL, revoked_at TEXT, previous_sha256 TEXT,
 history_sha256 TEXT NOT NULL CHECK(length(history_sha256)=64),
 command_id TEXT NOT NULL UNIQUE REFERENCES provider_command_history(id) DEFERRABLE INITIALLY DEFERRED,
 PRIMARY KEY(id,revision), UNIQUE(workspace_id,id,revision)
);
CREATE TABLE provider_consent_heads(
 id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id), revision INTEGER NOT NULL,
 proposal_id TEXT NOT NULL UNIQUE REFERENCES provider_proposals(id),
 FOREIGN KEY(workspace_id,id,revision) REFERENCES provider_consent_history(workspace_id,id,revision)
);
CREATE TABLE provider_dispatches(
 id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id),
 consent_id TEXT NOT NULL UNIQUE REFERENCES provider_consent_heads(id), job_id TEXT NOT NULL,
 proposal_id TEXT NOT NULL REFERENCES provider_proposals(id), request_body_sha256 TEXT NOT NULL CHECK(length(request_body_sha256)=64),
 started_at TEXT NOT NULL, integrity_sha256 TEXT NOT NULL CHECK(length(integrity_sha256)=64)
);
CREATE TABLE provider_dispatch_usage(
 dispatch_id TEXT NOT NULL REFERENCES provider_dispatches(id), sequence INTEGER NOT NULL CHECK(sequence>=1),
 usage_json TEXT NOT NULL CHECK(json_valid(usage_json)), previous_sha256 TEXT,
 integrity_sha256 TEXT NOT NULL CHECK(length(integrity_sha256)=64), PRIMARY KEY(dispatch_id,sequence)
);
CREATE TABLE provider_artifacts(
 id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id), dispatch_id TEXT NOT NULL REFERENCES provider_dispatches(id),
 channel TEXT NOT NULL CHECK(channel IN('answer','refusal')), bytes BLOB NOT NULL,
 sha256 TEXT NOT NULL CHECK(length(sha256)=64), UNIQUE(dispatch_id,channel)
);
CREATE TABLE provider_terminals(
 dispatch_id TEXT PRIMARY KEY REFERENCES provider_dispatches(id), workspace_id TEXT NOT NULL REFERENCES workspace(id),
 receipt_json TEXT NOT NULL CHECK(json_valid(receipt_json)), receipt_sha256 TEXT NOT NULL CHECK(length(receipt_sha256)=64)
);
CREATE TABLE provider_backup_projections(
 workspace_id TEXT PRIMARY KEY REFERENCES workspace(id), created_at TEXT NOT NULL,
 historical_scope_sha256 TEXT NOT NULL CHECK(length(historical_scope_sha256)=64),
 projection_json TEXT NOT NULL CHECK(json_valid(projection_json)), projection_sha256 TEXT NOT NULL CHECK(length(projection_sha256)=64)
);
CREATE TRIGGER provider_command_history_no_update BEFORE UPDATE ON provider_command_history BEGIN SELECT RAISE(ABORT,'immutable provider command'); END;
CREATE TRIGGER provider_command_history_no_delete BEFORE DELETE ON provider_command_history BEGIN SELECT RAISE(ABORT,'immutable provider command'); END;
CREATE TRIGGER provider_config_history_no_update BEFORE UPDATE ON provider_config_history BEGIN SELECT RAISE(ABORT,'immutable provider config'); END;
CREATE TRIGGER provider_config_history_no_delete BEFORE DELETE ON provider_config_history BEGIN SELECT RAISE(ABORT,'immutable provider config'); END;
CREATE TRIGGER provider_proposals_no_update BEFORE UPDATE ON provider_proposals BEGIN SELECT RAISE(ABORT,'immutable provider proposal'); END;
CREATE TRIGGER provider_proposals_no_delete BEFORE DELETE ON provider_proposals BEGIN SELECT RAISE(ABORT,'immutable provider proposal'); END;
CREATE TRIGGER provider_consent_history_no_update BEFORE UPDATE ON provider_consent_history BEGIN SELECT RAISE(ABORT,'immutable provider consent'); END;
CREATE TRIGGER provider_consent_history_no_delete BEFORE DELETE ON provider_consent_history BEGIN SELECT RAISE(ABORT,'immutable provider consent'); END;
CREATE TRIGGER provider_dispatches_no_update BEFORE UPDATE ON provider_dispatches BEGIN SELECT RAISE(ABORT,'immutable provider dispatch'); END;
CREATE TRIGGER provider_dispatches_no_delete BEFORE DELETE ON provider_dispatches BEGIN SELECT RAISE(ABORT,'immutable provider dispatch'); END;
CREATE TRIGGER provider_dispatch_usage_no_update BEFORE UPDATE ON provider_dispatch_usage BEGIN SELECT RAISE(ABORT,'immutable provider usage'); END;
CREATE TRIGGER provider_dispatch_usage_no_delete BEFORE DELETE ON provider_dispatch_usage BEGIN SELECT RAISE(ABORT,'immutable provider usage'); END;
CREATE TRIGGER provider_artifacts_no_update BEFORE UPDATE ON provider_artifacts BEGIN SELECT RAISE(ABORT,'immutable provider artifact'); END;
CREATE TRIGGER provider_artifacts_no_delete BEFORE DELETE ON provider_artifacts BEGIN SELECT RAISE(ABORT,'immutable provider artifact'); END;
CREATE TRIGGER provider_terminals_no_update BEFORE UPDATE ON provider_terminals BEGIN SELECT RAISE(ABORT,'immutable provider terminal'); END;
CREATE TRIGGER provider_terminals_no_delete BEFORE DELETE ON provider_terminals BEGIN SELECT RAISE(ABORT,'immutable provider terminal'); END;
CREATE TRIGGER provider_backup_projections_no_update BEFORE UPDATE ON provider_backup_projections BEGIN SELECT RAISE(ABORT,'immutable provider backup projection'); END;
CREATE TRIGGER provider_backup_projections_no_delete BEFORE DELETE ON provider_backup_projections BEGIN SELECT RAISE(ABORT,'immutable provider backup projection'); END;
