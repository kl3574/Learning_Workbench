import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import type { LearningActionResponse } from '../../../../../packages/contracts/generated/api-types'
import { exactRef, validId } from '../assessment/target'
import { DraftStore } from '../../workbench/DraftStore'
import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
export type CompletionDraft = { version: 1; workspace_id: string; route_ref: ContentRef; step_id: string; base_completed: boolean; expected_progress_revision: number; completed: boolean; command_id: string; acknowledged: LearningActionResponse | null }
export function decodeCompletion(raw: string, workspace: string): CompletionDraft {
  const value: unknown = JSON.parse(raw)
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('路线完成候选格式无效。')
  const row = value as Record<string, unknown>, fields = ['version', 'workspace_id', 'route_ref', 'step_id', 'base_completed', 'expected_progress_revision', 'completed', 'command_id', 'acknowledged']
  if (Object.keys(row).length !== fields.length || fields.some(key => !(key in row)) || row.version !== 1 || row.workspace_id !== workspace || !validId(workspace) || !exactRef(row.route_ref, 'route') || !validId(row.step_id) || !validId(row.command_id) || typeof row.base_completed !== 'boolean' || typeof row.completed !== 'boolean' || !Number.isSafeInteger(row.expected_progress_revision) || Number(row.expected_progress_revision) < 1) throw new Error('完成候选归属、基准或布尔标记无效。')
  if (row.acknowledged !== null) { const ack = row.acknowledged as Record<string, unknown>; if (!ack || typeof ack !== 'object' || Object.keys(ack).length !== 2 || !validId(ack.event_id) || ack.progress_revision !== Number(row.expected_progress_revision) + 1) throw new Error('完成回执不对应原基准。') }
  return value as CompletionDraft
}
export const completionKey = (value: CompletionDraft) => `${value.route_ref.id}:${value.route_ref.revision}:${value.step_id}`
export const completionStore = new DraftStore({ name: 'learning-workbench.route-completion-drafts.v1' })
export const useCompletionJournal = createResponseDraftJournal({ store: completionStore, decode: decodeCompletion, dirty: value => !value.acknowledged, key: completionKey })
