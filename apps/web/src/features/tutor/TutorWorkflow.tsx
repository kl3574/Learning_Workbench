import { useState } from 'react'
import type { useTutor } from './useTutor'
import { TutorEvidence } from './TutorEvidence'
import { TutorConsent } from './TutorConsent'
import { contextIdentity, terminalRun } from './tutorState'
import './tutor.css'
const labels = { thread: '创建线程', run: '创建问答任务', cancel: '取消任务' }
export function TutorWorkflow({ workspace, state, settings }: { workspace: string; state: ReturnType<typeof useTutor>; settings: () => void }) {
  const [title, setTitle] = useState('围绕当前内容的问答')
  const root = state.bound ? contextIdentity(state.bound.scope, state.bound.binding) : null
  const commands = state.commands.filter(value => value.root === root)
  const pending = commands.filter(value => !value.ack)
  return <section className="tutor-workflow" aria-label="真实问答线程与任务">
    <p>发送先建立本地任务并准备上下文，不自动外发；随后核对并明确批准本次授权。</p>
    {state.error && <p role="alert">{state.error}</p>}
    {!state.ready && <p role="status">正在读取本机原命令；未发送新任务。</p>}
    <button disabled={state.busy} onClick={() => void state.refreshThreads()}>重新读取线程与当前绑定</button>
    {state.bound && <>
      <label>新线程标题<input value={title} maxLength={200} onChange={event => setTitle(event.target.value)} /></label>
      <button disabled={!title.trim() || state.busy || !state.ready} onClick={() => state.createThread(title)}>明确创建本地线程</button>
      <div className="tutor-thread-list" aria-label="当前对象的真实线程">{state.threads.length ? state.threads.map(value => <button key={value.id} aria-pressed={state.thread?.id === value.id} disabled={state.busy} onClick={() => void state.select(value)}>{value.title} · r{value.revision}</button>) : <p>当前已读取页没有此精确对象的线程；可创建或继续读取服务器列表。</p>}</div>
      {state.threadCursor && <button disabled={state.busy} onClick={() => void state.refreshThreads(true)}>载入下一页线程</button>}
    </>}
    {state.thread && <><p>当前真实线程：{state.thread.title} · r{state.thread.revision} · {state.thread.id}</p><button disabled={state.busy} onClick={() => void state.select(state.thread!)}>刷新本线程消息</button>{state.messageCursor && <button disabled={state.busy} onClick={() => void state.select(state.thread!, true)}>载入下一页消息</button>}</>}
    {pending.length > 0 && <details open><summary>原命令与未确认结果</summary>{pending.map(command => <article key={command.command_id}><h4>{labels[command.kind]}</h4><p>原 key：{command.command_id}</p>{command.kind === 'run' && <pre className="tutor-original">{command.body.request.message}</pre>}{command.rejection ? <p>服务端已明确拒绝原命令（{command.rejection.status} / {command.rejection.code ?? '无错误码'}）。原记录保留；重新核对当前线程与问题后可明确创建新的命令。</p> : <p>原结果尚未确认，不会改正文或创建第二个 key。</p>}<button disabled={state.busy || !state.ready} onClick={() => void state.execute(command)}>回放原{labels[command.kind]}命令</button></article>)}</details>}
    {state.run && <section aria-label="当前问答任务"><h3>真实任务状态：{state.run.run.status}</h3><details><summary>任务详情</summary><p>{state.run.run.id} · Jobs r{state.run.job_revision} · 事件水位 {state.run.run.last_seq}</p></details><p role="status">{state.streamState}</p>{state.run.result.error_code && <p role="alert">{state.run.result.error_code}：保留当前原文与诊断，没有伪造成功回答。</p>}<button disabled={state.busy} onClick={() => void state.refreshRun()}>读取快照并恢复观察</button><button disabled={state.busy || !state.ready || terminalRun(state.run)} onClick={state.cancel}>明确取消本次问答任务</button><p>关闭页面只断开观察。取消请求不等于提供商已停，也不承诺退款。</p></section>}
    <TutorEvidence value={state.run} messages={state.messages} />
    {state.run && !terminalRun(state.run) && <TutorConsent key={`${workspace}:${root}:${state.run.run.id}`} workspace={workspace} run={state.run} refresh={state.refreshRun} settings={settings} />}
  </section>
}
