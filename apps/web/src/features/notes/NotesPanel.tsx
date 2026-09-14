import { useEffect, useRef, useState } from 'react'
import { request } from '../../api/client'
import type { ContentRef, Note, Selection } from '../../../../../packages/contracts/generated/types'
import type { PageNote } from '../../../../../packages/contracts/generated/api-types'
import type { DraftRecord } from '../../workbench/DraftStore'
import { DraftConflictPreview } from '../../workbench/DraftConflictPreview'
import { decodeNoteEnvelope, noteDirty, noteKey, type NoteEnvelope } from './noteDrafts'
import { useNoteDrafts } from './useNoteDrafts'
import './notes.css'
type Conflict = { base: Note | null; local: Note; remote: Note; remoteRef: ContentRef }
function previewCandidate(text: string, workspace: string): string { try { return decodeNoteEnvelope(text, workspace).candidate.markdown } catch { return '此候选无法安全解析，原记录保留。' } }
const keys = () => ({ 'Idempotency-Key': crypto.randomUUID() })
async function currentNote(note: Note): Promise<{ note: Note; ref: ContentRef }> {
  let cursor: string | null = null
  do {
    // The note ID survives a concurrent re-anchor to a different block.
    const page: PageNote = await request('GET /api/v1/notes', undefined, undefined, { query: { limit: 100, ...(cursor ? { cursor } : {}) } })
    const found = page.items.find(item => item.id === note.id)
    if (found) {
      const ref = await request('GET /api/v1/objects/{id}/current', undefined, undefined, { path: { id: note.id } })
      if (ref.entity !== 'note' || ref.revision !== found.revision) throw new Error('笔记在读取时已变化，请重新读取准确版本。')
      return { note: found, ref }
    }
    cursor = page.next_cursor
  } while (cursor)
  throw new Error('笔记已从当前视图删除或不可访问，本机草稿仍保留。')
}
export function NotesPanel({ workspace, selection, initialRefId, openAnchor, onState, onSaved }: { workspace: string; selection: Selection | null; initialRefId?: string; openAnchor: (selection: Selection) => void; onState: (value: { dirty: boolean; safe: boolean }) => void; onSaved: () => void }) {
  const [notes, setNotes] = useState<Note[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [filter, setFilter] = useState(initialRefId ?? '')
  const [editor, setEditor] = useState<NoteEnvelope | null>(null)
  const drafts = useNoteDrafts(workspace)
  const { records, saving: localSaving, error: localError } = drafts
  const recordRef = useRef(records); recordRef.current = records
  const localConflicts = editor ? records[noteKey(editor.candidate)]?.conflicts.map(item => item.text) ?? [] : []
  const [conflict, setConflict] = useState<Conflict | null>(null)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const live = useRef(true)
  const generation = useRef(0)
  const editorRef = useRef<NoteEnvelope | null>(null)
  const stateCallback = useRef(onState); stateCallback.current = onState
  useEffect(() => { stateCallback.current({ dirty: !!editor && noteDirty(editor), safe: !drafts.unsafe }) }, [editor, drafts.unsafe])
  useEffect(() => { live.current = true; return () => { live.current = false; generation.current++ } }, [workspace])
  const persist = drafts.save
  const loadList = async (more = false) => {
    const owner = generation.current
    try {
      const page = await request('GET /api/v1/notes', undefined, undefined, { query: { limit: 20, ...(filter ? { ref_id: filter } : {}), ...(more && cursor ? { cursor } : {}) } })
      if (live.current && owner === generation.current) { setNotes(old => more ? [...old, ...page.items] : page.items); setCursor(page.next_cursor) }
    } catch (reason) { if (live.current && owner === generation.current) setError((reason as Error).message) }
  }
  useEffect(() => { generation.current++; void loadList() }, [workspace, filter])
  const edit = (value: NoteEnvelope, save = true) => { editorRef.current = value; setEditor(value); setStatus(''); if (save) persist(value) }
  const create = () => {
    if (!selection) return
    generation.current++; setConflict(null); setError('')
    edit({ version: 1, base_ref: null, base_note: null, creation_key: crypto.randomUUID(), candidate: { entity: 'note', schema_version: '3.0.0', id: `note_${crypto.randomUUID().replaceAll('-', '')}`, workspace_id: workspace, revision: 1, anchor: structuredClone(selection), anchor_state: 'exact', markdown: '' } })
  }
  const chooseNote = async (note: Note) => {
    setBusy(true); setError(''); const owner = ++generation.current
    try {
      const stored = recordRef.current[noteKey(note)]
      const local = stored ? decodeNoteEnvelope(stored.text, workspace) : null
      setConflict(null)
      if (local && noteDirty(local)) { edit(local, false); setStatus('本机草稿已恢复；正在核对服务端基准。') }
      const remote = await currentNote(note)
      if (!live.current || owner !== generation.current) return
      if (local && noteDirty(local)) {
        if (!local.base_ref || local.base_ref.sha256 !== remote.ref.sha256) setConflict({ base: local.base_note, local: local.candidate, remote: remote.note, remoteRef: remote.ref })
        setStatus('本机草稿已恢复并核对服务端基准。')
      } else edit({ version: 1, base_ref: remote.ref, base_note: remote.note, candidate: remote.note, creation_key: crypto.randomUUID() }, false)

    } catch (reason) { if (live.current && owner === generation.current) setError((reason as Error).message) } finally { if (live.current && owner === generation.current) setBusy(false) }
  }
  const save = async () => {
    const value = editorRef.current
    if (!value || !value.candidate.markdown.trim() || conflict || localConflicts.length || busy) return
    setBusy(true); setError(''); setStatus('保存笔记中…'); const owner = generation.current
    const candidate = { ...value.candidate, revision: value.base_ref ? value.base_ref.revision + 1 : 1 }
    try {
      const ref = value.base_ref
        ? await request('PATCH /api/v1/notes/{id}', candidate, { ...keys(), 'If-Match': `"${value.base_ref.sha256}"` }, { path: { id: candidate.id } })
        : await request('POST /api/v1/notes', candidate, { 'Idempotency-Key': value.creation_key })
      const actual = await currentNote(candidate)
      if (!live.current || owner !== generation.current) return
      if (actual.ref.sha256 !== ref.sha256) throw new Error('保存后笔记又发生变化，请重新读取并比较。')
      const newerText = editorRef.current?.candidate.markdown
      edit({ version: 1, base_ref: ref, base_note: actual.note, candidate: newerText !== value.candidate.markdown ? { ...actual.note, markdown: newerText ?? actual.note.markdown } : actual.note, creation_key: crypto.randomUUID() })
      setStatus('笔记已保存到服务端'); onSaved(); await loadList()
    } catch (reason) {
      if (!live.current || owner !== generation.current) return
      if (reason && typeof reason === 'object' && 'status' in reason && reason.status === 412) {
        try { const remote = await currentNote(candidate); if (live.current && owner === generation.current) setConflict({ base: value.base_note, local: editorRef.current?.candidate ?? candidate, remote: remote.note, remoteRef: remote.ref }) } catch (failure) { setError((failure as Error).message) }
      }
      setStatus('笔记未确认保存'); setError((reason as Error).message)
    } finally { if (live.current && owner === generation.current) setBusy(false) }
  }
  const resolveServer = (keepLocal: boolean) => {
    if (!conflict) return
    edit({ version: 1, base_ref: conflict.remoteRef, base_note: conflict.remote, candidate: keepLocal ? { ...conflict.local, revision: conflict.remote.revision, anchor_state: conflict.remote.anchor_state } : conflict.remote, creation_key: crypto.randomUUID() })
    setConflict(null); setError(''); setStatus(keepLocal ? '已选择本地内容，请明确保存新修订。' : '已采用服务端版本。')
  }
  const resolveLocal = async (text: string) => {
    if (!editor) return
    setBusy(true); const owner = generation.current
    try {
      const value = await drafts.resolve(noteKey(editor.candidate), text)
      if (!live.current || owner !== generation.current) return
      edit(value, false); setConflict(null)
      if (value.base_note) {
        const remote = await currentNote(value.base_note)
        if (live.current && owner === generation.current && value.base_ref?.sha256 !== remote.ref.sha256) setConflict({ base: value.base_note, local: value.candidate, remote: remote.note, remoteRef: remote.ref })
      }
    } catch (reason) { if (live.current && owner === generation.current) setError((reason as Error).message) } finally { if (live.current && owner === generation.current) setBusy(false) }
  }
  const remove = async () => {
    if (!editor?.base_ref) return
    setBusy(true); const owner = generation.current
    try {
      await request('DELETE /api/v1/notes/{id}', undefined, { ...keys(), 'If-Match': `"${editor.base_ref.sha256}"` }, { path: { id: editor.candidate.id } })
      if (!live.current || owner !== generation.current) return
      // Deleting the server object does not authorize discarding local edits.
      if (!noteDirty(editor)) persist({ ...editor, candidate: editor.base_note! })
      editorRef.current = null; setEditor(null); setDeleting(false); setStatus('笔记已从当前视图删除；历史引用保留。'); onSaved(); await loadList()
    } catch (reason) {
      if (live.current && owner === generation.current) {
        if (reason && typeof reason === 'object' && 'status' in reason && reason.status === 412) {
          try { const remote = await currentNote(editor.candidate); if (live.current && owner === generation.current) { setConflict({ base: editor.base_note, local: editor.candidate, remote: remote.note, remoteRef: remote.ref }); setDeleting(false) } } catch (failure) { setError((failure as Error).message) }
        }
        setError(`删除未完成：${(reason as Error).message}`)
      }
    } finally { if (live.current && owner === generation.current) setBusy(false) }
  }
  const recover = (record: DraftRecord) => { try { const value = decodeNoteEnvelope(record.text, workspace); if (value.base_note) void chooseNote(value.base_note); else { setConflict(null); edit(value, false) } } catch (reason) { setError((reason as Error).message) } }
  return <div className="notes-panel"><p>笔记绑定准确内容块、修订与原文范围。它不属于已认证学习证据。</p><button disabled={!selection || busy || localSaving} onClick={create}>用当前选文新建笔记</button>{!selection && <p>先在正文或原始 Markdown 中选取范围，再新建笔记。</p>}<label>笔记范围<select disabled={busy} value={filter ? 'current' : 'all'} onChange={event => setFilter(event.target.value === 'all' ? '' : initialRefId ?? selection?.ref.id ?? '')}><option value="all">工作区全部笔记</option>{(initialRefId || selection) && <option value="current">当前内容块的笔记</option>}</select></label>
    <ul className="note-list">{notes.map(note => <li key={note.id}><button disabled={busy || drafts.unsafe} onClick={() => void chooseNote(note)}>{note.markdown.slice(0, 60)} <small>修订 {note.revision} · {note.anchor_state}</small></button></li>)}</ul>{cursor && <button onClick={() => void loadList(true)}>加载更多笔记</button>}{Object.entries(records).map(([key, record]) => { try { const value = decodeNoteEnvelope(record.text, workspace); return noteDirty(value) && value.candidate.id !== editor?.candidate.id ? <button key={key} disabled={busy} onClick={() => recover(record)}>恢复本机笔记草稿 {value.candidate.id}</button> : null } catch { return <p key={key}>一份本机草稿无法解析，原记录保留。</p> } })}
    {editor && <section className="note-editor"><h3>编辑笔记</h3><p className="note-identity">{editor.candidate.id} · 修订 {editor.base_ref?.revision ?? '尚未创建'}</p><p>锚点：{editor.candidate.anchor.ref.id} · 修订 {editor.candidate.anchor.ref.revision} · {editor.candidate.anchor_state}</p><blockquote>{editor.candidate.anchor.exact_quote}</blockquote><p>Unicode 码点范围 [{editor.candidate.anchor.start_codepoint}, {editor.candidate.anchor.end_codepoint})</p><button onClick={() => openAnchor(editor.candidate.anchor)}>打开笔记的原始修订</button>{selection && editor.base_ref && <button disabled={busy || localSaving || !!conflict || localConflicts.length > 0} onClick={() => edit({ ...editor, candidate: { ...editor.candidate, anchor: structuredClone(selection), anchor_state: 'exact' } })}>将笔记重新绑定当前选文</button>}<label>笔记正文<textarea value={editor.candidate.markdown} disabled={busy || localConflicts.length > 0} onChange={event => edit({ ...editor, candidate: { ...editor.candidate, markdown: event.target.value } })} /></label><div className="note-buttons"><button className="primary-button" disabled={busy || localSaving || !!conflict || localConflicts.length > 0 || !editor.candidate.markdown.trim()} onClick={() => void save()}>保存笔记到服务端</button>{editor.base_ref && <button disabled={busy || localSaving} onClick={() => setDeleting(true)}>删除此笔记</button>}{localError && <button onClick={() => persist(editor)}>重试保存本机草稿</button>}</div>{localSaving ? <p role="status">本机笔记草稿保存中…</p> : noteDirty(editor) && !localError && <p role="status">本机草稿已保留；尚未同步为服务端笔记。</p>}</section>}
    {conflict && <section className="note-conflict" role="status"><h3>笔记版本冲突</h3><DraftConflictPreview base={conflict.base?.markdown ?? null} local={conflict.local.markdown} stored={conflict.remote.markdown} /><details><summary>比较锚点与准确引用</summary>{([{ label: '原基准', note: conflict.base }, { label: '本机候选', note: conflict.local }, { label: '服务端版本', note: conflict.remote }]).map(item => item.note && <div key={item.label}><p>{item.label}：{item.note.anchor.ref.id} · 修订 {item.note.anchor.ref.revision} · {item.note.anchor_state}</p><code>{item.note.anchor.ref.sha256}</code><blockquote>{item.note.anchor.exact_quote}</blockquote></div>)}</details><button onClick={() => resolveServer(true)}>保留本地内容并采用新基准</button><button onClick={() => resolveServer(false)}>采用服务端笔记</button></section>}
    {localConflicts.length > 0 && editor && <section role="status"><h3>本机草稿版本冲突</h3><p>多个窗口的候选均保留，选择后再保存到服务端。</p>{[recordRef.current[noteKey(editor.candidate)]?.text, ...localConflicts].filter((text): text is string => !!text).map((text, index) => <div key={index}><pre>{previewCandidate(text, workspace)}</pre><button disabled={busy} onClick={() => void resolveLocal(text)}>采用本机候选 {index + 1}</button></div>)}</section>}
    {deleting && <section role="alertdialog" aria-label="确认删除笔记"><p>从当前笔记列表软删除；保留历史版本和引用。本机未同步内容仍需自行保留。</p><button disabled={busy} onClick={() => void remove()}>确认软删除笔记</button><button onClick={() => setDeleting(false)}>取消删除</button></section>}
    {error && <p role="alert">{error}</p>}{localError && <p role="alert">{localError}</p>}{status && <p role="status">{status}</p>}
  </div>
}
