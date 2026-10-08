import type { CodexEventPort } from './turnEventClient'
import { useCodexTurnEvents } from './useCodexTurnEvents'

export function CodexTurnEventsPanel({ workspace, turn, run, admitted, port }: { workspace: string; turn: string; run: string; admitted: boolean; port?: CodexEventPort }) {
 const state = useCodexTurnEvents(workspace, turn, run, admitted, port), active = state.phase === 'connecting' || state.phase === 'connected'
 const answer = state.events.flatMap(value => value.payload.type === 'answer_delta' ? [value.payload.text] : []).join('')
 return <section aria-label={`Codex 回合事件 ${turn}`} style={{ overflowWrap: 'anywhere' }}><h5>只读事件连接</h5>
  <p>连接只读取此回合已经记录的事件。不会开始、批准、导入或发布；关闭不等于任务停止。</p>
  <button disabled={!state.allowed || active || state.phase === 'terminal'} onClick={() => void state.connect()}>{state.cursor ? `从原游标明确重连 ${run}:${state.cursor}` : `明确连接回合事件 ${turn}`}</button>
  <button disabled={!active} onClick={state.disconnect}>断开此事件连接</button>
  {!state.allowed && <p>事件正文仅向当前作者且学科策略允许时开放。</p>}
  {state.phase === 'connecting' && <p role="status">正在核验当前权限并连接。</p>}
  {state.phase === 'connected' && <p role="status">事件连接已建立；尚未观察到终态。</p>}
  {state.phase === 'denied' && <p role="status">当前 actor 或权限无法确认；事件显示已清除。请重新读取当前权限。</p>}
  {state.phase === 'disconnected' && <p role="status">连接中断，任务状态未知。请用原有明确 GET 读取当前控制或结果；此处不会自动重连。</p>}
  {state.cursor > 0 && <p>本页已核游标 {run}:{state.cursor}。刷新页面不继承此连接。</p>}
  {answer !== '' && <pre aria-label="Codex 事件原文" style={{ whiteSpace: 'pre-wrap' }}>{answer}</pre>}
  {state.events.map(value => <div key={value.seq}>
   {value.payload.type === 'status' && <p>事件 #{value.seq}：Job {value.payload.job.id} · {value.payload.job.status}；Run r{value.payload.run_revision}（历史事件）</p>}
   {value.payload.type === 'usage' && <p>事件 #{value.seq} 用量：输入 {value.payload.usage.input_tokens ?? '未知'}，输出 {value.payload.usage.output_tokens ?? '未知'}。</p>}
   {value.payload.type === 'approval_required' && <p>审批 ID {value.payload.approval_id}。须使用另行明确的审批详情入口读取；此事件不作决定。</p>}
   {value.payload.type === 'manifest_ready' && <p>产物清单 ID {value.payload.manifest_id}。须使用另行明确的清单详情入口读取；此事件不导入。</p>}
   {value.payload.type === 'terminal' && <p role="status">已观察终态事件：{value.payload.outcome}{value.payload.error_code ? ` · ${value.payload.error_code}` : ''}。当前控制和完整结果仍须另行明确 GET。</p>}
  </div>)}
 </section>
}
