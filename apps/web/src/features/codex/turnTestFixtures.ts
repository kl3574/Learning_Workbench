import { vi } from 'vitest'
import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
import type { CodexTurnControlView, CodexTurnPreparationView, CodexTurnPrepareWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import { actor, codexSession, session, workspace } from './bootstrapTestFixtures'
import type { TurnPort } from './turnClient'
export const turnBody = (): CodexTurnPrepareWrite => ({ message: '  原文 α\n中文😀  ', context_refs: [], expected_session_revision: 2, provider_id: 'codex_local', tools: { max_tool_calls: 0, wall_seconds: 30 } })
export const turnPreparation = (request = turnBody()): CodexTurnPreparationView => ({
 id: 'turn_preparation_test', preparation_sha256: 'a'.repeat(64), actor_session_id: actor, session_id: codexSession().id,
 session_revision: 3, turn_id: 'turn_test', job: { id: 'job_turn_test', status: 'awaiting_approval' }, request,
 summary: { context_snapshot_id: 'snapshot_test', snapshot_sha256: 'a'.repeat(64), job_input_sha256: 'a'.repeat(64), prepared_input_sha256: 'a'.repeat(64),
  runtime: { profile_sha256: 'a'.repeat(64), cpu_seconds: 60, memory_bytes: 2147483648, file_bytes: 16777216, protocol_output_bytes: 16777216, file_descriptors: 128, processes: 16, core_bytes: 0, command_network: 'denied', writable_area: 'turn_outputs' },
  character_count: 100, materials: [], history_turn_ids: [], tools: request.tools, warnings: [] },
 created_at: '2026-10-04T00:00:00Z', proposal_id: null, consent_id: null, validity: 'unavailable',
})
export const turnControl = (): CodexTurnControlView => ({ id: 'turn_test', session_id: codexSession().id, actor_session_id: actor,
 job: { id: 'job_turn_test', status: 'awaiting_approval' }, job_revision: 1, run_revision: 1, last_seq: 1, cancel_requested: false,
 execution: 'not_started', outcome: null, approval_ids: [], approval_controls: [], consent_control: null, manifest_id: null,
 created_at: '2026-10-04T00:00:00Z', started_at: null, finished_at: null, error_code: null })
export const turnCancelledJob = (): JobSnapshot => ({ id: 'job_turn_test', workspace_id: workspace, kind: 'codex_turn',
 status: 'cancelled', revision: 2, created_at: '2026-10-04T00:00:00Z', updated_at: '2026-10-04T00:00:01Z',
 progress: { completed: 0, total: null, label: 'cancelled' }, result_refs: [], warnings: [], error: null })
export const turnPort = (): TurnPort => ({ session: vi.fn(async () => session()), current: vi.fn(async () => codexSession()),
 prepare: vi.fn<TurnPort['prepare']>(async (_id, request) => turnPreparation(request)), preparation: vi.fn(async () => turnPreparation()),
 control: vi.fn(async () => turnControl()), turns: vi.fn(async () => ({ items: [turnControl()], next_cursor: null })),
 cancel: vi.fn<TurnPort['cancel']>(async id => ({ ...turnCancelledJob(), id })),
})
