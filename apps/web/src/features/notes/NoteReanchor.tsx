import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, Selection, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, request, subscribeSessionAccess } from '../../api/client'
import { checkedProvider } from '../providers/providerSchema'
import { readBlock, type LoadedBlock } from '../reader/contentClient'
import { selectionFromTextarea } from '../reader/selection'
import { sameRef } from '../reader/target'

// Read-only preparation. Adoption changes the local Note draft; its owner
// still performs the separate, explicit CAS save.
export function NoteReanchor({ workspace, noteId, original, disabled, adopt }: {
  workspace: string; noteId: string; original: ContentRef; disabled: boolean; adopt: (selection: Selection) => void
}) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const key = JSON.stringify([workspace, noteId, original, access]), owner = useRef({ key, sequence: 0, disabled })
  if (owner.current.key !== key) owner.current = { key, sequence: owner.current.sequence + 1, disabled }
  owner.current.disabled = disabled
  const empty = { key, block: null as LoadedBlock | null, permission: '', selected: null as Selection | null, busy: false, error: '' }
  const [stored, setStored] = useState(empty), state = stored.key === key ? stored : empty
  const patch = (change: Partial<typeof stored>) => setStored(old => ({ ...(old.key === key ? old : empty), ...change }))
  const current = (sequence: number) => owner.current.key === key && owner.current.sequence === sequence && getSessionGeneration() === access
  const clear = () => { owner.current.sequence++; patch({ block: null, selected: null, permission: '', busy: false, error: '当前读取权限需要重新核验；原笔记和本机草稿未改动。' }) }
  useEffect(() => () => { owner.current.sequence++ }, [])
  useEffect(() => {
    const visibility = () => { if (document.visibilityState !== 'visible') clear() }
    window.addEventListener('focus', clear); document.addEventListener('visibilitychange', visibility)
    return () => { window.removeEventListener('focus', clear); document.removeEventListener('visibilitychange', visibility) }
  }, [key])
  const permission = async () => {
    let deadline = 0
    try {
      const actual = await Promise.race([request('GET /api/v1/session', undefined), new Promise<never>((_resolve, reject) => { deadline = window.setTimeout(() => reject(new Error('权限读取超时。')), 2000) })])
      const session = checkedProvider<SessionResponse>('SessionResponse', actual)
      if (session.workspace_id !== workspace || session.active_independent_attempt_id !== null) throw new Error('当前工作区或测试策略不允许读取笔记材料。')
      return JSON.stringify([session.workspace_id, session.actor_session_id, session.role, session.active_independent_attempt_id, session.active_open_book_attempt_id])
    } finally { window.clearTimeout(deadline) }
  }
  useEffect(() => {
    if (!state.block || !state.permission || state.busy) return
    const sequence = owner.current.sequence; let live = true, timer = 0, deadline = 0
    const valid = () => live && current(sequence)
    const poll = async () => {
      deadline = window.setTimeout(() => { if (valid()) clear() }, 2000)
      try { if (await permission() !== state.permission && valid()) clear() } catch { if (valid()) clear() }
      finally { window.clearTimeout(deadline); if (valid()) timer = window.setTimeout(() => void poll(), 2000) }
    }
    timer = window.setTimeout(() => void poll(), 2000)
    return () => { live = false; window.clearTimeout(timer); window.clearTimeout(deadline) }
  }, [key, state.block, state.permission, state.busy])
  const read = async () => {
    if (disabled || state.busy) return
    const sequence = ++owner.current.sequence; patch({ block: null, selected: null, permission: '', busy: true, error: '' })
    try {
      const allowed = await permission(); if (!current(sequence) || owner.current.disabled) return
      const ref = checkedProvider<ContentRef>('ContentRef', await request('GET /api/v1/objects/{id}/current', undefined, undefined, { path: { id: original.id } }))
      if (!current(sequence) || owner.current.disabled) return
      if (ref.entity !== 'block' || ref.id !== original.id) throw new Error('当前引用不属于原笔记的同一公开块。')
      const block = await readBlock(ref); if (!current(sequence) || owner.current.disabled) return
      if (await permission() !== allowed) throw new Error('读取期间会话或策略变化。')
      if (current(sequence) && !owner.current.disabled) patch({ block, permission: allowed })
    } catch { if (current(sequence)) patch({ block: null, selected: null, error: '无法确认当前块的权限、准确引用或原文字节；原笔记保持不变。' }) }
    finally { if (current(sequence)) patch({ busy: false }) }
  }
  const apply = async () => {
    if (disabled || state.busy || !state.selected || !state.block) return
    const selection = state.selected, allowed = state.permission, sequence = ++owner.current.sequence; patch({ busy: true, error: '' })
    try {
      if (await permission() !== allowed) { if (current(sequence)) clear(); return }
      if (!current(sequence) || owner.current.disabled) return
      adopt(selection); patch({ block: null, selected: null, permission: '' })
    } catch { if (current(sequence)) clear() }
    finally { if (current(sequence)) patch({ busy: false }) }
  }
  return <section className="note-reanchor" aria-label="手工选择新的笔记锚点">
    <p>旧锚点不会自动迁移。单独读取同一块的当前修订并选择原文，先采用到本机草稿，再明确保存笔记。教材父引用保持原样。</p>
    <button disabled={disabled || state.busy} onClick={() => void read()}>读取此块当前修订以手工重锚</button>
    {state.busy && <p role="status">正在核验准确原文与当前权限…</p>}{state.error && <p role="alert">{state.error}</p>}
    {state.block && <><p>以下是此次读取并核验的准确修订；当前指针之后变化不会自动替换这份选文。</p><p>准确新依据：{state.block.block_ref.id} · 修订 {state.block.block_ref.revision} · <code>{state.block.block_ref.sha256}</code></p>
      <p>完整正文 SHA256：<code>{state.block.block.body_sha256}</code></p>
      {sameRef(state.block.block_ref, original) && <p>当前指针仍是原锚点修订；不会仅据读取清除 stale。</p>}
      <details><summary>核对当前块完整元数据</summary><pre>{JSON.stringify(state.block.block, null, 2)}</pre></details>
      <label>当前准确修订的完整原文<textarea readOnly disabled={disabled || state.busy} value={state.block.body} onSelect={event => {
        if (disabled || state.busy || !state.block || owner.current.key !== key) return
        const result = selectionFromTextarea(state.block.block_ref, state.block.body, event.currentTarget.selectionStart, event.currentTarget.selectionEnd)
        patch({ selected: result.kind === 'selected' ? result.selection : null, error: result.kind === 'rejected' ? result.message : '' })
      }} /></label>
      {state.selected && <><p>新选文码点 [{state.selected.start_codepoint}, {state.selected.end_codepoint})，未提交到服务端。</p><blockquote>{state.selected.exact_quote}</blockquote></>}
      <button disabled={disabled || state.busy || !state.selected} onClick={() => void apply()}>将这份准确新选文采用到本机笔记</button>
    </>}
  </section>
}
