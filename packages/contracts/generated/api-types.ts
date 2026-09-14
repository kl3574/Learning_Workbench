// Generated from PRODUCT_DESIGN.md v3.0.0. DO NOT EDIT.
// spec_sha256: ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c
// JSON Schema is the type source; runtime semantic checks remain required.

export type BootstrapRequest = {
  "one_time_code": string;
};

export type BootstrapResponse = {
  "workspace_id": string;
  "csrf_token": string;
  "expires_at": string;
};

export type ContentRef = {
  "entity": "course" | "lesson" | "block" | "concept" | "route" | "question" | "practice_set" | "assessment" | "note";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type EmptyRequest = Record<string, never>;

export type ErrorDetail = {
  "code": string;
  "message": string;
  "request_id": string;
  "retryable": boolean;
  "details"?: Array<string>;
};

export type ErrorEnvelope = {
  "error": ErrorDetail;
};

export type HealthResponse = {
  "status"?: "ok";
  "build_version"?: string;
};

export type LogoutResponse = {
  "logged_out"?: true;
};

export type MutationAck = {
  "id": string;
  "revision": number;
  "applied": boolean;
};

export type PreferencesPatch = {
  "language"?: (string | null);
  "reader_font_size"?: (number | null);
  "default_learning_minutes"?: (number | null);
  "auto_attach_current_lesson"?: (boolean | null);
};

export type PreferencesRequest = {
  "expected_revision": number;
  "preferences": PreferencesPatch;
};

export type ReadinessResponse = {
  "database_ready": boolean;
  "worker_ready": boolean;
  "data_schema_version": string;
  "migrations_pending": boolean;
  "providers_configured": boolean;
};

export type RoleRequest = {
  "role": "learner" | "author";
};

export type SavedTab = {
  "id": string;
  "context": ViewContext;
  "pinned": boolean;
  "scroll_offset"?: number;
};

export type Selection = {
  "ref": ContentRef;
  "exact_quote": string;
  "prefix"?: string;
  "suffix"?: string;
  "start_codepoint": number;
  "end_codepoint": number;
};

export type SessionResponse = {
  "workspace_id": string;
  "role": "learner" | "author";
  "csrf_token": string;
  "active_independent_attempt_id": (string | null);
};

export type ViewContext = {
  "view_kind": "route" | "lesson" | "worked_example" | "practice" | "assessment_help" | "assessment_review" | "authoring";
  "active_ref": ContentRef;
  "attached_refs"?: Array<ContentRef>;
  "selection"?: (Selection | null);
  "attempt_id"?: (string | null);
};

export type WorkbenchSaveRequest = {
  "expected_revision": number;
  "session": WorkbenchSession;
};

export type WorkbenchSession = {
  "revision": number;
  "course_ref"?: (ContentRef | null);
  "navigation"?: "route" | "textbook" | "practice" | "assessment";
  "tabs"?: Array<SavedTab>;
  "active_tab_id"?: (string | null);
  "expanded_keys"?: Array<string>;
  "directory_scroll"?: number;
  "nav_width"?: number;
  "agent_width"?: number;
  "nav_collapsed"?: boolean;
  "agent_collapsed"?: boolean;
};

export type WorkspaceLayout = {
  "nav_width": number;
  "agent_width": number;
  "nav_collapsed": boolean;
  "agent_collapsed": boolean;
};

export type WorkspacePreferences = {
  "language"?: string;
  "reader_font_size"?: number;
  "default_learning_minutes"?: number;
  "auto_attach_current_lesson"?: boolean;
};

export type WorkspaceResponse = {
  "id": string;
  "title": string;
  "revision": number;
  "preferences": WorkspacePreferences;
  "layout": WorkspaceLayout;
  "data_schema_version": string;
};
