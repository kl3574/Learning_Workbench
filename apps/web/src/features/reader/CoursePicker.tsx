import { useEffect, useState } from 'react'
import { request } from '../../api/client'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import type { PageCourse } from '../../../../../packages/contracts/generated/api-types'
export function CoursePicker({ choose, loadSynthetic }: { choose: (ref: ContentRef) => void; loadSynthetic: () => void }) {
  const [courses, setCourses] = useState<PageCourse['items']>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let live = true; setBusy(true); setCourses([]); setError('')
    void request('GET /api/v1/courses', undefined, undefined, { query: { q: query, limit: 20 } }).then(page => { if (live) { setCourses(page.items); setCursor(page.next_cursor) } }).catch(reason => { if (live) setError((reason as Error).message) }).finally(() => { if (live) setBusy(false) })
    return () => { live = false }
  }, [query])
  const more = async () => {
    if (!cursor) return
    setBusy(true)
    try { const page = await request('GET /api/v1/courses', undefined, undefined, { query: { q: query, cursor, limit: 20 } }); setCourses(old => [...old, ...page.items]); setCursor(page.next_cursor) } catch (reason) { setError((reason as Error).message) } finally { setBusy(false) }
  }
  return <><label>搜索已导入课程<input value={query} onChange={event => setQuery(event.target.value)} /></label>{busy && <p role="status">正在读取课程…</p>}{error && <p role="alert">{error}</p>}<div className="command-list">{courses.map(course => <button key={`${course.ref.id}:${course.ref.revision}`} onClick={() => choose(course.ref)}>{course.title}<small>修订 {course.ref.revision} · {course.lesson_count} 节 · 尚未审校</small></button>)}</div>{!busy && !error && !courses.length && <p>没有匹配的已导入课程。可以关闭窗口后导入自己的材料。</p>}{cursor && <button disabled={busy} onClick={() => void more()}>加载更多课程</button>}<hr /><p className="muted">合成示例仅用于布局验收，不创建正式教材或学习记录。</p><button onClick={loadSynthetic}>加载合成示例课程</button></>
}
