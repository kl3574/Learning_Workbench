import { useEffect, useRef, useState } from 'react'
import { request, subscribeSessionAccess } from '../../api/client'
export function useWorkspacePolicy(workspace: string | null) {
  const [value, setValue] = useState<{ workspace: string | null; known: boolean; independentId: string | null; error: string }>({ workspace: null, known: false, independentId: null, error: '' })
  const refresh = useRef<() => void>(() => {})
  useEffect(() => {
    let live = true, epoch = 0, sequence = 0, applied = 0
    if (!workspace) return
    const read = async (invalidate = false) => {
      // Explicit access/focus changes invalidate every earlier read. Background
      // polls accept the newest completed read without starving slow responses.
      if (invalidate) { ++epoch; setValue(old => ({ ...old, known: false })) }
      const owner = epoch, requestSequence = ++sequence
      const current = () => live && owner === epoch && requestSequence > applied
      try {
        const session = await request('GET /api/v1/session', undefined)
        if (session.workspace_id !== workspace) throw new Error('工作区会话已变化，请重新连接。')
        if (current()) { applied = requestSequence; setValue({ workspace, known: true, independentId: session.active_independent_attempt_id, error: '' }) }
      } catch (reason) { if (current()) { applied = requestSequence; setValue(old => ({ ...old, workspace, known: false, error: reason instanceof Error ? reason.message : '尚未核验当前测试策略。' })) } }
    }
    refresh.current = () => void read(true)
    void read(true)
    const unsubscribe = subscribeSessionAccess(() => void read(true))
    const focus = () => void read(true)
    // Server state also covers other browser profiles that do not share broadcasts.
    const timer = setInterval(() => void read(), 2000)
    window.addEventListener('focus', focus)
    return () => { live = false; ++epoch; clearInterval(timer); unsubscribe(); window.removeEventListener('focus', focus) }
  }, [workspace])
  const known = value.workspace === workspace && value.known
  return { known, independentId: value.workspace === workspace ? value.independentId : null, error: value.error, refresh: () => refresh.current() }
}
