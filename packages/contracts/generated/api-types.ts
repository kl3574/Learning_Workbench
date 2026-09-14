// Generated from PRODUCT_DESIGN.md v3.0.0. DO NOT EDIT.
// spec_sha256: ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c
// JSON Schema is the type source; runtime semantic checks remain required.

export type AssessmentBlueprint = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "assessment";
  "title": string;
  "question_refs": Array<ContentRef>;
  "allowed_modes": Array<"independent" | "assisted" | "open_book">;
  "time_limit_seconds"?: (number | null);
};

export type BlockDraftPayload = {
  "metadata": ContentBlock;
  "body_markdown": string;
  "source_id": string;
  "citations"?: Array<Citation>;
};

export type BootstrapRequest = {
  "one_time_code": string;
};

export type BootstrapResponse = {
  "workspace_id": string;
  "csrf_token": string;
  "expires_at": string;
};

export type CandidateSummary = {
  "course_title": string;
  "lesson_count": number;
  "block_count": number;
  "unresolved_refs": Array<string>;
};

export type Choice = {
  "id": string;
  "text_markdown": string;
};

export type Citation = {
  "id": string;
  "title": string;
  "url"?: (string | null);
  "locator": string;
  "source_sha256"?: (string | null);
  "verification": "verified" | "unverified" | "user_supplied";
};

export type Concept = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "concept";
  "title": string;
  "prerequisite_ids"?: Array<string>;
  "skill_dimensions"?: Array<"recall" | "explain" | "compute" | "derive" | "transfer">;
};

export type ContentBlock = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "block";
  "kind": "orientation" | "definition" | "theorem" | "proof" | "intuition" | "worked_example" | "boundary" | "summary" | "text" | "code" | "figure";
  "title": string;
  "body_path": string;
  "body_sha256": string;
  "concepts"?: Array<string>;
  "citations"?: Array<string>;
  "depends_on"?: Array<ContentRef>;
};

export type ContentRef = {
  "entity": "course" | "lesson" | "block" | "concept" | "route" | "question" | "practice_set" | "assessment" | "note";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type Course = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "course";
  "title": string;
  "language"?: string;
  "audience": string;
  "lesson_refs": Array<ContentRef>;
  "concept_refs"?: Array<ContentRef>;
  "sections"?: Array<CourseSection>;
  "objectives"?: Array<string>;
  "difficulty"?: "beginner" | "intermediate" | "advanced";
};

export type CourseSection = {
  "id": string;
  "title": string;
  "lesson_ids": Array<string>;
};

export type CourseSummary = {
  "ref": ContentRef;
  "title": string;
  "language": string;
  "lesson_count": number;
  "review_state"?: "unreviewed";
};

export type DownloadArtifact = {
  "artifact_id": string;
  "filename": string;
  "size": number;
  "sha256": string;
  "media_type": string;
  "download_path": string;
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

export type ImportCancelRequest = {
  "expected_input_sha256": string;
};

export type ImportCancelResponse = {
  "id": string;
  "status"?: "cancelled";
};

export type ImportCommitRequest = {
  "expected_input_sha256": string;
  "accepted_warning_codes": Array<string>;
  "id_mapping": Array<ImportIdMapping>;
};

export type ImportCommitResponse = {
  "course_refs": Array<ContentRef>;
  "migration_receipt_id": string;
};

export type ImportDraftSnapshot = {
  "id": string;
  "kind": "course" | "lesson" | "block" | "concept" | "route" | "question" | "practice_set" | "assessment" | "note";
  "revision": number;
  "base_ref": (ContentRef | null);
  "state": "draft" | "in_review" | "approved" | "needs_changes" | "published" | "cancelled";
  "candidate_sha256": string;
  "payload": (BlockDraftPayload | Course | Lesson | Concept | Route | QuestionPublic | PracticeSet | AssessmentBlueprint | Note);
  "warnings": Array<Warning>;
};

export type ImportIdMapping = {
  "old_id": string;
  "new_id": string;
};

export type ImportPreview = {
  "id": string;
  "status": "staged" | "parsing" | "preview_ready" | "committed" | "cancelled" | "failed";
  "input_sha256": string;
  "warnings": Array<Warning>;
  "candidate_summary": CandidateSummary;
  "preview_refs": Array<string>;
};

export type ImportStaged = {
  "import_id": string;
  "job": JobRef;
  "input_sha256": string;
};

export type ImportUpload = {
  "file": Blob;
  "kind": "auto" | "markdown" | "text" | "html" | "pdf" | "docx" | "learnpack";
  "target_course_id"?: (string | null);
};

export type JobCancelRequest = {
  "expected_revision": number;
};

export type JobProgress = {
  "completed": number;
  "total": (number | null);
  "label": string;
};

export type JobRef = {
  "id": string;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
};

export type JobSnapshot = {
  "id": string;
  "workspace_id": string;
  "kind": string;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
  "revision": number;
  "created_at": string;
  "updated_at": string;
  "progress": JobProgress;
  "result_refs": Array<ContentRef>;
  "warnings": Array<Warning>;
  "error": (ErrorDetail | null);
};

export type Lesson = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "lesson";
  "title": string;
  "objectives": Array<string>;
  "prerequisite_ids"?: Array<string>;
  "block_refs": Array<ContentRef>;
  "proof_policy"?: "full" | "declared_dependencies";
};

export type LogoutResponse = {
  "logged_out"?: true;
};

export type MutationAck = {
  "id": string;
  "revision": number;
  "applied": boolean;
};

export type Note = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "note";
  "workspace_id": string;
  "anchor": Selection;
  "markdown": string;
  "anchor_state"?: "exact" | "stale" | "unresolved";
};

export type PageCourse = {
  "items": Array<CourseSummary>;
  "next_cursor": (string | null);
};

export type PageRevision = {
  "items": Array<RevisionSummary>;
  "next_cursor": (string | null);
};

export type PracticeSet = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "practice_set";
  "title": string;
  "lesson_ref": ContentRef;
  "question_refs": Array<ContentRef>;
  "feedback_policy"?: "on_submit_or_reveal";
};

export type PreferencesPatch = {
  "language"?: string;
  "reader_font_size"?: number;
  "default_learning_minutes"?: number;
  "auto_attach_current_lesson"?: boolean;
};

export type PreferencesRequest = {
  "expected_revision": number;
  "preferences": PreferencesPatch;
};

export type QuestionPublic = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "question";
  "kind": "single_choice" | "text_blank" | "numeric" | "expression" | "calculation";
  "stem_markdown": string;
  "choices"?: Array<Choice>;
  "concept_ids": Array<string>;
  "skill": "recall" | "explain" | "compute" | "derive" | "transfer";
  "exposure_group": string;
  "max_score"?: number;
  "input_instructions": string;
};

export type ReadinessResponse = {
  "database_ready": boolean;
  "worker_ready": boolean;
  "data_schema_version": string;
  "migrations_pending": boolean;
  "providers_configured": boolean;
};

export type RevisionSummary = {
  "ref": ContentRef;
  "created_at": string;
  "review_state"?: "unreviewed";
  "lifecycle": "active" | "archived";
};

export type RoleRequest = {
  "role": "learner" | "author";
};

export type Route = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "entity"?: "route";
  "title": string;
  "goal": string;
  "steps": Array<RouteStep>;
};

export type RouteStep = {
  "id": string;
  "title": string;
  "target": ContentRef;
  "requires_steps"?: Array<string>;
  "completion_rule": "manual" | "read" | "practice_submitted" | "assessment_submitted";
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

export type SourceResponse = {
  "id": string;
  "media_type": string;
  "size": number;
  "sha256": string;
  "rights": string;
  "parser_version": (string | null);
  "warnings": Array<Warning>;
  "artifact": DownloadArtifact;
};

export type ViewContext = {
  "view_kind": "route" | "lesson" | "worked_example" | "practice" | "assessment_help" | "assessment_review" | "authoring";
  "active_ref": ContentRef;
  "attached_refs"?: Array<ContentRef>;
  "selection"?: (Selection | null);
  "attempt_id"?: (string | null);
};

export type Warning = {
  "code": string;
  "message": string;
  "locator"?: (string | null);
  "severity": "info" | "warning" | "error";
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
