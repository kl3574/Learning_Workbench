import type { ApprovalDecision } from '../../../../../packages/contracts/generated/api-types'
import type { CodexTurnControlView, GenericApprovalView, GenericApprovalDecisionAck } from '../../../../../packages/contracts/generated/codex-turn-types'
import { DraftStore } from '../../workbench/DraftStore'
import { approvalClient, type ApprovalPort } from './approvalClient'
export type ApprovalCommand = {
 version: 1; workspace_id: string; actor_session_id: string; command_id: string; target_id: string;
 route: 'POST /api/v1/approvals/{id}/decision';
 basis: { kind: 'approve'; view: GenericApprovalView } | { kind: 'decline'; control: CodexTurnControlView };
 body: ApprovalDecision; ack: GenericApprovalDecisionAck | null; error: { status: number; code: string | null } | null
}
export const approvalStore = new DraftStore({ name: 'learning-workbench.codex-operation-commands.v1' })
export async function dispatchApprovalCommand(command: ApprovalCommand, port: Pick<ApprovalPort, 'decide'> = approvalClient, _store = approvalStore): Promise<ApprovalCommand> {
 return { ...command, ack: await port.decide(command.target_id, command.body, command.command_id) }
}
