import { useEffect, useRef, useState } from 'react'
import type { QuestionReviewMaterials } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration } from '../../api/client'
import { readCourse, readLesson, readBlock } from '../reader/contentClient'
import { readerHref, refKey, sameRef, type ReaderTarget } from '../reader/target'
export function ReviewMaterialLinks({ group, allowed, open }: { group: QuestionReviewMaterials | null; allowed: boolean; open?: (target: ReaderTarget, pinned?: boolean) => void }) {
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const owner = group ? `${refKey(group.question_ref)}:${getSessionGeneration()}:${allowed}` : ''
  const live = useRef(owner); live.current = owner
  useEffect(() => { live.current = owner; setError(''); setBusy(false); return () => { live.current = '' } }, [owner])
  const navigate = async (item: QuestionReviewMaterials['materials'][number]) => {
    const access = getSessionGeneration(), identity = live.current
    setBusy(true); setError('')
    try {
      const course = await readCourse(item.course_ref), lesson = await readLesson(item.lesson_ref)
      if (!course.lesson_refs.some(ref => sameRef(ref, item.lesson_ref)) || !lesson.block_refs.some(ref => sameRef(ref, item.block_ref))) throw new Error('教材父链不匹配，未替换为当前版本。')
      const block = await readBlock(item.block_ref)
      if (identity !== live.current || access !== getSessionGeneration()) return
      open?.({ course: item.course_ref, lesson: item.lesson_ref, block: item.block_ref, view: block.block.kind === 'worked_example' ? 'worked_example' : 'lesson' }, true)
    } catch (reason) { if (identity === live.current && access === getSessionGeneration()) setError(`对应教材尚不可打开：${reason instanceof Error ? reason.message : '核验失败'}`) } finally { if (identity === live.current) setBusy(false) }
  }
  return <section className="review-materials" aria-label="本题对应教材"><h2>对应教材</h2><p>仅列出本题精确概念与冻结课程中已核验的内容块；链接不表示推荐、内容审批或掌握结论。</p>{!allowed ? <p>当前访问策略尚未允许打开教材，请等待策略回读或结束正在进行的独立测试。</p> : !group?.materials.length ? <p>本题暂无可核验的对应教材定位，不根据标题或相同 ID 猜测。</p> : <ul>{group.materials.map(item => <li key={`${refKey(item.course_ref)}:${refKey(item.lesson_ref)}:${refKey(item.block_ref)}`}><button disabled={busy || !open} onClick={() => void navigate(item)}>{item.title} · r{item.block_ref.revision}</button><details><summary>核对对应教材定位</summary><code>课程 {item.course_ref.id} · r{item.course_ref.revision}<br />小节 {item.lesson_ref.id} · r{item.lesson_ref.revision}<br />内容块 {item.block_ref.id} · r{item.block_ref.revision}<br />SHA-256 {item.block_ref.sha256}</code><p><a href={readerHref({ course: item.course_ref, lesson: item.lesson_ref, block: item.block_ref })} onClick={event => { event.preventDefault(); if (!busy && open) void navigate(item) }}>打开此精确教材链接</a></p></details></li>)}</ul>}{busy && <p role="status">正在核验教材父链、修订与正文哈希…</p>}{error && <p role="alert">{error}</p>}</section>
}
