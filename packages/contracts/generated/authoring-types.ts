// Generated from PRODUCT_DESIGN.md v3.0.6. DO NOT EDIT.
// spec_sha256: 30220c34fe7312887f5bcb1c67406c9638f1719ff3ed7bc9e95d7d5085b5d924
// JSON Schema is the type source; runtime semantic checks remain required.

export type ApprovalDecision = {
  "operation_sha256": string;
  "decision": "approve_once" | "decline";
  "expected_revision": number;
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

export type AuthoringPageQuery = {
  "cursor"?: string;
  "limit"?: number;
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

export type AuthoringValidation = {
  "schema": "PASS" | "FAIL" | "NOT_RUN";
  "references": "PASS" | "FAIL" | "NOT_RUN";
  "symbol_declarations": "PASS" | "FAIL" | "NOT_RUN";
  "issues": Array<Warning>;
  "mathematical": "NOT_RUN";
  "sources": "NOT_RUN";
  "independent_pedagogy": "NOT_RUN";
};

export type Citation = {
  "id": string;
  "title": string;
  "url"?: (string | null);
  "locator": string;
  "source_sha256"?: (string | null);
  "verification": "verified" | "unverified" | "user_supplied";
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
