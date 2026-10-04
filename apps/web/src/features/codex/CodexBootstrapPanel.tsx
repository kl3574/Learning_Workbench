import { useEffect, useRef } from 'react'
import type { DraftStore } from '../../workbench/DraftStore'
import type { BootstrapPort } from './bootstrapClient'
import { useBootstrap } from './useBootstrap'
export type BootstrapPanelState = { dirty: boolean; safe: boolean; isolated: boolean }
export function CodexBootstrapPanel({ workspace, writeAdmitted, port, store, onState }: {
 workspace: string; writeAdmitted: boolean; port?: BootstrapPort; store?: DraftStore; onState?: (value: BootstrapPanelState) => void
}) {
 const state = useBootstrap(workspace, writeAdmitted, port, store), callback = useRef(onState); callback.current = onState
 useEffect(() => { callback.current?.({ dirty: state.dirty, safe: state.safe, isolated: state.isolated }) }, [state.dirty, state.safe, state.isolated])
 const current = state.current, owns = current?.actor_session_id === state.actor
 const writable = state.allowed && !state.busy && owns
 return <section aria-label="本地控制会话"><h3>本地控制会话</h3>
  <p>仅准备并明确批准一次隔离的本地 thread 映射。不会开启对话、登录、工具或教材读取。</p>
  <button disabled={!workspace || state.busy} onClick={() => void state.refresh()}>读取本地会话记录</button>
  <button disabled={!state.allowed || state.busy} onClick={() => void state.make('prepare')}>准备本地控制会话</button>
  {!state.ready ? <p>尚未读取当前会话与本机原命令。</p> : !state.allowed && <p>当前仅可读取安全控制元数据。新操作需要原作者会话且测试策略允许。</p>}
  {state.error && <p role="status">{state.error}</p>}{state.message && <p role="status">{state.message}</p>}
  {state.busy && <p role="status">正在处理；不自动重发命令。</p>}
  {state.canSave && <p>当前合法读者可仅保存原 actor 归属的控制事实；不改变原命令，也不取得执行权限。</p>}
  {state.canSave && <button disabled={state.busy} onClick={() => void state.saveMemory()}>仅保存原会话已收到的事实</button>}
  <section aria-label="本地会话原命令"><h4>原命令与历史 ACK</h4>
   {state.commands.some(v => !v.ack) && <p>仍有结果未确认的原命令；新准备不会清除旧未知事实，也不继承旧许可。</p>}
   {state.commands.map(command => <article key={command.command_id}><p>{command.kind} · {command.ack ? '原 ACK 已记录（不是当前资格）' : command.error ? '已收到安全错误；当前实例须另读' : '结果未知，原 key 与完整 body 保留'}</p>
    {command.actor_session_id !== state.actor && <p>其他原会话的命令仅只读保留，当前 actor 不能接管。</p>}
    <details><summary>核对原控制命令 {command.command_id}</summary><p>原 actor：{command.actor_session_id}</p><pre>{JSON.stringify(command.body, null, 2)}</pre>{command.ack && <pre>{JSON.stringify(command.ack, null, 2)}</pre>}</details>
    <button disabled={state.busy || !state.canReplay(command)} onClick={() => void state.execute(command)}>显式回放原 key {command.command_id}</button>
   </article>)}
  </section>
  {state.ids.map(id => <button key={id} disabled={state.busy} onClick={() => void state.readPreparation(id)}>读取准备当前状态 {id}</button>)}
  {current && <section aria-label="当前冻结准备"><h4>冻结范围：仅本地控制建会话</h4>
   <p>准备 {current.id} · r{current.revision} · {current.status} · 当前资格 {current.validity}</p>
   <dl><dt>逻辑根</dt><dd>{current.scope.sandbox_root_id} · {current.scope.sandbox_label}</dd><dt>固定适配版本</dt><dd>{current.scope.adapter_version}</dd>
    <dt>受限 profile SHA256</dt><dd><code>{current.scope.bootstrap_profile_sha256}</code></dd><dt>完整操作 SHA256</dt><dd><code>{current.operation_sha256}</code></dd>
    <dt>有效区间（UTC）</dt><dd>{current.created_at} → {current.expires_at}</dd></dl>
   <p>允许 actions：[]；零模型、零工具、零学科读取、零网络。</p>
   {current.status === 'pending' && <><button disabled={!writable || current.validity !== 'current' || state.hasOriginal('decision', current.id)} onClick={() => void state.make('approve_once')}>仅批准这一次本地建会话</button>
    <button disabled={!writable || ['expired', 'closed'].includes(current.validity) || state.hasOriginal('decision', current.id)} onClick={() => void state.make('decline')}>拒绝这次本地建会话</button></>}
   {current.status === 'approved' && <button disabled={!writable || current.validity !== 'current' || state.hasOriginal('create', current.id)} onClick={() => void state.make('create')}>明确创建这次本地会话</button>}
   {current.session_id && <p>已消费许可，绑定 session：{current.session_id}。closed 不清除原实例。</p>}
  </section>}
  {state.sessions.map(value => <section aria-label={`当前本地会话 ${value.id}`} key={value.id}><h4>当前 session {value.id}</h4><p>真实本地记录：{value.status} · r{value.revision}</p>
   {value.status === 'ready' ? <p>ready 仅表示已核验 thread 映射；不代表账号授权、模型能力或进程仍在运行。</p>
    : value.status === 'unknown' ? <p>旧实例结果未知。不会自动再启动；如需另试，须另建准备并重新批准。</p>
    : value.status === 'initializing' ? <p>开始许可已登记，尚不能断言 thread 已建立。</p> : <p>本次本地会话创建失败；保留原事实。</p>}
   <p>active_turn_id：{value.active_turn_id ?? 'null'}；审批、interrupt、artifacts：{String(value.capabilities.approvals)}、{String(value.capabilities.interrupt)}、{String(value.capabilities.artifacts)}。</p></section>)}
 </section>
}
