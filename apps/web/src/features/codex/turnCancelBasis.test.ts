import { expect, test } from 'vitest'
import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { actor, workspace } from './bootstrapTestFixtures'
import { decodeTurnCommand, turnCancelCommand } from './turnCommands'
import { turnCancelledJob, turnControl } from './turnTestFixtures'

const pending = turnControl()
const running = { ...pending, job: { ...pending.job, status: 'running' as const }, job_revision: 4,
 execution: 'active' as const, started_at: pending.created_at }
const requested = { ...running, cancel_requested: true }
const terminal = { ...running, job: { ...running.job, status: 'completed' as const }, job_revision: 5,
 execution: 'terminal' as const, outcome: 'completed' as const, finished_at: pending.created_at }

test.each([
 [pending, 'awaiting_approval', 1], [pending, 'cancelled', 1], [pending, 'failed', 2],
 [running, 'cancelled', 5], [requested, 'running', 5], [terminal, 'failed', 4],
] as const)('full JobSnapshot cannot contradict the original cancellation basis %#', (basis, status, revision) => {
 const original = turnCancelCommand(workspace, actor, basis)
 const ack: JobSnapshot = { ...turnCancelledJob(), status, revision }
 expect(() => decodeTurnCommand(JSON.stringify({ ...original, ack }), workspace)).toThrow()
})

test.each([
 [pending, 'cancelled', 2], [running, 'running', 5], [requested, 'running', 4], [terminal, 'completed', 5],
] as const)('owner cancellation transition and no-op observation preserve the exact full ACK %#', (basis, status, revision) => {
 const original = turnCancelCommand(workspace, actor, basis)
 const ack: JobSnapshot = { ...turnCancelledJob(), status, revision, progress: { completed: 0, total: null, label: status } }
 expect(decodeTurnCommand(JSON.stringify({ ...original, ack }), workspace)).toEqual({ ...original, ack })
})
