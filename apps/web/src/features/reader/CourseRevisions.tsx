import { useEffect, useRef, useState } from 'react'
import { request } from '../../api/client'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import type { RevisionSummary } from '../../../../../packages/contracts/generated/api-types'
export function CourseRevisions({ course, choose }: { course: ContentRef; choose: (ref: ContentRef) => void }) {
  const [items, setItems] = useState<RevisionSummary[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const epoch = useRef(0)
  const load = async (next?: string) => {
    const generation = ++epoch.current; setBusy(true); setError('')
    try {
      const page = await request('GET /api/v1/objects/{id}/revisions', undefined, undefined, { path: { id: course.id }, query: { limit: 20, ...(next ? { cursor: next } : {}) } })
      if (generation === epoch.current) { setItems(old => next ? [...old, ...page.items] : page.items); setCursor(page.next_cursor) }
    } catch (reason) { if (generation === epoch.current) setError((reason as Error).message) } finally { if (generation === epoch.current) setBusy(false) }
  }
  useEffect(() => { void load(); return () => { epoch.current++ } }, [course.id])
  return <><p>选择准确教材修订。已打开的旧标签、选文和笔记保持原来的引用。</p><div className="command-list">{items.map(item => <button key={item.ref.sha256} disabled={item.ref.entity !== 'course'} onClick={() => choose(item.ref)}>教材修订 {item.ref.revision}{item.ref.sha256 === course.sha256 ? ' · 当前所选' : ''}<small>{item.lifecycle === 'archived' ? '已归档' : '可读取'} · 尚未审校</small></button>)}</div>{busy && <p role="status">正在读取教材修订…</p>}{cursor && <button disabled={busy} onClick={() => void load(cursor)}>加载更多修订</button>}{error && <p role="alert">{error}</p>}</>
}
