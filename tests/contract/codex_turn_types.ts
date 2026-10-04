// Compile-only checks of the standalone generated seam. Never executes a turn.
import type {
  CodexCurrentSessionView, CodexTurnControlView, CodexTurnEventPayload,
  CodexOperation, CodexTurnPrepareWrite, SafeCode,
} from '../../packages/contracts/generated/codex-turn-types';
import type { CodexSessionCreateAck } from '../../packages/contracts/generated/codex-bootstrap-types';

declare function accepts<T>(value: T): void;
declare const current: CodexCurrentSessionView;
declare const original: CodexSessionCreateAck;
declare const control: CodexTurnControlView;

accepts<boolean>(current.capabilities.approvals);
accepts<false>(original.capabilities.approvals);
accepts<2>(original.revision);
accepts<string | null>(current.active_turn_id);
accepts<string>(control.approval_controls[0].operation_sha256);
accepts<SafeCode>('CODEX_NEW_OUTBOUND_CONSENT_REQUIRED');
accepts<SafeCode>('PROVIDER_OUTCOME_UNKNOWN');

// @ts-expect-error Current history is not an original bootstrap ACK.
accepts<CodexSessionCreateAck>(current);
// @ts-expect-error Raw upstream errors are not safe error codes.
accepts<SafeCode>('raw upstream error');
// @ts-expect-error The request is a closed application DTO, not the old turn wire.
accepts<CodexTurnPrepareWrite>({ message: 'synthetic', consent_id: 'old' });
// @ts-expect-error SSE payloads cannot mix another branch's fields.
accepts<CodexTurnEventPayload>({ type: 'answer_delta', text: ' \n', approval_id: 'other' });
// @ts-expect-error Upstream tool definitions do not extend the closed operation union.
accepts<CodexOperation>({ kind: 'network', destination: 'example.invalid' });

export function eventKind(payload: CodexTurnEventPayload): string {
  switch (payload.type) {
    case 'status': return payload.job.id;
    case 'answer_delta': return payload.text;
    case 'approval_required': return payload.approval_id;
    case 'usage': return String(payload.usage.input_tokens);
    case 'manifest_ready': return payload.manifest_sha256;
    case 'terminal': return payload.outcome;
  }
  const exhaustive: never = payload;
  return exhaustive;
}

export function operationKind(operation: CodexOperation): string {
  switch (operation.kind) {
    case 'command': return operation.command_text;
    case 'file_change': return operation.files[0].path;
    case 'unsupported': return operation.reason;
  }
  const exhaustive: never = operation;
  return exhaustive;
}
