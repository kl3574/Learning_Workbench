-- Tutor owns conversation/command/event records; Jobs owns lifecycle records.
CREATE TABLE tutor_threads(
 thread_id TEXT PRIMARY KEY REFERENCES threads(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 binding_json TEXT NOT NULL CHECK(json_valid(binding_json)),
 revision INTEGER NOT NULL CHECK(revision>=1),
 create_json TEXT NOT NULL CHECK(json_valid(create_json)),
 create_sha256 TEXT NOT NULL
);
CREATE TABLE tutor_runs(
 run_id TEXT PRIMARY KEY REFERENCES runs(id),
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 thread_id TEXT NOT NULL REFERENCES threads(id),
 input_sha256 TEXT NOT NULL,
 thread_revision INTEGER NOT NULL CHECK(thread_revision>=2),
 context_json TEXT CHECK(context_json IS NULL OR json_valid(context_json)),
 prepared_input_sha256 TEXT,
 latest_proposal_id TEXT,
 consent_id TEXT,
 result_json TEXT NOT NULL CHECK(json_valid(result_json)),
 integrity_sha256 TEXT NOT NULL
);
CREATE TABLE tutor_messages(
 message_id TEXT PRIMARY KEY REFERENCES messages(id),
 thread_id TEXT NOT NULL REFERENCES threads(id),
 seq INTEGER NOT NULL CHECK(seq>=1),
 message_json TEXT NOT NULL CHECK(json_valid(message_json)),
 message_sha256 TEXT NOT NULL,
 UNIQUE(thread_id,seq)
);
CREATE TABLE tutor_events(
 run_id TEXT NOT NULL REFERENCES runs(id),
 seq INTEGER NOT NULL CHECK(seq>=1),
 event_json TEXT NOT NULL CHECK(json_valid(event_json)),
 event_sha256 TEXT NOT NULL,
 PRIMARY KEY(run_id,seq)
);
CREATE TABLE tutor_commands(
 workspace_id TEXT NOT NULL REFERENCES workspace(id),
 route TEXT NOT NULL,
 key TEXT NOT NULL,
 thread_id TEXT NOT NULL REFERENCES threads(id),
 run_id TEXT REFERENCES runs(id),
 request_json TEXT NOT NULL CHECK(json_valid(request_json)),
 request_sha256 TEXT NOT NULL,
 ack_json TEXT NOT NULL CHECK(json_valid(ack_json)),
 ack_sha256 TEXT NOT NULL,
 created_at TEXT NOT NULL,
 PRIMARY KEY(workspace_id,route,key)
);
CREATE INDEX tutor_threads_workspace ON tutor_threads(workspace_id,thread_id);
CREATE INDEX tutor_runs_thread ON tutor_runs(workspace_id,thread_id);
CREATE INDEX tutor_messages_thread ON tutor_messages(thread_id,seq);
