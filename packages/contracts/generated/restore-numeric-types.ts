// Generated from PRODUCT_DESIGN.md v3.0.13. DO NOT EDIT.
// spec_sha256: 949e2348902d8b8cb65f560b36fa58039fce75cd2e70c0a9ce9dcd8023160c05
// JSON Schema is the type source; runtime semantic checks remain required.

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

export type JobRef = {
  "id": string;
  "status": "queued" | "running" | "awaiting_approval" | "completed" | "failed" | "cancelled";
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

export type RestoreNumericAssertionBinding = {
  "assertion_id": string;
  "expression_source": RestoreNumericSourceSpan;
  "expected_source": RestoreNumericSourceSpan;
};

export type RestoreNumericCheckPreviewWrite = {
  "candidate": AuthoringCandidate;
  "material": RestoreNumericMaterialWrite;
};

export type RestoreNumericCheckView = {
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
  "owner": "authoring_restore";
  "numeric_material_sha256": string;
};

export type RestoreNumericMaterialView = {
  "owner": "authoring_restore";
  "candidate": AuthoringCandidate;
  "restore_record_sha256": string;
  "source_ref": AuthoringBlockRef;
  "source_material_sha256": string;
  "body_sha256": string;
  "material": RestoreNumericMaterialWrite;
  "numeric_material_sha256": string;
};

export type RestoreNumericMaterialWrite = {
  "version": "restore-numeric-material-v1";
  "symbols": Array<WorkedExampleSymbol>;
  "plan": NumericPlan;
  "variable_bindings": Array<RestoreNumericVariableBinding>;
  "assertion_bindings": Array<RestoreNumericAssertionBinding>;
  "reason": string;
};

export type RestoreNumericSourceSpan = {
  "start_codepoint": number;
  "end_codepoint": number;
  "quote": string;
};

export type RestoreNumericVariableBinding = {
  "variable_name": string;
  "value_source": RestoreNumericSourceSpan;
};

export type Warning = {
  "code": string;
  "message": string;
  "locator"?: (string | null);
  "severity": "info" | "warning" | "error";
};

export type WorkedExampleSymbol = {
  "name": string;
  "tex": string;
  "domain": string;
  "dimension": string;
};
