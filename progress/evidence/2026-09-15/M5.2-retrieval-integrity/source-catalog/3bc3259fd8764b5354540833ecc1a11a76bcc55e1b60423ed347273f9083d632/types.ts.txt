// Generated from PRODUCT_DESIGN.md v3.0.3. DO NOT EDIT.
// spec_sha256: a9ad5cd57913630ef5cdf4781ae5f9155d44c7a7d8169bfec8ae4811be6481c8
// JSON Schema is the type source; runtime semantic checks remain required.

export type ApprovalDecision = {
  "operation_sha256": string;
  "decision": "approve_once" | "decline";
  "expected_revision": number;
};

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

export type AttemptCreate = {
  "assessment_ref": ContentRef;
  "mode": "independent" | "assisted" | "open_book";
};

export type AttemptPublic = {
  "id": string;
  "workspace_id": string;
  "assessment_ref": ContentRef;
  "status": "active" | "submitted" | "grading" | "graded" | "needs_review" | "abandoned";
  "policy": PolicySnapshot;
  "questions": Array<QuestionPublic>;
  "revision": number;
  "created_at": string;
  "deadline_at"?: (string | null);
  "submitted_at"?: (string | null);
};

export type AttemptSubmit = {
  "expected_revision": number;
};

export type AuthoringRequest = {
  "topic": string;
  "prerequisites": Array<string>;
  "objectives": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "output_kind": "lesson" | "worked_example" | "practice_set" | "assessment";
  "source_refs": Array<ContentRef>;
  "provider_id": string;
  "consent_id": string;
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

export type ContextSnapshot = {
  "id": string;
  "created_at": string;
  "request_sha256": string;
  "resolved_refs": Array<ContentRef>;
  "policy": "learning" | "practice" | "test_help" | "review" | "authoring";
  "character_count": number;
  "snapshot_sha256": string;
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

export type DraftCandidate = {
  "draft_id": string;
  "draft_revision": number;
  "entity": "course" | "lesson" | "block" | "concept" | "route" | "question" | "practice_set" | "assessment" | "note";
  "candidate_sha256": string;
};

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

export type Evidence = {
  "id": string;
  "event_id": string;
  "concept_id": string;
  "skill": "recall" | "explain" | "compute" | "derive" | "transfer";
  "eligible": boolean;
  "reason": string;
  "score"?: (number | null);
  "independence": "independent" | "assisted" | "unknown";
  "freshness": "novel" | "repeated" | "unknown";
};

export type EvidenceChunk = {
  "ref": ContentRef;
  "locator": string;
  "text": string;
};

export type FileEntry = {
  "path": string;
  "size": number;
  "sha256": string;
  "media_type": string;
  "visibility": "learner" | "author_private";
};

export type GenerationInput = {
  "snapshot_id": string;
  "snapshot_sha256": string;
  "messages": Array<GenerationMessage>;
  "evidence": Array<EvidenceChunk>;
  "max_input_tokens": number;
  "max_output_tokens": number;
  "consent_id": string;
  "web_search"?: boolean;
};

export type GenerationMessage = {
  "role": "system" | "user" | "assistant";
  "content": string;
};

export type GradingResult = {
  "attempt_id": string;
  "grading_revision": number;
  "grading_rules_version": string;
  "status": "graded" | "needs_review";
  "items": Array<ItemGrade>;
  "finalized_at": string;
};

export type ItemGrade = {
  "question_ref": ContentRef;
  "score"?: (number | null);
  "max_score": number;
  "status": "graded" | "needs_review";
  "feedback_markdown": string;
  "solution_markdown"?: (string | null);
};

export type JobRef = {
  "id": string;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
};

export type LearnerProfile = {
  "workspace_id": string;
  "revision": number;
  "goals"?: Array<string>;
  "goal_concept_ids"?: Array<string>;
  "weekly_minutes"?: number;
  "language"?: string;
  "preferred_difficulty"?: "beginner" | "intermediate" | "advanced";
  "self_assessments"?: Array<SelfAssessment>;
};

export type LearningEvent = {
  "event_id": string;
  "workspace_id": string;
  "actor": "learner" | "server" | "import";
  "origin": "native" | "user_supplied_import";
  "kind": "read_marked" | "hint_revealed" | "solution_revealed" | "practice_submitted" | "test_submitted" | "grade_finalized" | "note_created";
  "ref": ContentRef;
  "occurred_at": string;
  "attempt_id"?: (string | null);
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

export type Manifest = {
  "schema_version"?: "3.0.0";
  "format"?: "learning-package";
  "package_id": string;
  "profile": "learner" | "author";
  "created_at": string;
  "root_course"?: string;
  "files": Array<FileEntry>;
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

export type PolicySnapshot = {
  "policy_version"?: "1.0.0";
  "mode": "independent" | "assisted" | "open_book";
  "tutor_scope": "operation_help_only" | "academic";
  "allow_web": boolean;
  "allow_materials": boolean;
  "solution_release"?: "after_submit";
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

export type ProviderCapabilities = {
  "provider_id": string;
  "configured": boolean;
  "chat": boolean;
  "structured_output": boolean;
  "web_search": boolean;
  "streaming": boolean;
  "tool_calls": boolean;
  "version_evidence": string;
};

export type ProviderEvent = {
  "type": "delta" | "citation" | "usage" | "search_executed" | "finished" | "error";
  "text"?: (string | null);
  "citation"?: (Citation | null);
  "input_tokens"?: (number | null);
  "output_tokens"?: (number | null);
  "error_code"?: (string | null);
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

export type Recommendation = {
  "id": string;
  "target": ContentRef;
  "reason_code": "prerequisite_gap" | "assessment_error" | "review_due" | "next_route_step" | "user_goal";
  "explanation": string;
  "evidence_ids": Array<string>;
  "decision"?: "pending" | "accepted" | "dismissed";
  "action"?: "read" | "practice" | "test" | "review" | "inspect_source";
  "prerequisite_gaps"?: Array<string>;
  "estimated_minutes"?: (number | null);
  "rule_version"?: string;
  "generated_at": string;
  "staleness"?: "current" | "stale";
};

export type ResponseDraft = {
  "question_id": string;
  "answer": string;
  "steps_markdown"?: string;
};

export type ResponsesWrite = {
  "expected_revision": number;
  "responses": Array<ResponseDraft>;
};

export type ReviewReceipt = {
  "id": string;
  "revision"?: number;
  "candidate": DraftCandidate;
  "structural": "PASS" | "FAIL" | "NOT_RUN" | "BLOCKED";
  "mathematical": "APPROVED" | "REJECTED" | "NOT_RUN" | "NOT_APPLICABLE";
  "sources": "APPROVED" | "REJECTED" | "NOT_RUN" | "NOT_APPLICABLE";
  "independent_pedagogy": "PASS" | "FAIL" | "NOT_RUN" | "BLOCKED";
  "reviewer": string;
  "created_at": string;
  "evidence_paths": Array<string>;
  "decision_reason": string;
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

export type RunEvent = {
  "run_id": string;
  "seq": number;
  "type": "queued" | "context_ready" | "retrieval_completed" | "answer_delta" | "citation" | "approval_required" | "usage" | "completed" | "failed" | "cancelled";
  "occurred_at": string;
  "text"?: (string | null);
  "context_snapshot_id"?: (string | null);
  "citation"?: (Citation | null);
  "approval_id"?: (string | null);
  "input_tokens"?: (number | null);
  "output_tokens"?: (number | null);
  "error_code"?: (string | null);
};

export type RunSnapshot = {
  "id": string;
  "thread_id": string;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
  "context_snapshot_id"?: (string | null);
  "last_seq": number;
  "answer_markdown"?: string;
  "citations"?: Array<Citation>;
  "search_status"?: "not_requested" | "not_executed" | "executed" | "failed";
};

export type SavedTab = {
  "id": string;
  "context": ViewContext;
  "pinned": boolean;
  "scroll_offset"?: number;
};

export type SearchSource = {
  "id": string;
  "title": string;
  "url": string;
  "retrieved_at": string;
  "locator": string;
  "excerpt": string;
  "verification"?: "verified" | "unverified";
};

export type Selection = {
  "ref": ContentRef;
  "exact_quote": string;
  "prefix"?: string;
  "suffix"?: string;
  "start_codepoint": number;
  "end_codepoint": number;
};

export type SelfAssessment = {
  "concept_id": string;
  "level": "not_learned" | "encountered" | "independent_use";
  "origin"?: "self_report";
  "updated_at": string;
};

export type SolutionPrivate = {
  "schema_version"?: "3.0.0";
  "id": string;
  "revision": number;
  "question_ref": ContentRef;
  "grading_kind": "choice_exact" | "text_normalized" | "numeric_tolerance" | "symbolic_review" | "rubric_review";
  "accepted_answers": Array<string>;
  "absolute_tolerance"?: number;
  "relative_tolerance"?: number;
  "unit"?: (string | null);
  "domain_assumptions"?: Array<string>;
  "solution_markdown": string;
  "rubric_markdown"?: string;
  "review_status": "draft" | "needs_review" | "approved";
};

export type Symbol = {
  "id": string;
  "tex": string;
  "meaning": string;
  "domain": string;
  "dimension": string;
  "scope": string;
  "first_definition": ContentRef;
};

export type TutorRequest = {
  "thread_id": string;
  "workspace_id": string;
  "message": string;
  "intent": "explain" | "hint" | "derive" | "research";
  "context": ViewContext;
  "web_search"?: boolean;
  "consent_id"?: (string | null);
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
