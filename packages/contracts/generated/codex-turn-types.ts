// Generated from PRODUCT_DESIGN.md v3.0.15. DO NOT EDIT.
// spec_sha256: b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec
// JSON Schema is the type source; runtime semantic checks remain required.

export type ActualUsageCost = {
  "kind": "actual";
  "currency": "USD";
  "amount": number;
  "source": "provider_reported";
};

export type CodexApprovalControl = {
  "id": string;
  "revision": number;
  "operation_sha256": string;
  "decision": "pending" | "approve_once" | "decline";
  "validity": "current" | "expired" | "changed" | "unavailable" | "closed";
};

export type CodexArtifactEntry = {
  "artifact_id": string;
  "logical_path": string;
  "size": number;
  "sha256": string;
  "media_type": string;
  "scan": "PASS";
  "import_kind": ("markdown" | "html" | "learnpack" | null);
};

export type CodexArtifactExcluded = {
  "entry_id": string;
  "reason": ("CODEX_PROTOCOL_INVALID" | "CODEX_PROFILE_CHANGED" | "CODEX_RUNTIME_UNAVAILABLE" | "CODEX_BINDING_INVALID" | "CODEX_HISTORY_DAMAGED" | "CODEX_INPUT_PROOF_UNAVAILABLE" | "CODEX_OPERATION_UNSUPPORTED" | "CODEX_NEW_OUTBOUND_CONSENT_REQUIRED" | "CODEX_TIMEOUT" | "CODEX_RESOURCE_LIMIT" | "CODEX_CANCELLED" | "CODEX_OUTCOME_UNKNOWN" | "CODEX_OPERATION_FAILED" | "CODEX_ARTIFACT_REJECTED" | "CODEX_ARTIFACT_MISSING" | "CODEX_SOURCE_CHANGED" | "CODEX_SOURCE_UNAVAILABLE" | "CODEX_APPROVAL_EXPIRED" | "CODEX_CONSENT_EXPIRED" | "CODEX_CONSENT_REVOKED" | "CODEX_BUDGET_EXCEEDED" | "POLICY_DENIED" | "ASSESSMENT_ACTIVE" | "CAPABILITY_UNSUPPORTED" | "PROVIDER_CONFIGURATION_CHANGED" | "PROVIDER_SECRET_UNAVAILABLE" | "OUTBOUND_SOURCE_CHANGED" | "OUTBOUND_SOURCE_UNAVAILABLE" | "CONSENT_REQUIRED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED" | "OUTBOUND_BUDGET_EXCEEDED" | "PROVIDER_TIMEOUT" | "PROVIDER_CANCELLED" | "PROVIDER_TRANSPORT_ERROR" | "PROVIDER_PROTOCOL_ERROR" | "PROVIDER_OUTCOME_UNKNOWN" | "PROVIDER_USAGE_INCONSISTENT" | "PROVIDER_REFUSAL" | "PROVIDER_INCOMPLETE");
};

export type CodexArtifactImportItem = {
  "artifact_id": string;
  "source_sha256": string;
  "import_id": string;
  "job": JobRef;
};

export type CodexArtifactImportView = {
  "job": JobRef;
  "session_id": string;
  "turn_id": string;
  "manifest_sha256": string;
  "actor_session_id": string;
  "items": Array<CodexArtifactImportItem>;
};

export type CodexArtifactImportWrite = {
  "turn_id": string;
  "artifact_ids": Array<string>;
  "expected_manifest_sha256": string;
};

export type CodexArtifactManifest = {
  "version": "codex-artifact-manifest-v1";
  "id": string;
  "revision": 1;
  "session_id": string;
  "turn_id": string;
  "run_id": string;
  "source_job_id": string;
  "source_outcome": "completed" | "failed" | "incomplete" | "cancelled" | "unknown";
  "runtime_profile_sha256": string;
  "terminal_receipt_sha256": string;
  "scan_profile_sha256": string;
  "created_at": string;
  "entries": Array<CodexArtifactEntry>;
  "excluded": Array<CodexArtifactExcluded>;
  "total_bytes": number;
  "mathematical": "NOT_RUN";
  "sources": "NOT_RUN";
  "independent_pedagogy": "NOT_RUN";
};

export type CodexArtifactManifestView = {
  "manifest": CodexArtifactManifest;
  "manifest_sha256": string;
};

export type CodexBlockRef = {
  "entity": "block";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type CodexCommandOperation = {
  "kind": "command";
  "command_text": string;
  "cwd": string;
  "executable_sha256": string;
  "environment_sha256": string;
  "read_files": Array<CodexOperationFile>;
  "writable_area": "turn_outputs";
  "filesystem_scope_sha256": string;
  "network": "denied";
  "operation_profile_sha256": string;
};

export type CodexConsentControl = {
  "id": string;
  "revision": number;
  "status": "active" | "revoked" | "expired";
};

export type CodexConsentCreateAck = {
  "id": string;
  "revision": 1;
  "status": "active";
  "actor_session_id": string;
  "proposal_id": string;
  "proposal_sha256": string;
  "summary": CodexFrozenOutboundSummary;
};

export type CodexConsentCreateWrite = {
  "proposal_id": string;
  "proposal_sha256": string;
};

export type CodexConsentProposalView = {
  "id": string;
  "proposal_sha256": string;
  "summary": CodexFrozenOutboundSummary;
  "validity": "current" | "stale" | "expired" | "unavailable";
  "consent_id": (string | null);
  "warnings": Array<ProposalWarning>;
};

export type CodexConsentView = {
  "id": string;
  "revision": number;
  "status": "active" | "revoked" | "expired";
  "actor_session_id": string;
  "proposal_id": string;
  "proposal_sha256": string;
  "summary": CodexFrozenOutboundSummary;
  "created_at": string;
  "expires_at": string;
  "revoked_at": (string | null);
  "dispatch": (CodexDispatchView | null);
};

export type CodexCurrentFeatures = {
  "approvals": boolean;
  "interrupt": boolean;
  "artifacts": boolean;
};

export type CodexCurrentSessionView = {
  "id": string;
  "revision": number;
  "status": "initializing" | "ready" | "failed" | "unknown";
  "active_turn_id": (string | null);
  "adapter_version": string;
  "capabilities": CodexCurrentFeatures;
};

export type CodexDeniedOperation = {
  "kind": "unsupported";
  "category": "network" | "permission_expansion" | "unbound_operation" | "unsupported_tool";
  "reason": ("CODEX_PROTOCOL_INVALID" | "CODEX_PROFILE_CHANGED" | "CODEX_RUNTIME_UNAVAILABLE" | "CODEX_BINDING_INVALID" | "CODEX_HISTORY_DAMAGED" | "CODEX_INPUT_PROOF_UNAVAILABLE" | "CODEX_OPERATION_UNSUPPORTED" | "CODEX_NEW_OUTBOUND_CONSENT_REQUIRED" | "CODEX_TIMEOUT" | "CODEX_RESOURCE_LIMIT" | "CODEX_CANCELLED" | "CODEX_OUTCOME_UNKNOWN" | "CODEX_OPERATION_FAILED" | "CODEX_ARTIFACT_REJECTED" | "CODEX_ARTIFACT_MISSING" | "CODEX_SOURCE_CHANGED" | "CODEX_SOURCE_UNAVAILABLE" | "CODEX_APPROVAL_EXPIRED" | "CODEX_CONSENT_EXPIRED" | "CODEX_CONSENT_REVOKED" | "CODEX_BUDGET_EXCEEDED" | "POLICY_DENIED" | "ASSESSMENT_ACTIVE" | "CAPABILITY_UNSUPPORTED" | "PROVIDER_CONFIGURATION_CHANGED" | "PROVIDER_SECRET_UNAVAILABLE" | "OUTBOUND_SOURCE_CHANGED" | "OUTBOUND_SOURCE_UNAVAILABLE" | "CONSENT_REQUIRED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED" | "OUTBOUND_BUDGET_EXCEEDED" | "PROVIDER_TIMEOUT" | "PROVIDER_CANCELLED" | "PROVIDER_TRANSPORT_ERROR" | "PROVIDER_PROTOCOL_ERROR" | "PROVIDER_OUTCOME_UNKNOWN" | "PROVIDER_USAGE_INCONSISTENT" | "PROVIDER_REFUSAL" | "PROVIDER_INCOMPLETE");
};

export type CodexDispatchView = {
  "id": string;
  "job": JobRef;
  "started_at": (string | null);
  "finished_at": (string | null);
  "consumed_provider_calls": number;
  "input_tokens": (number | null);
  "output_tokens": (number | null);
  "elapsed_ms": (number | null);
  "cost": (UnknownUsageCost | EstimatedUsageCost | ActualUsageCost);
  "outcome": ("completed" | "failed" | "incomplete" | "cancelled" | "unknown" | null);
  "error_code": ("CODEX_PROTOCOL_INVALID" | "CODEX_PROFILE_CHANGED" | "CODEX_RUNTIME_UNAVAILABLE" | "CODEX_BINDING_INVALID" | "CODEX_HISTORY_DAMAGED" | "CODEX_INPUT_PROOF_UNAVAILABLE" | "CODEX_OPERATION_UNSUPPORTED" | "CODEX_NEW_OUTBOUND_CONSENT_REQUIRED" | "CODEX_TIMEOUT" | "CODEX_RESOURCE_LIMIT" | "CODEX_CANCELLED" | "CODEX_OUTCOME_UNKNOWN" | "CODEX_OPERATION_FAILED" | "CODEX_ARTIFACT_REJECTED" | "CODEX_ARTIFACT_MISSING" | "CODEX_SOURCE_CHANGED" | "CODEX_SOURCE_UNAVAILABLE" | "CODEX_APPROVAL_EXPIRED" | "CODEX_CONSENT_EXPIRED" | "CODEX_CONSENT_REVOKED" | "CODEX_BUDGET_EXCEEDED" | "POLICY_DENIED" | "ASSESSMENT_ACTIVE" | "CAPABILITY_UNSUPPORTED" | "PROVIDER_CONFIGURATION_CHANGED" | "PROVIDER_SECRET_UNAVAILABLE" | "OUTBOUND_SOURCE_CHANGED" | "OUTBOUND_SOURCE_UNAVAILABLE" | "CONSENT_REQUIRED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED" | "OUTBOUND_BUDGET_EXCEEDED" | "PROVIDER_TIMEOUT" | "PROVIDER_CANCELLED" | "PROVIDER_TRANSPORT_ERROR" | "PROVIDER_PROTOCOL_ERROR" | "PROVIDER_OUTCOME_UNKNOWN" | "PROVIDER_USAGE_INCONSISTENT" | "PROVIDER_REFUSAL" | "PROVIDER_INCOMPLETE" | null);
};

export type CodexFileChange = {
  "path": string;
  "action": "add" | "update" | "delete";
  "before_sha256": (string | null);
  "after_sha256": (string | null);
  "before_size": (number | null);
  "after_size": (number | null);
  "diff": string;
};

export type CodexFileOperation = {
  "kind": "file_change";
  "files": Array<CodexFileChange>;
  "operation_profile_sha256": string;
};

export type CodexFrozenOutboundSummary = {
  "version": "codex-outbound-summary-v1";
  "preparation_id": string;
  "preparation_sha256": string;
  "session_id": string;
  "turn_id": string;
  "job_id": string;
  "source_job_revision": number;
  "source_input_sha256": string;
  "provider_id": string;
  "provider_revision": number;
  "config_sha256": string;
  "adapter": "codex_app_server";
  "adapter_version": string;
  "endpoint": string;
  "endpoint_policy": "public_https" | "explicit_loopback";
  "model": string;
  "context_snapshot_id": string;
  "context_snapshot_sha256": string;
  "input_sha256": string;
  "request_body_sha256": string;
  "messages": Array<MessageSummary>;
  "references": Array<ReferenceSummary>;
  "input_character_count": number;
  "input_token_assurance": (LocalExactInputTokens | LocalUpperBoundInputTokens);
  "budget": CodexOutboundBudgetWrite;
  "tools": CodexLocalToolBudget;
  "runtime": CodexTurnRuntimeSummary;
  "cost_estimate": (UnknownCostEstimate | EstimatedCostEstimate);
  "created_at": string;
  "expires_at": string;
};

export type CodexInterruptAck = {
  "id": string;
  "turn_id": string;
  "status": "interrupt_requested" | "already_terminal";
};

export type CodexInterruptWrite = {
  "turn_id": string;
  "expected_session_revision": number;
};

export type CodexLocalToolBudget = {
  "max_tool_calls": number;
  "wall_seconds": number;
};

export type CodexOperation = (CodexCommandOperation | CodexFileOperation | CodexDeniedOperation);

export type CodexOperationFile = {
  "path": string;
  "size": number;
  "sha256": string;
};

export type CodexOutboundBudgetWrite = {
  "max_input_tokens": number;
  "max_output_tokens": number;
  "max_provider_calls": 1;
  "max_search_calls": 0;
  "max_cost_usd": (number | null);
};

export type CodexOutboundPreviewWrite = {
  "preparation_id": string;
  "preparation_sha256": string;
  "expected_job_revision": number;
  "expected_provider_revision": number;
  "budget": CodexOutboundBudgetWrite;
  "expires_at": string;
};

export type CodexTurnAnswerEvent = {
  "type": "answer_delta";
  "text": string;
};

export type CodexTurnApprovalEvent = {
  "type": "approval_required";
  "approval_id": string;
};

export type CodexTurnControlView = {
  "id": string;
  "session_id": string;
  "actor_session_id": string;
  "job": JobRef;
  "job_revision": number;
  "run_revision": number;
  "last_seq": number;
  "cancel_requested": boolean;
  "execution": "not_started" | "active" | "terminal";
  "outcome": ("completed" | "failed" | "incomplete" | "cancelled" | "unknown" | null);
  "approval_ids": Array<string>;
  "approval_controls": Array<CodexApprovalControl>;
  "consent_control": (CodexConsentControl | null);
  "manifest_id": (string | null);
  "created_at": string;
  "started_at": (string | null);
  "finished_at": (string | null);
  "error_code": ("CODEX_PROTOCOL_INVALID" | "CODEX_PROFILE_CHANGED" | "CODEX_RUNTIME_UNAVAILABLE" | "CODEX_BINDING_INVALID" | "CODEX_HISTORY_DAMAGED" | "CODEX_INPUT_PROOF_UNAVAILABLE" | "CODEX_OPERATION_UNSUPPORTED" | "CODEX_NEW_OUTBOUND_CONSENT_REQUIRED" | "CODEX_TIMEOUT" | "CODEX_RESOURCE_LIMIT" | "CODEX_CANCELLED" | "CODEX_OUTCOME_UNKNOWN" | "CODEX_OPERATION_FAILED" | "CODEX_ARTIFACT_REJECTED" | "CODEX_ARTIFACT_MISSING" | "CODEX_SOURCE_CHANGED" | "CODEX_SOURCE_UNAVAILABLE" | "CODEX_APPROVAL_EXPIRED" | "CODEX_CONSENT_EXPIRED" | "CODEX_CONSENT_REVOKED" | "CODEX_BUDGET_EXCEEDED" | "POLICY_DENIED" | "ASSESSMENT_ACTIVE" | "CAPABILITY_UNSUPPORTED" | "PROVIDER_CONFIGURATION_CHANGED" | "PROVIDER_SECRET_UNAVAILABLE" | "OUTBOUND_SOURCE_CHANGED" | "OUTBOUND_SOURCE_UNAVAILABLE" | "CONSENT_REQUIRED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED" | "OUTBOUND_BUDGET_EXCEEDED" | "PROVIDER_TIMEOUT" | "PROVIDER_CANCELLED" | "PROVIDER_TRANSPORT_ERROR" | "PROVIDER_PROTOCOL_ERROR" | "PROVIDER_OUTCOME_UNKNOWN" | "PROVIDER_USAGE_INCONSISTENT" | "PROVIDER_REFUSAL" | "PROVIDER_INCOMPLETE" | null);
};

export type CodexTurnEvent = {
  "turn_id": string;
  "run_id": string;
  "seq": number;
  "occurred_at": string;
  "payload": (CodexTurnStatusEvent | CodexTurnAnswerEvent | CodexTurnApprovalEvent | CodexTurnUsageEvent | CodexTurnManifestEvent | CodexTurnTerminalEvent);
};

export type CodexTurnEventPayload = (CodexTurnStatusEvent | CodexTurnAnswerEvent | CodexTurnApprovalEvent | CodexTurnUsageEvent | CodexTurnManifestEvent | CodexTurnTerminalEvent);

export type CodexTurnManifestEvent = {
  "type": "manifest_ready";
  "manifest_id": string;
  "manifest_sha256": string;
};

export type CodexTurnPage = {
  "items": Array<CodexTurnControlView>;
  "next_cursor": (string | null);
};

export type CodexTurnPreparationSummary = {
  "context_snapshot_id": string;
  "snapshot_sha256": string;
  "job_input_sha256": string;
  "prepared_input_sha256": string;
  "runtime": CodexTurnRuntimeSummary;
  "character_count": number;
  "materials": Array<ReferenceSummary>;
  "history_turn_ids": Array<string>;
  "tools": CodexLocalToolBudget;
  "warnings": Array<CodexTurnWarning>;
};

export type CodexTurnPreparationView = {
  "id": string;
  "preparation_sha256": string;
  "actor_session_id": string;
  "session_id": string;
  "session_revision": number;
  "turn_id": string;
  "job": JobRef;
  "request": CodexTurnPrepareWrite;
  "summary": CodexTurnPreparationSummary;
  "created_at": string;
  "proposal_id": (string | null);
  "consent_id": (string | null);
  "validity": "current" | "changed" | "unavailable" | "closed";
};

export type CodexTurnPrepareWrite = {
  "message": string;
  "context_refs": Array<CodexBlockRef>;
  "expected_session_revision": number;
  "provider_id": string;
  "tools": CodexLocalToolBudget;
};

export type CodexTurnResultView = {
  "control": CodexTurnControlView;
  "preparation_id": string;
  "answer_markdown": string;
  "output_sha256": (string | null);
  "output_state": "none" | "partial" | "complete";
  "usage": UsageSnapshot;
  "mathematical": "NOT_RUN";
  "sources": "NOT_RUN";
  "independent_pedagogy": "NOT_RUN";
};

export type CodexTurnRuntimeSummary = {
  "profile_sha256": string;
  "cpu_seconds": 60;
  "memory_bytes": 2147483648;
  "file_bytes": 16777216;
  "protocol_output_bytes": 16777216;
  "file_descriptors": 128;
  "processes": 16;
  "core_bytes": 0;
  "command_network": "denied";
  "writable_area": "turn_outputs";
};

export type CodexTurnStartAck = {
  "turn_id": string;
  "session_revision": number;
  "job": JobRef;
};

export type CodexTurnStartWrite = {
  "preparation_id": string;
  "preparation_sha256": string;
  "consent_id": string;
  "expected_session_revision": number;
};

export type CodexTurnStatusEvent = {
  "type": "status";
  "job": JobRef;
  "run_revision": number;
};

export type CodexTurnTerminalEvent = {
  "type": "terminal";
  "outcome": "completed" | "failed" | "incomplete" | "cancelled" | "unknown";
  "error_code": ("CODEX_PROTOCOL_INVALID" | "CODEX_PROFILE_CHANGED" | "CODEX_RUNTIME_UNAVAILABLE" | "CODEX_BINDING_INVALID" | "CODEX_HISTORY_DAMAGED" | "CODEX_INPUT_PROOF_UNAVAILABLE" | "CODEX_OPERATION_UNSUPPORTED" | "CODEX_NEW_OUTBOUND_CONSENT_REQUIRED" | "CODEX_TIMEOUT" | "CODEX_RESOURCE_LIMIT" | "CODEX_CANCELLED" | "CODEX_OUTCOME_UNKNOWN" | "CODEX_OPERATION_FAILED" | "CODEX_ARTIFACT_REJECTED" | "CODEX_ARTIFACT_MISSING" | "CODEX_SOURCE_CHANGED" | "CODEX_SOURCE_UNAVAILABLE" | "CODEX_APPROVAL_EXPIRED" | "CODEX_CONSENT_EXPIRED" | "CODEX_CONSENT_REVOKED" | "CODEX_BUDGET_EXCEEDED" | "POLICY_DENIED" | "ASSESSMENT_ACTIVE" | "CAPABILITY_UNSUPPORTED" | "PROVIDER_CONFIGURATION_CHANGED" | "PROVIDER_SECRET_UNAVAILABLE" | "OUTBOUND_SOURCE_CHANGED" | "OUTBOUND_SOURCE_UNAVAILABLE" | "CONSENT_REQUIRED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED" | "OUTBOUND_BUDGET_EXCEEDED" | "PROVIDER_TIMEOUT" | "PROVIDER_CANCELLED" | "PROVIDER_TRANSPORT_ERROR" | "PROVIDER_PROTOCOL_ERROR" | "PROVIDER_OUTCOME_UNKNOWN" | "PROVIDER_USAGE_INCONSISTENT" | "PROVIDER_REFUSAL" | "PROVIDER_INCOMPLETE" | null);
};

export type CodexTurnUsageEvent = {
  "type": "usage";
  "usage": UsageSnapshot;
};

export type CodexTurnWarning = {
  "code": string;
  "message": string;
  "locator": (string | null);
  "severity": "info" | "warning" | "error";
};

export type ContentRef = {
  "entity": "course" | "lesson" | "block" | "concept" | "route" | "question" | "practice_set" | "assessment" | "note";
  "id": string;
  "revision": number;
  "sha256": string;
};

export type EstimatedCostEstimate = {
  "kind": "estimated";
  "currency": "USD";
  "maximum_estimated_cost": number;
  "pricing_sha256": string;
};

export type EstimatedUsageCost = {
  "kind": "estimated";
  "currency": "USD";
  "amount": number;
  "pricing_sha256": string;
};

export type GenericApprovalDecisionAck = {
  "id": string;
  "revision": 2;
  "actor_session_id": string;
  "operation_sha256": string;
  "decision": "approve_once" | "decline";
  "applied": true;
  "session_id": string;
  "turn_id": string;
  "run_id": string;
  "job": JobRef;
};

export type GenericApprovalView = {
  "id": string;
  "revision": number;
  "actor_session_id": string;
  "session_id": string;
  "turn_id": string;
  "run_id": string;
  "job": JobRef;
  "job_revision": number;
  "operation": (CodexCommandOperation | CodexFileOperation | CodexDeniedOperation);
  "operation_sha256": string;
  "created_at": string;
  "expires_at": string;
  "decision": "pending" | "approve_once" | "decline";
  "validity": "current" | "expired" | "changed" | "unavailable" | "closed";
  "execution": "not_started" | "started" | "completed" | "failed" | "unknown";
  "decided_at": (string | null);
  "started_at": (string | null);
  "finished_at": (string | null);
  "result_sha256": (string | null);
  "error_code": ("CODEX_PROTOCOL_INVALID" | "CODEX_PROFILE_CHANGED" | "CODEX_RUNTIME_UNAVAILABLE" | "CODEX_BINDING_INVALID" | "CODEX_HISTORY_DAMAGED" | "CODEX_INPUT_PROOF_UNAVAILABLE" | "CODEX_OPERATION_UNSUPPORTED" | "CODEX_NEW_OUTBOUND_CONSENT_REQUIRED" | "CODEX_TIMEOUT" | "CODEX_RESOURCE_LIMIT" | "CODEX_CANCELLED" | "CODEX_OUTCOME_UNKNOWN" | "CODEX_OPERATION_FAILED" | "CODEX_ARTIFACT_REJECTED" | "CODEX_ARTIFACT_MISSING" | "CODEX_SOURCE_CHANGED" | "CODEX_SOURCE_UNAVAILABLE" | "CODEX_APPROVAL_EXPIRED" | "CODEX_CONSENT_EXPIRED" | "CODEX_CONSENT_REVOKED" | "CODEX_BUDGET_EXCEEDED" | "POLICY_DENIED" | "ASSESSMENT_ACTIVE" | "CAPABILITY_UNSUPPORTED" | "PROVIDER_CONFIGURATION_CHANGED" | "PROVIDER_SECRET_UNAVAILABLE" | "OUTBOUND_SOURCE_CHANGED" | "OUTBOUND_SOURCE_UNAVAILABLE" | "CONSENT_REQUIRED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED" | "OUTBOUND_BUDGET_EXCEEDED" | "PROVIDER_TIMEOUT" | "PROVIDER_CANCELLED" | "PROVIDER_TRANSPORT_ERROR" | "PROVIDER_PROTOCOL_ERROR" | "PROVIDER_OUTCOME_UNKNOWN" | "PROVIDER_USAGE_INCONSISTENT" | "PROVIDER_REFUSAL" | "PROVIDER_INCOMPLETE" | null);
};

export type JobRef = {
  "id": string;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
};

export type LocalExactInputTokens = {
  "kind": "local_exact";
  "input_tokens": number;
  "checker_version": string;
  "proof_sha256": string;
  "request_body_sha256": string;
};

export type LocalUpperBoundInputTokens = {
  "kind": "local_upper_bound";
  "input_tokens_upper_bound": number;
  "checker_version": string;
  "proof_sha256": string;
  "request_body_sha256": string;
};

export type MessageSummary = {
  "role": "system" | "user" | "assistant";
  "character_count": number;
  "content_sha256": string;
};

export type ProposalWarning = {
  "code": "price_unknown" | "estimate_not_guaranteed" | "provider_changed" | "source_changed" | "source_unavailable" | "job_unavailable" | "proposal_expired" | "capability_unavailable";
  "message": string;
};

export type ReferenceSummary = {
  "ref": ContentRef;
  "title": string;
  "locator": string;
  "character_count": number;
  "excerpt_sha256": string;
};

export type SafeCode = ("CODEX_PROTOCOL_INVALID" | "CODEX_PROFILE_CHANGED" | "CODEX_RUNTIME_UNAVAILABLE" | "CODEX_BINDING_INVALID" | "CODEX_HISTORY_DAMAGED" | "CODEX_INPUT_PROOF_UNAVAILABLE" | "CODEX_OPERATION_UNSUPPORTED" | "CODEX_NEW_OUTBOUND_CONSENT_REQUIRED" | "CODEX_TIMEOUT" | "CODEX_RESOURCE_LIMIT" | "CODEX_CANCELLED" | "CODEX_OUTCOME_UNKNOWN" | "CODEX_OPERATION_FAILED" | "CODEX_ARTIFACT_REJECTED" | "CODEX_ARTIFACT_MISSING" | "CODEX_SOURCE_CHANGED" | "CODEX_SOURCE_UNAVAILABLE" | "CODEX_APPROVAL_EXPIRED" | "CODEX_CONSENT_EXPIRED" | "CODEX_CONSENT_REVOKED" | "CODEX_BUDGET_EXCEEDED" | "POLICY_DENIED" | "ASSESSMENT_ACTIVE" | "CAPABILITY_UNSUPPORTED" | "PROVIDER_CONFIGURATION_CHANGED" | "PROVIDER_SECRET_UNAVAILABLE" | "OUTBOUND_SOURCE_CHANGED" | "OUTBOUND_SOURCE_UNAVAILABLE" | "CONSENT_REQUIRED" | "CONSENT_REVOKED" | "CONSENT_EXPIRED" | "OUTBOUND_BUDGET_EXCEEDED" | "PROVIDER_TIMEOUT" | "PROVIDER_CANCELLED" | "PROVIDER_TRANSPORT_ERROR" | "PROVIDER_PROTOCOL_ERROR" | "PROVIDER_OUTCOME_UNKNOWN" | "PROVIDER_USAGE_INCONSISTENT" | "PROVIDER_REFUSAL" | "PROVIDER_INCOMPLETE");

export type UnknownCostEstimate = {
  "kind": "unknown";
  "currency": "USD";
};

export type UnknownUsageCost = {
  "kind": "unknown";
  "currency": "USD";
};

export type UsageSnapshot = {
  "input_tokens": (number | null);
  "output_tokens": (number | null);
};
