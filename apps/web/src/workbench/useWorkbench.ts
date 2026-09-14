import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError, connectSession, readSession, saveSession } from '../api/client'
import { emptySession, normalizeSession, type Session } from './model'
export type SaveState = 'connecting' | 'saved' | 'saving' | 'offline' | 'conflict'
const lastWorkspaceKey = 'learning-workbench.last-confirmed-workspace.v1'
const pendingKey = (workspace: string) => `learning-workbench.${workspace}.pending-ui.v1`
const draftsKey = (workspace: string) => `learning-workbench.${workspace}.unsent-drafts.v1`
function loadDrafts(workspace: string | null): Record<string, string> { if (!workspace) return {}; try { return JSON.parse(localStorage.getItem(draftsKey(workspace)) ?? '{}') } catch { return {} } }
export function useWorkbench() {
  const cache = useQueryClient()
  const [session, setSession] = useState<Session>(emptySession)
  const [status, setStatus] = useState<SaveState>('connecting')
  const [error, setError] = useState('')
  const workspace = useRef<string | null>(localStorage.getItem(lastWorkspaceKey))
  const [drafts, setDrafts] = useState(() => loadDrafts(workspace.current))
  const live = useRef(session)
  const version = useRef(0)
  const savedVersion = useRef(0)
  const inFlight = useRef(false)
  const connected = useRef(false)
  const set = useCallback((update: Session | ((old: Session) => Session)) => {
    const next = typeof update === 'function' ? update(live.current) : update
    live.current = next; version.current++; setSession(next)
    if (workspace.current) localStorage.setItem(pendingKey(workspace.current), JSON.stringify(next))
    setStatus(old => old === 'conflict' ? old : connected.current ? 'saving' : 'offline')
  }, [])
  const reconnect = useCallback(async (useServer = false) => {
    setStatus('connecting')
    try {
      const authenticatedWorkspace = await connectSession()
      workspace.current = authenticatedWorkspace
      localStorage.setItem(lastWorkspaceKey, authenticatedWorkspace)
      setDrafts(loadDrafts(authenticatedWorkspace))
      const remote = normalizeSession(await cache.fetchQuery({ queryKey: ['workbench-session'], queryFn: readSession, staleTime: 0 }))
      connected.current = true
      let pending: Session | null = null
      try { pending = JSON.parse((workspace.current ? localStorage.getItem(pendingKey(workspace.current)) : null) ?? 'null') } catch { /* malformed local cache is never sent */ }
      if (!useServer && pending && pending.revision !== remote.revision) {
        live.current = pending; setSession(pending); setStatus('conflict'); setError('另一个窗口更新了会话。当前本地布局与标签已保留，请选择读取服务端会话；对象草稿仍保留。'); return
      }
      const restored = !useServer && pending ? normalizeSession(pending) : remote
      live.current = restored; setSession(restored)
      if (useServer) workspace.current && localStorage.removeItem(pendingKey(workspace.current))
      version.current = pending && !useServer ? 1 : 0; savedVersion.current = 0
      setStatus(pending && !useServer ? 'saving' : 'saved'); setError('')
    } catch (e) {
      connected.current = false; setStatus('offline')
      setError(e instanceof ApiError && e.status === 401 ? '尚未建立本机会话。请从 make dev 或 make start 输出的一次性启动链接打开；当前改动仅在本机浏览器暂存。' : `服务连接失败，改动保留在本机浏览器。${(e as Error).message}`)
      try { const local = JSON.parse((workspace.current ? localStorage.getItem(pendingKey(workspace.current)) : null) ?? 'null'); if (local) { live.current = normalizeSession(local); setSession(live.current) } } catch { /* keep safe initial session */ }
    }
  }, [cache])
  useEffect(() => { void reconnect() }, [reconnect])
  useEffect(() => {
    if (status !== 'saving') return
    const timer = setTimeout(async () => {
      if (!connected.current || inFlight.current || version.current === savedVersion.current) return
      inFlight.current = true
      const writingVersion = version.current
      try {
        const saved = normalizeSession(await saveSession(live.current))
        savedVersion.current = writingVersion
        const next = version.current === writingVersion ? saved : { ...live.current, revision: saved.revision }
        live.current = next; setSession(next); cache.setQueryData(['workbench-session'], saved)
        if (version.current === writingVersion) { workspace.current && localStorage.removeItem(pendingKey(workspace.current)); setStatus('saved') }
        else { if (workspace.current) localStorage.setItem(pendingKey(workspace.current), JSON.stringify(next)); setStatus('saving') }
        setError('')
      } catch (e) {
        setStatus(e instanceof ApiError && e.status === 412 ? 'conflict' : 'offline')
        setError(e instanceof ApiError && e.status === 412 ? '会话版本冲突，本地标签、布局与草稿已保留。读取服务端会话后可继续。' : `保存失败：${(e as Error).message}。本地改动仍保留。`)
      } finally { inFlight.current = false }
    }, 350)
    return () => clearTimeout(timer)
  }, [session, status, cache])
  const updateDraft = (id: string, text: string) => setDrafts(old => { const next = { ...old, [id]: text }; workspace.current && localStorage.setItem(draftsKey(workspace.current), JSON.stringify(next)); return next })
  return { session, set, status, error, drafts, updateDraft, reconnect }
}
