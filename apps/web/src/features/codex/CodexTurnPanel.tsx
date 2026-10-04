import { useEffect, useRef, useState } from 'react'
import type { ContentRef } from '../../../../../packages/contracts/generated/api-types'
import type { TurnPort } from './turnClient'
import type { DraftStore } from '../../workbench/DraftStore'
import { useCodexTurns } from './useCodexTurns'
import { CodexTurnOutboundPanel } from './CodexTurnOutboundPanel'
import type { TurnOutboundPort } from './turnOutboundClient'
import { CodexTurnEventsPanel } from './CodexTurnEventsPanel'
import type { CodexEventPort } from './turnEventClient'
export type TurnPanelState = { dirty: boolean; safe: boolean; isolated: boolean }
export function CodexTurnPanel({ workspace, writeAdmitted, port, store, formStore, outboundPort, outboundStore, outboundFormStore, eventPort, currentBlock = null, selectedSession = null, onState }: {
 workspace: string; writeAdmitted: boolean; port?: TurnPort; store?: DraftStore; formStore?: DraftStore; currentBlock?: ContentRef | null;
 selectedSession?: string | null; onState?: (value: TurnPanelState) => void
 outboundPort?: TurnOutboundPort; outboundStore?: DraftStore; outboundFormStore?: DraftStore
 eventPort?: CodexEventPort
}) {
 const state = useCodexTurns(workspace, writeAdmitted, port, store, formStore), callback = useRef(onState); callback.current = onState
 const [outbound, setOutbound] = useState<TurnPanelState>({ dirty: false, safe: true, isolated: false })
 useEffect(() => { callback.current?.({ dirty: state.dirty || outbound.dirty, safe: state.safe && outbound.safe, isolated: state.isolated || outbound.isolated }) }, [state.dirty, state.safe, state.isolated, outbound])
 const blocked = state.busy || !state.ready, current = state.current
 return <section aria-label="Codex 回合准备与安全控制"><h3>Codex 回合准备与安全控制</h3>
  <p>明确准备只冻结原输入并预约一个 Job。外发预览、批准、开始和结果读取须在下方逐次明确操作；准备本身不调用模型或工具。</p>
  <button disabled={!workspace || state.busy} onClick={() => void state.refresh()}>读取回合记录与权限</button>
  {!state.ready && <p>先读取当前权限和本机记录；不会自动恢复发送。</p>}
  {state.ready && !state.allowed && <p>当前仅开放安全控制。原文、材料和准备详情已收起；本机原记录保留，须原作者且当前策略允许后显式恢复。</p>}
  {state.error && <p role="status">{state.error}</p>}{state.message && <p role="status">{state.message}</p>}
  {state.busy && <p role="status">正在处理本次明确操作。</p>}
  {state.retained > 0 && <p>有尚未落盘的隔离回合事实或表单；关闭和刷新前请保存，原 actor 归属不变。</p>}
  {state.canSave && <button disabled={state.busy} onClick={() => void state.saveMemory()}>仅保存原回合本机事实</button>}
  <label>已建立的 session ID<input disabled={blocked} value={state.selected} onChange={e => state.select(e.target.value)} /></label>
  {selectedSession && <button disabled={blocked} onClick={() => state.select(selectedSession)}>选择已核验会话 {selectedSession}</button>}
  <button disabled={blocked || !state.selected} onClick={() => void state.readCurrent()}>独立读取当前 session</button>
  <button disabled={blocked || !state.selected} onClick={() => void state.readPage()}>读取安全回合分页</button>
  {current && <section aria-label="独立 GET 当前 session"><p>{current.id} · {current.status} · r{current.revision} · 活动回合 {current.active_turn_id ?? '无'}</p>
   <p>ready 仅表示原本地映射已核验。当前 GET 不执行；准备只使用这次 GET 的版本。</p>
   {current.active_turn_id && <button disabled={blocked} onClick={() => void state.readControl(current.active_turn_id!)}>读取回合控制 {current.active_turn_id}</button>}
  </section>}
  {state.allowed && <section aria-label="回合原输入表单">
   <label>回合原文<textarea disabled={state.busy} value={state.fields.message} onChange={e => state.edit({ message: e.target.value })} /></label>
   <p>原 Unicode、空格与换行保持原样；1..8000 个字符，不能只有空白。</p>
   <label>Provider ID<input disabled={state.busy} value={state.fields.provider_id} onChange={e => state.edit({ provider_id: e.target.value })} /></label>
   <label>工具调用上限<input inputMode="numeric" disabled={state.busy} value={state.fields.max_tool_calls} onChange={e => state.edit({ max_tool_calls: e.target.value })} /></label>
   <label>回合 wall 秒数<input inputMode="numeric" disabled={state.busy} value={state.fields.wall_seconds} onChange={e => state.edit({ wall_seconds: e.target.value })} /></label>
   <p>工具默认 0，最多 16；wall 1..300 秒。预算不批准任何具体操作。</p>
   <button disabled={state.busy} onClick={() => state.edit({ context_refs: [] })}>明确不附加材料 []</button>
   <button disabled={state.busy || currentBlock?.entity !== 'block'} onClick={() => { if (currentBlock?.entity === 'block') state.edit({ context_refs: [{ ...currentBlock, entity: 'block' }] }) }}>选择当前完整公开块</button>
   <pre aria-label="本次精确材料引用">{JSON.stringify(state.fields.context_refs, null, 2)}</pre>
   <p>只发送明确选定的完整公开块修订。切换阅读位置不会替换已选引用；是否仍可读取由服务端重新核验。</p>
   <button disabled={state.busy || !state.canPrepare} onClick={() => void state.prepare()}>明确准备回合并预约 Job</button>
   <p>每次编辑保存独立本机快照，关闭后保留，恢复需再次明确选择。旧未知命令不随表单修改；重放须使用下面的原 key。</p>
   {state.forms.map(value => <button key={value.snapshot_id} disabled={state.busy} onClick={() => void state.restoreForm(value)}>恢复原表单 {value.draft_id} · {value.sequence}</button>)}
  </section>}
  <section aria-label="回合原命令与历史 ACK"><h4>原命令与历史 ACK</h4>
   <p>准备正文只向原作者且当前策略允许时显示。已保存表单和未知命令在权限变化后仍保留；历史 ACK 不更新当前 GET。</p>
   {state.commands.map(command => <article key={command.command_id}>
    <p>{command.kind === 'prepare' ? '准备回合' : '取消回合 Job'} · {command.ack ? '原 ACK 已记录，不是当前状态' : command.error ? `安全错误 ${command.error.status} ${command.error.code ?? ''}；原基准保留` : '结果未知；原 key 与完整命令保留'}</p>
    {command.actor_session_id !== state.actor && <p>其他 actor 的安全控制记录只读；不能接管或重放。</p>}
    <details><summary>核对回合原命令 {command.command_id}</summary><p>原 actor {command.actor_session_id}</p><pre>{JSON.stringify({ session_id: command.session_id, body: command.body, basis: command.basis, ack: command.ack }, null, 2)}</pre></details>
    <button disabled={state.busy || !state.canReplay(command)} onClick={() => void state.execute(command)}>显式回放回合原 key {command.command_id}</button>
    {command.kind === 'prepare' && command.ack && <button disabled={state.busy || !state.allowed} onClick={() => void state.readPreparation(command)}>独立读取准备详情 {command.ack.id}</button>}
   </article>)}
  </section>
  {state.detail && <section aria-label="当前回合准备详情"><h4>独立 GET 的准备详情</h4><p>{state.detail.id} · {state.detail.validity} · Job {state.detail.job.id} · {state.detail.job.status}</p>
   {state.detail.validity === 'unavailable' && <p>当前准备不可用于执行（unavailable），原准备仍保留。缺完整输入证明时服务端拒绝 CODEX_INPUT_PROOF_UNAVAILABLE。</p>}
   <pre>{JSON.stringify(state.detail.request, null, 2)}</pre><pre>{JSON.stringify(state.detail.summary, null, 2)}</pre>
   <p>字符数不是完整 token 证明；生成、数学、来源与独立教学审查均未验收。</p>
  </section>}
  {state.page && <section aria-label="安全回合分页"><h4>本次只读分页快照</h4>{!state.page.items.length && <p>此页没有回合。</p>}
   {state.page.items.map(value => <article key={value.id}><p>{value.id} · {value.job.status} · {value.execution} · {value.outcome ?? '尚无终态'}</p><button disabled={blocked} onClick={() => void state.readControl(value.id)}>读取回合控制 {value.id}</button></article>)}
   {state.page.next_cursor && <button disabled={blocked} onClick={() => void state.readPage(true)}>继续读取安全回合</button>}
  </section>}
  {Object.values(state.controls).map(value => <section key={value.id} aria-label={`当前回合控制 ${value.id}`}><h4>当前安全控制 {value.id}</h4>
   <p>Job {value.job.id} · {value.job.status} · r{value.job_revision}；Run r{value.run_revision} · seq {value.last_seq}</p>
   <p>{value.execution} · {value.outcome ?? '尚无终态'} · cancel_requested={String(value.cancel_requested)} {value.error_code}</p>
   <button disabled={blocked} onClick={() => void state.readControl(value.id)}>刷新安全控制 {value.id}</button>
   <button disabled={blocked} onClick={() => void state.cancel(value)}>明确取消回合 Job {value.job.id}</button>
   <p>取消使用本次控制 GET 的 Job revision；ACK 和取消请求不证明远端已经停止。</p>
   <CodexTurnEventsPanel workspace={workspace} turn={value.id} run={value.job.id} admitted={state.allowed} port={eventPort} />
  </section>)}
  <CodexTurnOutboundPanel workspace={workspace} writeAdmitted={writeAdmitted} port={outboundPort} store={outboundStore} formStore={outboundFormStore} onState={setOutbound} />
 </section>
}
