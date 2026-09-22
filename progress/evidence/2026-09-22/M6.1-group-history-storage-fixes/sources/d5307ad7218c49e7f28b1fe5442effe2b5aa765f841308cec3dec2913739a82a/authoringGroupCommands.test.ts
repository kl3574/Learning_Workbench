import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import type { ApprovalDecision, AuthoringGroupNumericPreviewWrite, AuthoringGroupPrepareWrite } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore } from '../../workbench/DraftStore'
import { checkedAuthoring, decodeAuthoringCommand, makeAuthoringCommand, persistAuthoringCommand, readAuthoringCommand, type AuthoringCommand } from './authoringCommands'

// Original DTOs from the real SQLite group numeric integration test (synthetic content only).
const original = {
  "prepare-numeric-group": {
    "body": {
      "objectives": [
        "检验显式求和"
      ],
      "output_kind": "lesson",
      "prerequisites": [],
      "proof_policy": "full",
      "provider_id": "test_provider",
      "source_refs": [],
      "target_concept_refs": [],
      "topic": "原创合成教学小节"
    },
    "ack": {
      "id": "authoring_e7f48d750d0a4a29b77dd260f022b44d",
      "status": "awaiting_approval"
    }
  },
  "numeric-preview": {
    "body": {
      "candidate": {
        "candidate_sha256": "9aaaf389863ec88cfeb75a88925da5f5763292f116de3561d83d9934f2e40157",
        "draft_id": "authoring_group_5b46e5ecda3e4610a48bed8e85e607f4",
        "draft_revision": 1,
        "entity": "lesson"
      },
      "target": {
        "entity": "block",
        "member_key": "lesson_example",
        "member_sha256": "b31bdb885338279c5b0492f1fece27a94c32d4cbafeb581aedf2fb79a9f70fba"
      }
    },
    "ack": {
      "candidate": {
        "candidate_sha256": "9aaaf389863ec88cfeb75a88925da5f5763292f116de3561d83d9934f2e40157",
        "draft_id": "authoring_group_5b46e5ecda3e4610a48bed8e85e607f4",
        "draft_revision": 1,
        "entity": "lesson"
      },
      "created_at": "2026-09-22T02:23:36.125244Z",
      "decision": "pending",
      "expired": false,
      "expires_at": "2026-09-22T02:33:36.125244Z",
      "id": "group_numeric_c4a333053a8f4108809d9595351770e0",
      "job": null,
      "job_revision": null,
      "operation_sha256": "34e06984f06ce04c5199dd66e874c9ff1ed37c9cf7e6fe84461aad11f26558e0",
      "plan": {
        "assertions": [
          {
            "atol": 0.0,
            "expected": 42.0,
            "expression": "x+25",
            "id": "sum_check",
            "rtol": 0.0,
            "unit": "number"
          }
        ],
        "seed": null,
        "variables": [
          {
            "name": "x",
            "unit": "number",
            "value": 17.0
          }
        ],
        "version": "finite-arithmetic-v1"
      },
      "result": null,
      "revision": 1,
      "runtime": {
        "cpu_seconds": 2,
        "evaluator_process_limit": 1,
        "evaluator_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "evaluator_version": "finite-arithmetic-v1",
        "memory_bytes": 268435456,
        "output_bytes": 65536,
        "python_version": "synthetic-ledger-only",
        "runtime_manifest_sha256": "79b2ffc2a852bab302640621f459743129e33b32bf413c8321f538f72c8e8c8e",
        "sandbox_version": "not-executed",
        "wall_seconds": 5
      },
      "target": {
        "entity": "block",
        "member_key": "lesson_example",
        "member_sha256": "b31bdb885338279c5b0492f1fece27a94c32d4cbafeb581aedf2fb79a9f70fba"
      },
      "warnings": []
    }
  },
  "approve": {
    "body": {
      "decision": "approve_once",
      "expected_revision": 1,
      "operation_sha256": "34e06984f06ce04c5199dd66e874c9ff1ed37c9cf7e6fe84461aad11f26558e0"
    },
    "ack": {
      "applied": true,
      "decision": "approve_once",
      "id": "group_numeric_c4a333053a8f4108809d9595351770e0",
      "job": {
        "id": "group_numeric_job_1a67123ba3e64586ad859c21abd2ef0e",
        "status": "queued"
      },
      "operation_sha256": "34e06984f06ce04c5199dd66e874c9ff1ed37c9cf7e6fe84461aad11f26558e0",
      "revision": 2
    }
  }
}

const stores: DraftStore[] = []
afterEach(() => { for (const value of stores.splice(0)) value.close() })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  const store = new DraftStore({ name: `authoring_group_commands_${crypto.randomUUID()}` }); stores.push(store)
  const prepare = makeAuthoringCommand(workspace, { kind: 'group_prepare', body: checkedAuthoring<AuthoringGroupPrepareWrite>('AuthoringGroupPrepareWrite', structuredClone(original['prepare-numeric-group'].body)) })
  const body = checkedAuthoring<AuthoringGroupNumericPreviewWrite>('AuthoringGroupNumericPreviewWrite', structuredClone(original['numeric-preview'].body))
  const preview = makeAuthoringCommand(workspace, { kind: 'group_numeric_preview', draft_id: body.candidate.draft_id, member_key: body.target.member_key, body })
  const decision = makeAuthoringCommand(workspace, { kind: 'group_numeric_decision', check_id: original.approve.ack.id, body: checkedAuthoring<ApprovalDecision>('ApprovalDecision', structuredClone(original.approve.body)) })
  return { workspace, store, prepare, preview, decision }
}
function acknowledged(command: AuthoringCommand, ack: unknown): AuthoringCommand {
  return decodeAuthoringCommand(JSON.stringify({ ...command, ack }), command.workspace_id)
}
test.each(['prepare', 'preview', 'decision'] as const)('group %s keeps its original key, body and ACK across real IDB reload and pending replay', async kind => {
  const f = fixture(), pending = f[kind]
  const expected = kind === 'prepare' ? original['prepare-numeric-group'].ack : kind === 'preview' ? original['numeric-preview'].ack : original.approve.ack
  await persistAuthoringCommand(pending, f.store)
  const loaded = readAuthoringCommand((await f.store.load(f.workspace))[pending.command_id], f.workspace)
  expect(loaded).toEqual(pending)
  const accepted = acknowledged(loaded, expected)
  await persistAuthoringCommand(accepted, f.store)
  expect(await persistAuthoringCommand(pending, f.store)).toEqual(accepted)
  expect(readAuthoringCommand((await f.store.load(f.workspace))[pending.command_id], f.workspace)).toEqual(accepted)
})
test.each(['draft_url', 'member_url', 'root_hash', 'member_hash', 'private_extra'] as const)('group preview rejects %s mismatch before persistence', mutation => {
  const f = fixture(), pending = f.preview
  if (pending.kind !== 'group_numeric_preview') throw new Error('Wrong fixture')
  const value = structuredClone(pending)
  value.ack = checkedAuthoring('AuthoringGroupNumericCheckView', structuredClone(original['numeric-preview'].ack))
  if (mutation === 'draft_url') value.draft_id = 'draft_other'
  if (mutation === 'member_url') value.member_key = 'other_member'
  if (mutation === 'root_hash') value.ack!.candidate.candidate_sha256 = '0'.repeat(64)
  if (mutation === 'member_hash') value.ack!.target.member_sha256 = '0'.repeat(64)
  const raw = mutation === 'private_extra' ? { ...value, body: { ...value.body, private_solution: 'not a request field' } } : value
  expect(() => decodeAuthoringCommand(JSON.stringify(raw), f.workspace)).toThrow()
  expect(() => decodeAuthoringCommand(JSON.stringify(pending), 'workspace_other')).toThrow()
})
test.each(['check_id', 'operation_hash', 'decision', 'revision'] as const)('group decision rejects a foreign %s ACK', mutation => {
  const f = fixture(), ack = structuredClone(original.approve.ack)
  if (mutation === 'check_id') ack.id = 'numeric_other'
  if (mutation === 'operation_hash') ack.operation_sha256 = '0'.repeat(64)
  if (mutation === 'decision') ack.decision = 'declined'
  if (mutation === 'revision') ack.revision += 1
  expect(() => acknowledged(f.decision, ack)).toThrow()
})
test('conflicting real IDB writers preserve both group command bodies and block automatic replay', async () => {
  const f = fixture(), first = f.prepare
  await persistAuthoringCommand(first, f.store)
  const other = structuredClone(first)
  if (other.kind !== 'group_prepare') throw new Error('Wrong fixture')
  other.body.topic += ' different request'
  const conflict = await f.store.save(f.workspace, other.command_id, JSON.stringify(other), 0)
  expect(conflict.kind).toBe('conflict')
  expect(conflict.record.conflicts).toHaveLength(1)
  expect(() => readAuthoringCommand(conflict.record, f.workspace)).toThrow()
  await expect(persistAuthoringCommand(first, f.store)).rejects.toThrow()
  const after = (await f.store.load(f.workspace))[first.command_id]
  expect(after.text).toBe(conflict.record.text)
  expect(after.conflicts).toEqual(conflict.record.conflicts)
})
test('a later valid-shaped receipt cannot replace the original group prepare job ACK', async () => {
  const f = fixture(), accepted = acknowledged(f.prepare, original['prepare-numeric-group'].ack)
  await persistAuthoringCommand(accepted, f.store)
  const foreign = acknowledged(f.prepare, { ...original['prepare-numeric-group'].ack, id: 'job_other' })
  await expect(persistAuthoringCommand(foreign, f.store)).rejects.toThrow()
  expect(readAuthoringCommand((await f.store.load(f.workspace))[f.prepare.command_id], f.workspace)).toEqual(accepted)
})
