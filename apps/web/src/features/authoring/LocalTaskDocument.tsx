import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { AuthoringPort } from './authoringClient'
import { checkedAuthoring } from './authoringCommands'

type Inputs = { topic: string; prerequisites: string; objectives: string; proof: 'full' | 'declared_dependencies' }
export type LocalTaskScope = { workspace: string; actor: string | null; port: Pick<AuthoringPort, 'session'> }
export function LocalTaskDocument({ workspace, actor, port, inputs, busy, denied }: LocalTaskScope & {
  inputs: Inputs; busy: boolean; denied: (reason: unknown) => void
}) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = JSON.stringify([workspace, actor, access, busy, inputs.topic, inputs.prerequisites, inputs.objectives, inputs.proof])
  const current = useRef({ owner, port }); current.current = { owner, port }
  const live = useRef(true), pending = useRef<object | null>(null), urls = useRef(new Set<string>())
  const [working, setWorking] = useState(false), [message, setMessage] = useState('')
  useEffect(() => {
    live.current = true; pending.current = null; setWorking(false); setMessage('')
    return () => { live.current = false; pending.current = null; for (const url of urls.current) URL.revokeObjectURL(url); urls.current.clear() }
  }, [owner, port])
  const download = async () => {
    if (!actor || busy || pending.current) return
    if (!inputs.topic.trim() || !inputs.objectives.trim()) { setMessage('请填写主题与学习目标；没有创建任务或下载文件。'); return }
    const token = {}, snapshot = { ...inputs }; pending.current = token; setWorking(true); setMessage('')
    const valid = () => live.current && pending.current === token && current.current.owner === owner && current.current.port === port && getSessionGeneration() === access
    try {
      const session = checkedAuthoring<SessionResponse>('SessionResponse', await port.session())
      if (!valid()) return
      if (session.workspace_id !== workspace || session.actor_session_id !== actor || session.role !== 'author' || session.active_independent_attempt_id !== null || session.active_open_book_attempt_id !== null) {
        throw new ApiError(403, '当前身份或测试策略已改变，未下载需求说明。')
      }
      const text = '# 离线创作需求说明\n\n本次下载未调用 Codex。本文件仅包含作者当前输入的四项需求，不含已选材料或其他任务设置；没有创建服务器任务、授权或生成结果。\n\n'
        + `## 主题\n\n${snapshot.topic}\n\n## 已声明先修\n\n${snapshot.prerequisites}\n\n## 学习目标\n\n${snapshot.objectives}\n\n## 证明策略\n\n${snapshot.proof === 'full' ? 'full（完整证明）' : 'declared_dependencies（明确声明所依赖的结论）'}\n`
      const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' })); urls.current.add(url)
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'learning-task.md'
      try { document.body.append(anchor); anchor.click() } finally { anchor.remove(); window.setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url) }, 0) }
      setMessage('已交给浏览器下载；临时表单仍未保存到服务器。返回文件请另从“导入”选择并预览，不证明 Codex 来源或质量。')
    } catch (reason) {
      if (!valid()) return
      if (reason instanceof ApiError && [401, 403].includes(reason.status)) denied(reason)
      setMessage('当前权限或下载未确认；原输入保留，请重新读取权限后明确重试。')
    } finally {
      if (pending.current === token) { pending.current = null; if (live.current) setWorking(false) }
    }
  }
  return <section aria-label="离线需求说明"><p>本次下载不调用 Codex：仅下载当前主题、先修、学习目标与证明策略。已选材料、来源引用、提供商及其他任务设置不在文件内；不会创建任务或授予执行权限。</p>
    <button disabled={busy || working || !actor} onClick={() => void download()}>下载当前四项需求说明</button>
    {working && <p role="status">正在重新核对当前作者与测试策略…</p>}{message && <p role="status">{message}</p>}
  </section>
}
