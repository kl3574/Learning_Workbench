import type { DraftCandidate, DraftReviewWrite, JobCancelRequest, JobSnapshot, ReviewDecisionWrite, ReviewJobAck, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { checkedReview, reviewJob, reviewReceipt } from './reviewSchema'

type Origin = { page_id: string; access_generation: number }
type Identity = { version: 1; workspace_id: string; command_id: string; origin: Origin; rejection: { status: number; code: string | null } | null }
export type ReviewCommand = Identity & (
  { kind: 'create'; candidate: DraftCandidate; body: DraftReviewWrite; ack: ReviewJobAck | null }
  | { kind: 'decision'; review_id: string; candidate: DraftCandidate; body: ReviewDecisionWrite; ack: StoredReviewReceipt | null }
  | { kind: 'cancel'; review_id: string; body: JobCancelRequest; ack: JobSnapshot | null }
)
type Input<T> = T extends ReviewCommand ? Omit<T, keyof Identity | 'ack'> : never
export type ReviewCommandInput = Input<ReviewCommand>
// A random page marker is not an actor identity or an authentication proof.
// A fresh JS page cannot replay an old actor-bound write using this marker.
export const reviewPageId = `page_${crypto.randomUUID()}`
export const reviewCommandStore = new DraftStore({ name: 'learning-workbench.review-commands.v1' })
export const reviewControlStore = new DraftStore({ name: 'learning-workbench.review-controls.v1' })
export const reviewJobStore = new DraftStore({ name: 'learning-workbench.review-job-ids.v1' })

export function decodeReviewCommand(raw: string, workspace: string): ReviewCommand {
  const value = JSON.parse(raw) as ReviewCommand
  const keys = ['version', 'workspace_id', 'command_id', 'origin', 'rejection', 'kind', 'body', 'ack',
    ...(value?.kind === 'create' ? ['candidate'] : value?.kind === 'decision' ? ['candidate', 'review_id'] : ['review_id'])]
  if (!exactObject(value, keys) || value.version !== 1 || value.workspace_id !== workspace || !validIdentity(value.command_id)
      || !exactObject(value.origin, ['page_id', 'access_generation']) || !validIdentity(value.origin.page_id)
      || !Number.isSafeInteger(value.origin.access_generation) || value.origin.access_generation < 0) throw new Error('审核原命令身份无效。')
  if (value.rejection !== null && (!exactObject(value.rejection, ['status', 'code'])
      || ![400, 409, 412, 422].includes(value.rejection.status)
      || value.rejection.code !== null && (typeof value.rejection.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(value.rejection.code)))
      || value.rejection && value.ack) throw new Error('审核命令拒绝记录无效。')
  if (value.kind === 'create') {
    checkedReview('DraftCandidate', value.candidate); checkedReview('DraftReviewWrite', value.body)
    if (value.body.expected_revision !== value.candidate.draft_revision || new Set(value.body.checks).size !== value.body.checks.length) throw new Error('审核命令的候选基准不一致。')
    if (value.ack !== null && checkedReview<ReviewJobAck>('ReviewJobAck', value.ack).status !== 'queued') throw new Error('审核创建原回执状态无效。')
  } else if (value.kind === 'decision') {
    checkedReview('DraftCandidate', value.candidate); checkedReview('ReviewDecisionWrite', value.body)
    if (!validIdentity(value.review_id) || value.body.candidate_sha256 !== value.candidate.candidate_sha256
        || !value.body.reason.trim() || new Set(value.body.evidence_artifact_ids).size !== value.body.evidence_artifact_ids.length) throw new Error('审核决定未绑定准确候选和明确理由。')
    if (value.ack !== null) {
      const ack = reviewReceipt(value.ack, value.review_id, value.candidate)
      if (ack.revision !== value.body.expected_revision + 1 || ack.mathematical !== value.body.mathematical
          || ack.sources !== value.body.sources || ack.decision_reason !== value.body.reason) throw new Error('审核决定回执不匹配原命令。')
    }
  } else if (value.kind === 'cancel') {
    checkedReview('JobCancelRequest', value.body)
    if (!validIdentity(value.review_id)) throw new Error('审核任务身份无效。')
    if (value.ack !== null) reviewJob(value.ack, workspace, value.review_id)
  } else throw new Error('未知审核命令。')
  return value
}
export function makeReviewCommand(workspace: string, access: number, input: ReviewCommandInput): ReviewCommand {
  return decodeReviewCommand(JSON.stringify({ ...input, version: 1, workspace_id: workspace,
    command_id: `reviewcmd_${crypto.randomUUID()}`, origin: { page_id: reviewPageId, access_generation: access }, rejection: null, ack: null }), workspace)
}
export function sameReviewActorPage(command: ReviewCommand, access: number): boolean {
  return command.origin.page_id === reviewPageId && command.origin.access_generation === access
}
const immutable = (command: ReviewCommand) => ({ ...command, ack: null, rejection: null })
export function readReviewCommand(record: DraftRecord, workspace: string): ReviewCommand {
  const values = [record.text, ...record.conflicts.map(value => value.text)].map(raw => decodeReviewCommand(raw, workspace)), first = values[0]
  if (record.objectId !== first.command_id || values.some(value => !sameValue(immutable(value), immutable(first)))) throw new Error('原审核命令存在不同内容，保留全部本机候选。')
  const acks = values.filter(value => value.ack)
  if (acks.some(value => !sameValue(value.ack, acks[0].ack))) throw new Error('原审核命令存在不同回执。')
  return acks[0] ?? values.find(value => value.rejection) ?? first
}
export async function persistReviewCommand(value: ReviewCommand, store = value.kind === 'cancel' ? reviewControlStore : reviewCommandStore, guard?: DraftWriteGuard): Promise<ReviewCommand> {
  assertDraftWriteAllowed(guard)
  let desired = decodeReviewCommand(JSON.stringify(value), value.workspace_id)
  for (let attempt = 0; attempt < 4; attempt++) {
    assertDraftWriteAllowed(guard)
    const old = (await store.load(value.workspace_id))[value.command_id]
    assertDraftWriteAllowed(guard)
    if (old) {
      const current = readReviewCommand(old, value.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('不能替换审核原命令或原回执。')
      if (current.ack || !desired.ack && current.rejection) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const saved = await store.save(value.workspace_id, value.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(item => item.id) ?? [], guard)
    const actual = readReviewCommand(saved.record, value.workspace_id)
    if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
  }
  throw new Error('其他页面仍在保存审核命令，请保留原命令后重试。')
}

export async function knownReviewJobs(workspace: string): Promise<string[]> {
  return Object.values(await reviewJobStore.load(workspace)).map(record => {
    const values = [record.text, ...record.conflicts.map(value => value.text)].map(raw => JSON.parse(raw) as Record<string, unknown>)
    if (values.some(value => !exactObject(value, ['version', 'workspace_id', 'review_id']) || value.version !== 1
        || value.workspace_id !== workspace || !validIdentity(value.review_id) || record.objectId !== value.review_id
        || !sameValue(value, values[0]))) throw new Error('本机审核恢复标识不一致，未覆盖原记录。')
    return values[0].review_id as string
  }).sort()
}
export async function rememberReviewJob(workspace: string, id: string): Promise<void> {
  if (!validIdentity(id)) throw new Error('审核恢复标识无效。')
  const old = (await reviewJobStore.load(workspace))[id]
  const text = JSON.stringify({ version: 1, workspace_id: workspace, review_id: id })
  if (old && old.text === text && !old.conflicts.length) return
  if (old && (old.text !== text || old.conflicts.some(value => value.text !== text))) throw new Error('审核恢复标识冲突。')
  await reviewJobStore.save(workspace, id, text, old?.revision ?? 0, old?.conflicts.map(value => value.id) ?? [])
}
