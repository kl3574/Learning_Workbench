// Generated from PRODUCT_DESIGN.md v3.0.7. DO NOT EDIT.
// spec_sha256: 2d1ecce71e0aa6953c0f772b1935e7e3abdc5933bfbbe93d851a6171236d8a4d
// JSON Schema is the type source; runtime semantic checks remain required.

export type ApprovalDecision = {
  "operation_sha256": string;
  "decision": "approve_once" | "decline";
  "expected_revision": number;
};

export type AssessmentCandidateRoot = {
  "entity": "assessment";
  "title": string;
  "questions": Array<AuthoringQuestionMemberRef>;
  "allowed_modes": Array<"independent" | "assisted" | "open_book">;
  "time_limit_seconds": (number | null);
};

export type AuthoringAssessmentGenerated = {
  "output_kind": "assessment";
  "title": string;
  "questions": Array<QuestionDraftPublic>;
  "solutions": Array<GeneratedSolutionAnswer>;
};

export type AuthoringAssessmentPrepareWrite = {
  "topic": string;
  "prerequisites": Array<string>;
  "objectives": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "source_refs": Array<AuthoringBlockRef>;
  "provider_id": string;
  "target_concept_refs": Array<AuthoringConceptRef>;
  "output_kind": "assessment";
  "allowed_modes": Array<"independent" | "assisted" | "open_book">;
  "time_limit_seconds": (number | null);
};

export type AuthoringBlockMemberRef = {
  "member_key": string;
  "entity": "block";
  "member_sha256": string;
};

export type AuthoringBlockPlanEntry = {
  "member_key": string;
  "entity": "block";
  "kind": "orientation" | "definition" | "theorem" | "proof" | "intuition" | "worked_example" | "boundary" | "summary" | "text" | "code" | "figure";
  "title": string;
  "objective_indexes": Array<number>;
  "prerequisite_indexes": Array<number>;
  "depends_on_keys": Array<string>;
};

export type AuthoringBlockRef = {
  "entity": "block";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type AuthoringCandidate = {
  "draft_id": string;
  "draft_revision": number;
  "entity": "block";
  "candidate_sha256": string;
};

export type AuthoringConceptRef = {
  "entity": "concept";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type AuthoringContentPlan = {
  "version": "authoring-content-plan-v1";
  "output_kind": "lesson" | "practice_set" | "assessment";
  "topic": string;
  "prerequisites": Array<string>;
  "objectives": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "entries": Array<(AuthoringBlockPlanEntry | AuthoringQuestionPlanEntry)>;
};

export type AuthoringContentPlanRef = {
  "source_job_id": string;
  "plan_sha256": string;
};

export type AuthoringDraftMemberRef = {
  "member_key": string;
  "entity": "block" | "question";
  "member_sha256": string;
};

export type AuthoringDraftView = {
  "owner": "authoring";
  "candidate": AuthoringCandidate;
  "source_job_id": string;
  "state": "draft";
  "base_ref": null;
  "body_sha256": string;
  "payload": WorkedExamplePayload;
  "validation": AuthoringValidation;
  "numeric_check_ids": Array<string>;
  "warnings": Array<Warning>;
};

export type AuthoringGeneratedBlock = {
  "member_key": string;
  "depends_on_keys": Array<string>;
  "payload": (WorkedExamplePayload | AuthoringTextBlockPayload);
};

export type AuthoringGroupCandidate = {
  "draft_id": string;
  "draft_revision": number;
  "entity": "lesson" | "practice_set" | "assessment";
  "candidate_sha256": string;
};

export type AuthoringGroupCandidatePayload = {
  "version": "authoring-group-candidate-v1";
  "content_plan": AuthoringContentPlan;
  "root": (LessonCandidateRoot | PracticeSetCandidateRoot | AssessmentCandidateRoot);
  "blocks": Array<AuthoringGeneratedBlock>;
  "questions": Array<QuestionDraftPublic>;
  "private_solutions": Array<SolutionDraftPrivate>;
};

export type AuthoringGroupDraftView = {
  "owner": "authoring";
  "candidate": AuthoringGroupCandidate;
  "source_job_id": string;
  "state": "draft";
  "base_ref": null;
  "plan_ref": AuthoringContentPlanRef;
  "content_plan": AuthoringContentPlan;
  "root": (LessonCandidateRoot | PracticeSetCandidateRoot | AssessmentCandidateRoot);
  "blocks": Array<AuthoringGeneratedBlock>;
  "questions": Array<QuestionDraftPublic>;
  "private_solution_refs": Array<AuthoringPrivateSolutionRef>;
  "validation": AuthoringGroupValidation;
  "numeric_check_ids": Array<string>;
  "warnings": Array<Warning>;
};

export type AuthoringGroupGenerated = {
  "version": "authoring-group-generated-v1";
  "content_plan": AuthoringContentPlan;
  "draft": (AuthoringLessonGenerated | AuthoringPracticeGenerated | AuthoringAssessmentGenerated);
};

export type AuthoringGroupJobSummary = {
  "id": string;
  "kind": "authoring";
  "job_revision": number;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
  "title": string;
  "candidate": (AuthoringGroupCandidate | null);
  "created_at": string;
  "updated_at": string;
};

export type AuthoringGroupJobView = {
  "variant": "group";
  "summary": AuthoringGroupJobSummary;
  "request": AuthoringGroupPrepareWrite;
  "preparation": AuthoringGroupPreparationSummary;
  "proposal_id": (string | null);
  "consent_id": (string | null);
  "provider_receipt_id": (string | null);
  "provider_outcome": ("completed" | "failed" | "incomplete" | "cancelled" | "unknown" | null);
  "usage": UsageSnapshot;
  "raw_answer": (string | null);
  "raw_refusal": (string | null);
  "validation": AuthoringGroupValidation;
  "error_code": (string | null);
  "plan_ref": (AuthoringContentPlanRef | null);
  "content_plan": (AuthoringContentPlan | null);
};

export type AuthoringGroupNumericCheckView = {
  "id": string;
  "revision": number;
  "candidate": AuthoringGroupCandidate;
  "target": AuthoringDraftMemberRef;
  "plan": NumericPlan;
  "runtime": NumericRuntimeProfile;
  "operation_sha256": string;
  "decision": "pending" | "approve_once" | "decline";
  "created_at": string;
  "expires_at": string;
  "expired": boolean;
  "job": (JobRef | null);
  "job_revision": (number | null);
  "result": (NumericCheckResult | null);
  "warnings": Array<Warning>;
};

export type AuthoringGroupNumericPreviewWrite = {
  "candidate": AuthoringGroupCandidate;
  "target": AuthoringDraftMemberRef;
};

export type AuthoringGroupPreparationSummary = {
  "context_snapshot_id": string;
  "snapshot_sha256": string;
  "job_input_sha256": string;
  "prepared_input_sha256": string;
  "character_count": number;
  "materials": Array<AuthoringInputMaterial>;
  "warnings": Array<Warning>;
  "targets": Array<AuthoringTargetMaterial>;
};

export type AuthoringGroupPrepareWrite = (AuthoringLessonPrepareWrite | AuthoringPracticePrepareWrite | AuthoringAssessmentPrepareWrite);

export type AuthoringGroupValidation = {
  "schema": "PASS" | "FAIL" | "NOT_RUN";
  "references": "PASS" | "FAIL" | "NOT_RUN";
  "symbol_declarations": "PASS" | "FAIL" | "NOT_RUN";
  "issues": Array<Warning>;
  "mathematical": "NOT_RUN";
  "sources": "NOT_RUN";
  "independent_pedagogy": "NOT_RUN";
  "plan_membership": "PASS" | "FAIL" | "NOT_RUN";
  "private_bindings": "PASS" | "FAIL" | "NOT_RUN";
  "question_checks": Array<AuthoringQuestionQuality>;
};

export type AuthoringInputMaterial = {
  "ref": AuthoringBlockRef;
  "title": string;
  "body_sha256": string;
  "body_bytes": number;
  "material_review": "unreviewed";
  "provenance": RetrievalProvenance;
};

export type AuthoringJobPage = {
  "items": Array<JobSnapshot>;
  "next_cursor": (string | null);
  "total_hint"?: number;
};

export type AuthoringJobReadView = (AuthoringJobView | AuthoringGroupJobView);

export type AuthoringJobSummary = {
  "id": string;
  "kind": "authoring";
  "job_revision": number;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
  "title": string;
  "candidate": (AuthoringCandidate | null);
  "created_at": string;
  "updated_at": string;
};

export type AuthoringJobView = {
  "summary": AuthoringJobSummary;
  "request": AuthoringPrepareWrite;
  "preparation": AuthoringPreparationSummary;
  "proposal_id": (string | null);
  "consent_id": (string | null);
  "provider_receipt_id": (string | null);
  "provider_outcome": ("completed" | "failed" | "incomplete" | "cancelled" | "unknown" | null);
  "usage": UsageSnapshot;
  "raw_answer": (string | null);
  "raw_refusal": (string | null);
  "validation": AuthoringValidation;
  "error_code": (string | null);
};

export type AuthoringLessonGenerated = {
  "output_kind": "lesson";
  "title": string;
  "blocks": Array<AuthoringGeneratedBlock>;
};

export type AuthoringLessonPrepareWrite = {
  "topic": string;
  "prerequisites": Array<string>;
  "objectives": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "source_refs": Array<AuthoringBlockRef>;
  "provider_id": string;
  "target_concept_refs": Array<AuthoringConceptRef>;
  "output_kind": "lesson";
};

export type AuthoringLessonRef = {
  "entity": "lesson";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type AuthoringPageQuery = {
  "cursor"?: string;
  "limit"?: number;
};

export type AuthoringPracticeGenerated = {
  "output_kind": "practice_set";
  "title": string;
  "questions": Array<QuestionDraftPublic>;
  "solutions": Array<GeneratedSolutionAnswer>;
};

export type AuthoringPracticePrepareWrite = {
  "topic": string;
  "prerequisites": Array<string>;
  "objectives": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "source_refs": Array<AuthoringBlockRef>;
  "provider_id": string;
  "target_concept_refs": Array<AuthoringConceptRef>;
  "output_kind": "practice_set";
  "lesson_ref": AuthoringLessonRef;
};

export type AuthoringPreparationSummary = {
  "context_snapshot_id": string;
  "snapshot_sha256": string;
  "job_input_sha256": string;
  "prepared_input_sha256": string;
  "character_count": number;
  "materials": Array<AuthoringInputMaterial>;
  "warnings": Array<Warning>;
};

export type AuthoringPrepareWrite = {
  "topic": string;
  "prerequisites": Array<string>;
  "objectives": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "output_kind": "worked_example";
  "source_refs": Array<AuthoringBlockRef>;
  "provider_id": string;
};

export type AuthoringPrivateSolutionRef = {
  "question": AuthoringQuestionMemberRef;
  "solution_sha256": string;
};

export type AuthoringPrivateSolutionView = {
  "candidate": AuthoringGroupCandidate;
  "ref": AuthoringPrivateSolutionRef;
  "payload": SolutionDraftPrivate;
};

export type AuthoringQuestionMemberRef = {
  "member_key": string;
  "entity": "question";
  "member_sha256": string;
};

export type AuthoringQuestionPlanEntry = {
  "member_key": string;
  "entity": "question";
  "kind": "single_choice" | "text_blank" | "numeric" | "expression" | "calculation";
  "objective_indexes": Array<number>;
  "prerequisite_indexes": Array<number>;
  "depends_on_keys": Array<string>;
};

export type AuthoringQuestionQuality = {
  "question": AuthoringQuestionMemberRef;
  "grading_compatibility": "PASS" | "FAIL" | "NOT_RUN";
  "accepted_answer_membership": "PASS" | "FAIL" | "NOT_RUN";
  "answer_uniqueness": "NOT_RUN";
  "distractor_reasonableness": "NOT_RUN";
  "condition_sufficiency": "NOT_RUN";
  "unit_semantics": "NOT_RUN";
  "solution_grading_semantics": "NOT_RUN";
  "objective_alignment": "NOT_RUN";
  "prerequisite_sufficiency": "NOT_RUN";
};

export type AuthoringTargetMaterial = {
  "ref": AuthoringTargetRef;
  "metadata": (Lesson | Concept);
};

export type AuthoringTargetRef = {
  "entity": "lesson" | "concept";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type AuthoringTextBlockPayload = {
  "version": "content-block-candidate-v1";
  "kind": "orientation" | "definition" | "theorem" | "proof" | "intuition" | "boundary" | "summary" | "text" | "code" | "figure";
  "title": string;
  "body_markdown": string;
  "symbols": Array<WorkedExampleSymbol>;
  "declared_source_refs": Array<AuthoringBlockRef>;
};

export type AuthoringValidation = {
  "schema": "PASS" | "FAIL" | "NOT_RUN";
  "references": "PASS" | "FAIL" | "NOT_RUN";
  "symbol_declarations": "PASS" | "FAIL" | "NOT_RUN";
  "issues": Array<Warning>;
  "mathematical": "NOT_RUN";
  "sources": "NOT_RUN";
  "independent_pedagogy": "NOT_RUN";
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

export type ContentRef = {
  "entity": "course" | "lesson" | "block" | "concept" | "route" | "question" | "practice_set" | "assessment" | "note";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type ErrorDetail = {
  "code": string;
  "message": string;
  "request_id": string;
  "retryable": boolean;
  "details"?: Array<string>;
};

export type GeneratedSolutionAnswer = {
  "question_key": string;
  "grading_kind": "choice_exact" | "text_normalized" | "numeric_tolerance" | "symbolic_review" | "rubric_review";
  "accepted_answers": Array<string>;
  "absolute_tolerance": number;
  "relative_tolerance": number;
  "unit": (string | null);
  "domain_assumptions": Array<string>;
  "solution_markdown": string;
  "rubric_markdown": string;
  "symbols": Array<WorkedExampleSymbol>;
  "numeric_plan": (NumericPlan | null);
};

export type GroupCommon = {
  "topic": string;
  "prerequisites": Array<string>;
  "objectives": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "source_refs": Array<AuthoringBlockRef>;
  "provider_id": string;
  "target_concept_refs": Array<AuthoringConceptRef>;
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

export type LessonCandidateRoot = {
  "entity": "lesson";
  "title": string;
  "objectives": Array<string>;
  "prerequisites": Array<string>;
  "proof_policy": "full" | "declared_dependencies";
  "blocks": Array<AuthoringBlockMemberRef>;
};

export type NumericAssertion = {
  "id": string;
  "expression": string;
  "expected": number;
  "atol": number;
  "rtol": number;
  "unit": string;
};

export type NumericAssertionResult = {
  "id": string;
  "actual": (number | null);
  "passed": boolean;
  "error_code": ("NUMERIC_DOMAIN_ERROR" | "NUMERIC_NONFINITE" | null);
};

export type NumericCheckDecisionAck = {
  "id": string;
  "revision": number;
  "operation_sha256": string;
  "decision": "approve_once" | "decline";
  "applied": true;
  "job": (JobRef | null);
};

export type NumericCheckPreviewWrite = {
  "candidate": AuthoringCandidate;
};

export type NumericCheckResult = {
  "job_id": string;
  "input_sha256": string;
  "operation_sha256": string;
  "outcome": "passed" | "mismatch" | "evaluation_error" | "timeout" | "resource_limit" | "cancelled" | "environment_unavailable" | "outcome_unknown";
  "verdict": "PASS" | "FAIL" | "BLOCKED";
  "started_at": (string | null);
  "finished_at": string;
  "exit_code": (number | null);
  "assertions": Array<NumericAssertionResult>;
  "output_sha256": (string | null);
  "result_sha256": string;
};

export type NumericCheckView = {
  "id": string;
  "revision": number;
  "candidate": AuthoringCandidate;
  "plan": NumericPlan;
  "runtime": NumericRuntimeProfile;
  "operation_sha256": string;
  "decision": "pending" | "approve_once" | "decline";
  "created_at": string;
  "expires_at": string;
  "expired": boolean;
  "job": (JobRef | null);
  "job_revision": (number | null);
  "result": (NumericCheckResult | null);
  "warnings": Array<Warning>;
};

export type NumericPlan = {
  "version": "finite-arithmetic-v1";
  "variables": Array<NumericVariable>;
  "assertions": Array<NumericAssertion>;
  "seed": null;
};

export type NumericRuntimeProfile = {
  "evaluator_version": "finite-arithmetic-v1";
  "evaluator_sha256": string;
  "runtime_manifest_sha256": string;
  "python_version": string;
  "sandbox_version": string;
  "wall_seconds": 5;
  "cpu_seconds": 2;
  "memory_bytes": 268435456;
  "output_bytes": 65536;
  "evaluator_process_limit": 1;
};

export type NumericVariable = {
  "name": string;
  "value": number;
  "unit": string;
};

export type PracticeSetCandidateRoot = {
  "entity": "practice_set";
  "title": string;
  "lesson_ref": AuthoringLessonRef;
  "questions": Array<AuthoringQuestionMemberRef>;
  "feedback_policy": "on_submit_or_reveal";
};

export type QuestionDraftPublic = {
  "member_key": string;
  "kind": "single_choice" | "text_blank" | "numeric" | "expression" | "calculation";
  "stem_markdown": string;
  "choices": Array<Choice>;
  "concept_refs": Array<AuthoringConceptRef>;
  "skill": "recall" | "explain" | "compute" | "derive" | "transfer";
  "exposure_family_key": string;
  "max_score": number;
  "input_instructions": string;
  "declared_source_refs": Array<AuthoringBlockRef>;
  "depends_on_keys": Array<string>;
};

export type RetrievalProvenance = {
  "state": "frozen" | "unresolved";
  "original": (RetrievalRetainedSource | null);
  "citations": Array<Citation>;
  "unresolved_citation_ids": Array<string>;
  "warnings": Array<Warning>;
};

export type RetrievalRetainedSource = {
  "id": string;
  "media_type": string;
  "size": number;
  "sha256": string;
  "rights": string;
  "parser_version": (string | null);
};

export type SolutionDraftPrivate = {
  "question": AuthoringQuestionMemberRef;
  "answer": GeneratedSolutionAnswer;
  "review_status": "needs_review";
};

export type UsageSnapshot = {
  "input_tokens": (number | null);
  "output_tokens": (number | null);
};

export type Warning = {
  "code": string;
  "message": string;
  "locator"?: (string | null);
  "severity": "info" | "warning" | "error";
};

export type WorkedExamplePayload = {
  "version": "worked-example-candidate-v1";
  "kind": "worked_example";
  "title": string;
  "body_markdown": string;
  "symbols": Array<WorkedExampleSymbol>;
  "declared_source_refs": Array<AuthoringBlockRef>;
  "numeric_plan": NumericPlan;
};

export type WorkedExampleSymbol = {
  "name": string;
  "tex": string;
  "domain": string;
  "dimension": string;
};
