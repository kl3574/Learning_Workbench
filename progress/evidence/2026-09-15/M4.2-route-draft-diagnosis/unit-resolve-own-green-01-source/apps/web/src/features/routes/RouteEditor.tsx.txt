import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, Route } from '../../../../../packages/contracts/generated/types'
import { ApiError, getSessionGeneration, request, subscribeSessionAccess } from '../../api/client'
import { sameRef } from '../reader/target'
import { readRoutes, type RouteRecord } from './routeClient'
import { readRouteChoices } from './routeChoices'
import { RouteEditorFields, type RouteChoice } from './RouteEditorFields'
import { decodeRouteDraft, newRouteDraft, routeDirty, routeDraftKey, routeStore, routeValidation, useRouteJournal, type RouteEnvelope } from './routeDrafts'
import '../learning/learning.css'
import './routes.css'
export function RouteEditor({ workspace, initial, paused, onState, saved }: { workspace: string; initial: RouteRecord | null; paused: boolean; onState: (value: { dirty: boolean; safe: boolean }) => void; saved: (ref: ContentRef) => void }) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration), identity = `${workspace}:${access}`, owner = useRef(identity); owner.current = identity
  const journal = useRouteJournal(workspace), [editor, setEditor] = useState<RouteEnvelope | null>(null), [choices, setChoices] = useState<{ owner: string; items: RouteChoice[] } | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false), [remote, setRemote] = useState<RouteRecord | null>(null)
  const live = useRef(editor); live.current = editor
  const callback = useRef(onState); callback.current = onState
  const epoch = useRef(0), active = useRef(true); active.current = !paused
  const record = editor ? journal.records[routeDraftKey(editor)] : null
  const candidates: { text: string; value: RouteEnvelope }[] = []; let decodeError = ''
  for (const value of Object.values(journal.records)) for (const text of new Set([value.text, ...value.conflicts.map(item => item.text)])) {
    try { const item = decodeRouteDraft(text, workspace); if (routeDirty(item) && (!initial || item.candidate.id === initial.ref.id)) candidates.push({ text, value: item }) } catch (reason) { decodeError = reason instanceof Error ? reason.message : '路线候选无法读取，原数据保留。' }
  }
  const safe = journal.ready && !journal.unsafe && !journal.error && !decodeError
  const dirty = !!editor && routeDirty(editor) || candidates.length > 0
  useEffect(() => { callback.current({ dirty, safe }) }, [dirty, safe])
  useEffect(() => {
    const sequence = ++epoch.current
    setBusy(false)
    if (paused) return
    void readRouteChoices().then(items => { if (sequence === epoch.current) setChoices({ owner: identity, items }) }).catch(reason => { if (sequence === epoch.current) setError(`任务目录尚未读回：${reason instanceof Error ? reason.message : ''}`) })
    return () => { ++epoch.current }
  }, [identity, paused])
  const persist = (value: RouteEnvelope) => { live.current = value; setEditor(value); journal.save(value) }
  const begin = () => { if (paused || !safe || busy) return; persist(newRouteDraft(workspace, initial?.route ?? null, initial?.ref ?? null)); setError('') }
  const change = (candidate: Route) => { if (!editor || paused || busy || record?.conflicts.length) return; persist({ ...editor, candidate, command_id: `route_command_${crypto.randomUUID()}`, acknowledged: null }); setError('') }
  const restore = async (candidate: { text: string; value: RouteEnvelope }) => {
    const captured = identity, sequence = epoch.current
    if (paused || busy || !safe) return
    setBusy(true)
    try {
      const key = routeDraftKey(candidate.value), disk = (await routeStore.load(workspace))[key]
      if (!disk || ![disk.text, ...disk.conflicts.map(item => item.text)].includes(candidate.text)) throw new Error('候选尚未从本机存储读回。')
      const value = disk.conflicts.length ? await journal.resolve(key, candidate.text) : decodeRouteDraft(candidate.text, workspace)
      if (owner.current !== captured || !active.current || sequence !== epoch.current) return
      live.current = value; setEditor(value); setError('')
    } catch (reason) { if (owner.current === captured && sequence === epoch.current) setError(reason instanceof Error ? reason.message : '候选恢复失败。') } finally { if (owner.current === captured && sequence === epoch.current) setBusy(false) }
  }
  const submit = async () => {
    const value = live.current, captured = identity, sequence = epoch.current
    if (!value || paused || busy || !safe || record?.conflicts.length) return
    const invalid = routeValidation(value.candidate); if (invalid) { setError(invalid); return }
    setBusy(true); setError('')
    try {
      const disk = (await routeStore.load(workspace))[routeDraftKey(value)]
      if (!disk || ![disk.text, ...disk.conflicts.map(item => item.text)].includes(JSON.stringify(value))) throw new Error('当前路线命令尚未持久化，不发送。')
      if (owner.current !== captured || !active.current || sequence !== epoch.current) return
      const headers = { 'Idempotency-Key': value.command_id }
      const ref = value.base_ref ? await request('PUT /api/v1/routes/{id}', value.candidate, { ...headers, 'If-Match': `"${value.base_ref.sha256}"` }, { path: { id: value.base_ref.id } }) : await request('POST /api/v1/routes', value.candidate, headers)
      const acknowledged = decodeRouteDraft(JSON.stringify({ ...value, acknowledged: ref }), workspace)
      // This receipt confirms only its original command. A policy refresh can
      // allow a newer local branch before it arrives; never replace that branch.
      if (live.current?.workspace_id === workspace && live.current.command_id === value.command_id) {
        journal.save(acknowledged); live.current = acknowledged; setEditor(acknowledged)
      }
      if (owner.current !== captured || !active.current || sequence !== epoch.current) return
      setRemote(null)
    } catch (reason) {
      if (owner.current !== captured || !active.current || sequence !== epoch.current) return
      if (reason instanceof ApiError && reason.status === 412) {
        setRemote(null)
        try { const items = await readRoutes(); if (owner.current === captured && sequence === epoch.current) setRemote(items.filter(item => item.ref.id === value.candidate.id).sort((a, b) => b.ref.revision - a.ref.revision)[0] ?? null) } catch { /* keep unknown rather than fabricate a current revision */ }
      }
      if (owner.current === captured && sequence === epoch.current) setError(`路线未确认保存，候选与原命令保留。${reason instanceof Error ? reason.message : ''}`)
    } finally { if (owner.current === captured && sequence === epoch.current) setBusy(false) }
  }
  if (paused) return <p>当前策略尚未核验或限制路线操作。编辑候选保留，恢复权限后继续。</p>
  return <section className="learning-panel route-editor" aria-label="路线编辑"><p>任务绑定真实内容的精确修订。保存生成新路线修订；旧路线与旧人工完成记录保留，先修只作提醒。</p><p role="status">{journal.saving ? '路线草稿保存中…' : safe ? '本机路线草稿存储可用' : '路线草稿尚未安全保存'}</p>{[error, journal.error, decodeError].filter(Boolean).map((message, index) => <p role="alert" key={index}>{message}</p>)}{journal.error && editor && <button onClick={() => journal.save(editor)}>重试本机路线保存</button>}
    {(!editor || !!record?.conflicts.length) && candidates.length > 0 && <section><h3>本机路线候选</h3>{candidates.map((candidate, index) => <details className="learning-candidate" open key={candidate.text}><summary>路线候选 {index + 1} · {candidate.value.candidate.title || '未命名路线'}</summary><p>{candidate.value.candidate.goal}</p><p>{candidate.value.candidate.steps.map(step => step.title).join(' → ')}</p><button disabled={!safe || busy} onClick={() => void restore(candidate)}>恢复路线候选 {index + 1}</button></details>)}</section>}
    {!editor && <button disabled={!safe || busy || candidates.length > 0} onClick={begin}>{initial ? '编辑此路线修订' : '填写新路线'}</button>}
    {editor && (editor.acknowledged ? <><p role="status">路线已保存为修订 {editor.acknowledged.revision}。旧修订未覆盖。</p><button disabled={!safe} onClick={() => saved(editor.acknowledged!)}>打开已保存路线</button></> : <><RouteEditorFields value={editor.candidate} choices={choices?.owner === identity ? choices.items : []} disabled={busy || !!record?.conflicts.length || !journal.ready} change={change} />{remote && !sameRef(remote.ref, editor.base_ref) && <section className="learning-comparison"><h3>路线版本冲突：比较并明确选择</h3><div><section><h4>原基准 r{editor.base?.revision ?? '未知'}</h4><p>{editor.base?.goal}</p><p>{editor.base?.steps.map(step => step.title).join(' → ')}</p></section><section><h4>本页候选</h4><p>{editor.candidate.goal}</p><p>{editor.candidate.steps.map(step => step.title).join(' → ')}</p></section><section><h4>服务端 r{remote.ref.revision}</h4><p>{remote.route.goal}</p><p>{remote.route.steps.map(step => step.title).join(' → ')}</p></section></div><button disabled={!safe || busy} onClick={() => { persist({ ...newRouteDraft(workspace, remote.route, remote.ref), candidate: { ...editor.candidate, revision: remote.ref.revision + 1 } }); setRemote(null) }}>保留本页路线并采用服务端基准</button></section>}<div className="learning-actions"><button className="primary-button" disabled={!safe || busy || !!record?.conflicts.length || !!remote} onClick={() => void submit()}>保存路线新修订</button>{error && <button disabled={!safe || busy || !!record?.conflicts.length} onClick={() => void submit()}>重试原路线保存命令</button>}</div></>)}
  </section>
}
