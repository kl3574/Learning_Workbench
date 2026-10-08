import { useEffect, useRef } from 'react'
import type { GenericApprovalView } from '../../../../../packages/contracts/generated/codex-turn-types'
import type { DraftStore } from '../../workbench/DraftStore'
import type { ApprovalPort } from './approvalClient'
import { useCodexApprovals } from './useCodexApprovals'
export type ApprovalPanelState = { dirty: boolean; safe: boolean; isolated: boolean }
function Operation({ value }: { value: GenericApprovalView }) {
 const op = value.operation
 return <section aria-label="完整当前操作"><p>审批 {value.id} · 原 actor {value.actor_session_id} · r{value.revision}</p>
  <p>session {value.session_id} · turn {value.turn_id} · run {value.run_id} · Job {value.job.id} / {value.job.status} / r{value.job_revision}</p>
  <p>操作 SHA <code>{value.operation_sha256}</code>；此 SHA 包含私有 owner 绑定，不能从显示摘要重算。</p>
  <p>创建 {value.created_at}；期限 {value.expires_at}</p>
  <p>当前决定 {value.decision}；有效性 {value.validity}；执行 {value.execution}</p>
  {op.kind === 'unsupported' ? <p>不支持的操作：{op.category} · {op.reason}。仅可通过安全控制明确拒绝。</p> : <>
   <p>固定操作 profile SHA <code>{op.operation_profile_sha256}</code>。批准仅限这一个受检操作，不授予后续操作、会话缓存权限或新的模型请求。</p>
   {op.kind === 'command' ? <>
    <h5>完整实际命令</h5><pre aria-label="完整实际命令">{op.command_text}</pre>
    <p>相对工作目录 {op.cwd}；唯一写入范围 {op.writable_area}；网络 {op.network}</p>
    <p>可执行身份 SHA <code>{op.executable_sha256}</code>；环境 SHA <code>{op.environment_sha256}</code>；文件范围 SHA <code>{op.filesystem_scope_sha256}</code></p>
    <h5>全部可读文件</h5>{!op.read_files.length && <p>本操作无可读文件。</p>}
    {op.read_files.map(f => <p key={f.path}>{f.path} · {f.size} bytes · <code>{f.sha256}</code></p>)}
   </> : <><h5>完整有序文件变更</h5>{op.files.map((f, i) => <article key={f.path}><p>{i + 1}. {f.action} · {f.path}</p><p>before：{f.before_size ?? 'null'} bytes · {f.before_sha256 ?? 'null'}</p><p>after：{f.after_size ?? 'null'} bytes · {f.after_sha256 ?? 'null'}</p><pre aria-label={`完整 diff ${f.path}`}>{f.diff}</pre></article>)}<p>只允许本 turn 私有输出区；不授予网络或宿主目录写入权限。</p></>}
  </>}
  <p>决定时间 {value.decided_at ?? '无'}；实际开始 {value.started_at ?? '无'}；实际结束 {value.finished_at ?? '无'}</p>
  <p>结果 SHA {value.result_sha256 ?? '无'}；安全错误 {value.error_code ?? '无'}</p>
  <details><summary>核对完整当前审批 GET</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>
 </section>
}
export function CodexApprovalsPanel({ workspace, writeAdmitted, port, store, formStore, onState }: { workspace: string; writeAdmitted: boolean; port?: ApprovalPort; store?: DraftStore; formStore?: DraftStore; onState?: (value: ApprovalPanelState) => void }) {
 const state = useCodexApprovals(workspace, writeAdmitted, port, store, formStore), callback = useRef(onState); callback.current = onState
 useEffect(() => { callback.current?.({ dirty: state.dirty, safe: state.safe, isolated: state.isolated }) }, [state.dirty, state.safe, state.isolated])
 const blocked = state.busy || !state.ready, detail = state.detail
 const approvable = !!detail && detail.actor_session_id === state.actor && detail.decision === 'pending' && detail.validity === 'current' && detail.execution === 'not_started' && detail.operation.kind !== 'unsupported' && !state.hasCommand(detail.id)
 return <section aria-label="Codex 逐操作审批" style={{ overflowWrap: 'anywhere' }}><h3>Codex 逐操作审批</h3>
  <p>逐项工具许可独立于 Provider 外发批准、数值检查和人工审校。读取与恢复不会自动决定或执行；默认未注册的操作不能批准。</p>
  <button disabled={!workspace || state.busy} onClick={() => void state.refresh()}>读取审批记录与权限</button>
  {!state.ready && <p>先读取当前权限和本机记录；没有自动 POST。</p>}
  {state.ready && !state.allowed && <p>当前仅开放安全控制与明确拒绝；操作正文和原批准详情已收起。有效 learner/author 在测试策略限制下仍可减权。</p>}
  {state.error && <p role="status">{state.error}</p>}{state.message && <p role="status">{state.message}</p>}
  {state.busy && <p role="status">正在处理这次明确操作。</p>}
  {state.retained > 0 && <p>有尚未落盘的原 actor 审批事实或表单；保留在隔离内存，离开前请仅保存本机事实。</p>}
  {state.canSave && <button disabled={state.busy} onClick={() => void state.saveMemory()}>仅保存审批本机事实</button>}
  <label>审批来源 turn ID<input disabled={blocked} value={state.fields.turn_id} onChange={e => state.edit({ turn_id: e.target.value })} /></label>
  <button disabled={blocked || !state.fields.turn_id} onClick={() => void state.readControl()}>独立读取审批安全控制</button>
  <p>来源 ID 的未发送输入独立保存；恢复需明确选择原 actor 的快照。</p>
  {state.forms.map(f => <button key={f.snapshot_id} disabled={state.busy} onClick={() => void state.restore(f)}>恢复审批表单 {f.draft_id} · {f.sequence}</button>)}
  {state.control && <section aria-label="审批安全控制 GET"><h4>本次安全控制 GET</h4><p>session {state.control.session_id} · turn {state.control.id} · Job {state.control.job.id} · {state.control.execution}</p>
   {!state.control.approval_controls.length && <p>本次控制没有审批记录；没有构造或猜测操作。</p>}
   {state.control.approval_controls.map(a => <article key={a.id}><p>{a.id} · 审批 r{a.revision} · {a.decision} · {a.validity}</p><p>操作 SHA <code>{a.operation_sha256}</code></p>
    <button disabled={blocked || !state.allowed} onClick={() => void state.read(a.id)}>独立读取完整操作 {a.id}</button>
    <button disabled={blocked || a.decision !== 'pending' || state.hasCommand(a.id, 'decline')} onClick={() => void state.decide(a.id, 'decline')}>明确拒绝这一次操作 {a.id}</button>
    <p>拒绝以本次完整安全控制的审批 revision/hash 为基准；无需读取操作正文，也不证明远端已经停止。</p>
   </article>)}
  </section>}
  {detail && <section aria-label="审批当前详情 GET"><Operation value={detail} />
   {detail.validity !== 'current' && <p>BLOCKED：当前操作为 {detail.validity}；原历史仍保留，不能据此新增批准。</p>}
   {detail.actor_session_id !== state.actor && <p>这是其他原 actor 的操作；当前作者可读取，但不能接管批准。</p>}
   <button disabled={blocked || !state.allowed || !approvable} onClick={() => void state.decide(detail.id, 'approve_once')}>明确仅批准这一次完整操作 {detail.id}</button>
   <button disabled={blocked || !state.allowed} onClick={() => void state.read(detail.id, detail)}>独立刷新操作执行事实 {detail.id}</button>
   <p>approve_once ACK 只记录决定；实际开始、结束与结果只能以上方独立 GET 为准。已开始后未知不能通过再次批准来补跑。</p>
  </section>}
  <section aria-label="审批原命令与完整 ACK"><h4>原决定命令与完整历史 ACK</h4>
   {state.commands.map(c => <article key={c.command_id}><p>{c.body.decision} · {c.ack ? '原 ACK 已记录，不是当前执行状态' : c.error ? `安全错误 ${c.error.status} ${c.error.code ?? ''}；原基准保留` : '结果未知；原 key 与完整命令保留'}</p>
    {c.actor_session_id !== state.actor && <p>其他 actor 的减权事实只读；不能接管或重放。</p>}
    <details><summary>核对原审批命令 {c.command_id}</summary><p>原 actor {c.actor_session_id}</p><pre>{JSON.stringify({ route: c.route, target_id: c.target_id, body: c.body, basis: c.basis, ack: c.ack }, null, 2)}</pre></details>
    <button disabled={state.busy || !state.canReplay(c)} onClick={() => void state.execute(c)}>显式回放审批原 key {c.command_id}</button>
    <button disabled={blocked || !state.allowed} onClick={() => void state.read(c.target_id, c.basis.kind === 'approve' ? c.basis.view : c.basis.control)}>独立读取原审批当前事实 {c.target_id}</button>
   </article>)}
  </section>
 </section>
}
