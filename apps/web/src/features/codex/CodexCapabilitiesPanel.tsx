import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { CodexCapabilities, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { checkedCodex, codexCapabilityClient, type CodexCapabilityPort } from './codexClient'

type Observation = { owner: string; port: CodexCapabilityPort; value: CodexCapabilities | null; message: string }
const unknownMessage = '暂时无法确认 Codex 连接状态，请重新检查。'

export function CodexCapabilitiesPanel({ workspace, admitted, port = codexCapabilityClient }: {
  workspace: string; admitted: boolean; port?: CodexCapabilityPort
}) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = JSON.stringify([workspace, access, admitted])
  const currentOwner = useRef(owner); currentOwner.current = owner
  const currentPort = useRef(port); currentPort.current = port
  const operation = useRef(0), working = useRef(false), alive = useRef(false)
  const [observation, setObservation] = useState<Observation | null>(null)
  const [busyOwner, setBusyOwner] = useState<{ owner: string; port: CodexCapabilityPort } | null>(null)
  useEffect(() => { alive.current = true; return () => { alive.current = false; ++operation.current } }, [])
  useEffect(() => { ++operation.current; working.current = false; setObservation(null); setBusyOwner(null) }, [owner, port])
  const visible = admitted && observation?.owner === owner && observation.port === port ? observation : null
  const busy = admitted && busyOwner?.owner === owner && busyOwner.port === port

  const refresh = async () => {
    if (!admitted || !workspace || working.current || currentOwner.current !== owner || getSessionGeneration() !== access) return
    working.current = true
    const sequence = ++operation.current
    const current = () => alive.current && sequence === operation.current && currentOwner.current === owner && currentPort.current === port && getSessionGeneration() === access
    setBusyOwner({ owner, port }); setObservation(null)
    try {
      const session = checkedCodex<SessionResponse>('SessionResponse', await port.session())
      if (!current()) return
      if (session.workspace_id !== workspace || session.role !== 'author' || session.active_independent_attempt_id !== null || session.active_open_book_attempt_id !== null) {
        setObservation({ owner, port, value: null, message: '当前会话或测试策略不允许检查 Codex，请重新确认作者权限。' })
        return
      }
      const value = checkedCodex<CodexCapabilities>('CodexCapabilities', await port.capabilities())
      if (current()) setObservation({ owner, port, value, message: '' })
    } catch (reason) {
      if (current()) setObservation({ owner, port, value: null, message: reason instanceof ApiError && (reason.status === 401 || reason.status === 403 || reason.status === 409)
        ? '当前会话或测试策略不允许检查 Codex，请重新确认作者权限。' : unknownMessage })
    } finally {
      if (current()) { working.current = false; setBusyOwner(null) }
    }
  }
  const value = visible?.value
  return <section aria-label="Codex 连接状态">
    <h3>Codex 文件创作</h3>
    <p>检查此工作区隔离 Broker 的连接与授权状态；这不会启动生成或执行工具。</p>
    <button disabled={!admitted || !workspace || busy} onClick={() => void refresh()}>{busy ? '正在检查 Codex 连接…' : '检查 Codex 连接'}</button>
    {!admitted ? <p role="status">请在作者会话且测试策略允许后检查 Codex。</p>
      : busy ? <p role="status">正在读取本机连接状态。</p>
        : visible?.message ? <p role="status">{visible.message} 当前状态未知。</p>
          : !value ? <p role="status">尚未检查 Codex 连接。</p>
            : <>
              <p role="status">{!value.available ? '未连接 Codex：未发现可用的本机适配器。' : !value.authorized ? '未连接 Codex：此工作区的隔离 Broker 尚未授权。' : '此工作区的 Codex 连接与授权状态已确认。'}</p>
              <p>此结果仅属于当前工作区的隔离 Broker，不表示其他 Codex 会话的登录状态。</p>
              <dl><dt>适配器版本</dt><dd>{value.adapter_version ?? '不可用'}</dd>
                <dt>操作审批</dt><dd>{value.capabilities.approvals ? '可用' : '不可用'}</dd>
                <dt>中断任务</dt><dd>{value.capabilities.interrupt ? '可用' : '不可用'}</dd>
                <dt>产物清单</dt><dd>{value.capabilities.artifacts ? '可用' : '不可用'}</dd></dl>
              {value.sandbox_roots.length > 0 && <div><p>隔离目录</p><ul>{value.sandbox_roots.map(root => <li key={root.id}>{root.label}</li>)}</ul></div>}
            </>}
    {admitted && <p>受控 Codex 任务导出尚未实现；已有受检产物可从下方清单明确选择回导预览。当前可下载四项本地需求说明；该本地需求说明不调用 Codex。已有文件可从“导入”进入预览与审核。</p>}
  </section>
}
