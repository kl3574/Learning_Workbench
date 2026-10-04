// Generated from PRODUCT_DESIGN.md v3.0.15. DO NOT EDIT.
// spec_sha256: b140764e416dac644b45ed8c0b6bd1c71eb9b578cb3b5b19d2530a94cea4cfec
// JSON Schema is the type source; runtime semantic checks remain required.

export type CodexBootstrapDecisionAck = {
  "preparation_id": string;
  "revision": 2;
  "actor_session_id": string;
  "decision": "approve_once" | "decline";
  "operation_sha256": string;
  "consent_id": (string | null);
  "decided_at": string;
};

export type CodexBootstrapFeatures = {
  "approvals": false;
  "interrupt": false;
  "artifacts": false;
};

export type CodexBootstrapPreparationView = {
  "id": string;
  "revision": number;
  "actor_session_id": string;
  "status": "pending" | "approved" | "declined" | "consumed";
  "scope": CodexBootstrapScope;
  "operation_sha256": string;
  "created_at": string;
  "expires_at": string;
  "consent_id": (string | null);
  "session_id": (string | null);
  "validity": "current" | "expired" | "changed" | "unavailable" | "closed";
};

export type CodexBootstrapPreparationWrite = {
  "sandbox_root_id": string;
  "allowed_actions": [];
};

export type CodexBootstrapScope = {
  "version": "codex-local-session-bootstrap-v1";
  "sandbox_root_id": string;
  "sandbox_label": string;
  "allowed_actions": [];
  "adapter_version": string;
  "bootstrap_profile_sha256": string;
};

export type CodexSessionCreateAck = {
  "id": string;
  "revision": 2;
  "status": "ready";
  "capabilities": CodexBootstrapFeatures;
  "adapter_version": string;
};

export type CodexSessionCreateWrite = {
  "sandbox_root_id": string;
  "consent_id": string;
  "allowed_actions": [];
};

export type CodexSessionView = {
  "id": string;
  "revision": number;
  "status": "initializing" | "ready" | "failed" | "unknown";
  "active_turn_id": null;
  "adapter_version": string;
  "capabilities": CodexBootstrapFeatures;
};
