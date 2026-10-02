import type { DraftCandidate, DraftReviewWrite, ReviewDecisionWrite, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { validIdentity } from '../providers/providerSchema'

export type CreateFormValue = { checks: DraftReviewWrite['checks']; note: string; confirmed: boolean }
export type DecisionFormValue = { mathematical: ReviewDecisionWrite['mathematical'] | ''; sources: ReviewDecisionWrite['sources'] | ''; reason: string; evidence: string; confirmed: boolean }
export const emptyCreateForm = (): CreateFormValue => ({ checks: ['structure', 'numerical_examples', 'mathematics', 'sources'], note: '', confirmed: false })
export const emptyDecisionForm = (): DecisionFormValue => ({ mathematical: '', sources: '', reason: '', evidence: '', confirmed: false })
export const createFormDirty = (value: CreateFormValue) => !!value.note || value.confirmed || value.checks.length !== 4
export const decisionFormDirty = (value: DecisionFormValue) => !!(value.mathematical || value.sources || value.reason || value.evidence || value.confirmed)

export function ReviewCreateForm({ candidate, candidateState, busy, submit, value, change }: {
  candidate: DraftCandidate; candidateState: string; busy: boolean; submit: (body: DraftReviewWrite) => void
  value: CreateFormValue; change: (value: CreateFormValue) => void
}) {
  const { checks, note, confirmed } = value
  return <section aria-label="准备准确候选审核"><h4>准备这份准确候选的审核</h4>
    <p>{candidate.entity} · {candidate.draft_id} · 候选 r{candidate.draft_revision}</p><code>{candidate.candidate_sha256}</code>
    <p>候选入口最近读到的状态：{candidateState}。审核任务与审核回执是独立事实，不自动推进草稿状态或发布；符合当前范围的 Import 文本块须在独立发布面板明确确认。</p>
    <fieldset disabled={busy}><legend>本次请求的检查</legend>{([
      ['structure', '结构与声明关系'], ['numerical_examples', '已存在的数值执行记录'], ['mathematics', '数学审核状态'], ['sources', '来源审核状态'],
    ] as const).map(([key, label]) => <label key={key}><input type="checkbox" checked={checks.includes(key)} onChange={event => change({ ...value, checks: event.target.checked ? [...checks, key] : checks.filter(item => item !== key) })} />{label}</label>)}</fieldset>
    <p>任务读取现有数值历史，不启动新的数值执行。数学、来源和独立教学审核不会由机器检查自动批准。</p>
    <label>本次审核备注<textarea aria-label="本次审核备注" value={note} disabled={busy} onChange={event => change({ ...value, note: event.target.value })} /></label>
    <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => change({ ...value, confirmed: event.target.checked })} />我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。</label>
    <button disabled={busy || !confirmed || !checks.length} onClick={() => submit({ expected_revision: candidate.draft_revision, checks, reviewer_note: note })}>明确创建本次审核任务</button>
  </section>
}

export function ReviewDecisionForm({ receipt, busy, submit, value, change }: {
  receipt: StoredReviewReceipt; busy: boolean; submit: (body: ReviewDecisionWrite) => void
  value: DecisionFormValue; change: (value: DecisionFormValue) => void
}) {
  const { mathematical, sources, reason, evidence, confirmed } = value
  const ids = evidence.trim() ? evidence.trim().split(/[\s,]+/) : []
  const valid = ids.every(validIdentity) && new Set(ids).size === ids.length
  return <section aria-label="明确人工审核决定"><h4>记录这一次明确人工决定</h4>
    <p>审核 {receipt.id} · 当前回执 r{receipt.revision}；决定只绑定下列候选哈希：</p><code>{receipt.candidate.candidate_sha256}</code>
    <p>操作者由当前作者会话确定；这里不填写 reviewer。此决定不发布内容，不授予独立教学通过。</p>
    <label>数学审核决定<select aria-label="数学审核决定" value={mathematical} disabled={busy} onChange={event => change({ ...value, mathematical: event.target.value as typeof mathematical })}><option value="">请明确选择</option><option value="APPROVED">明确批准</option><option value="REJECTED">明确拒绝</option><option value="NOT_APPLICABLE">不适用（须说明理由）</option></select></label>
    <label>来源审核决定<select aria-label="来源审核决定" value={sources} disabled={busy} onChange={event => change({ ...value, sources: event.target.value as typeof sources })}><option value="">请明确选择</option><option value="APPROVED">明确批准</option><option value="REJECTED">明确拒绝</option><option value="NOT_APPLICABLE">不适用（须说明理由）</option></select></label>
    <p>含数学结构或数值计划的候选不能用“不适用”跳过数学审核；服务端会另行核验。</p>
    <label>审核理由<textarea aria-label="审核理由" value={reason} disabled={busy} onChange={event => change({ ...value, reason: event.target.value })} /></label>
    <label>已有证据附件 ID（可空，空格或逗号分隔）<textarea aria-label="已有证据附件 ID（可空，空格或逗号分隔）" value={evidence} disabled={busy} onChange={event => change({ ...value, evidence: event.target.value })} /></label>
    <p>只接受本工作区当前可访问的实际附件，服务端会核验归属与字节；输入 ID 不是上传或授权。</p>
    {!valid && <p role="alert">附件 ID 无效或重复。</p>}
    <label><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => change({ ...value, confirmed: event.target.checked })} />我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。</label>
    <button disabled={busy || !mathematical || !sources || !reason.trim() || !valid || !confirmed}
      onClick={() => { if (mathematical && sources) submit({ expected_revision: receipt.revision!, candidate_sha256: receipt.candidate.candidate_sha256, mathematical, sources, reason, evidence_artifact_ids: ids }) }}>明确保存这次人工审核决定</button>
  </section>
}
