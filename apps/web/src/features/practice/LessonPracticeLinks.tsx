import { useEffect, useState } from 'react'
import type { PracticeSetSummary } from '../../../../../packages/contracts/generated/api-types'
import type { ReaderTarget } from '../reader/target'
import { listPracticeSets } from './practiceClient'
import type { PracticeTarget } from './target'
export function LessonPracticeLinks({ target, open }: { target: ReaderTarget; open: (target: PracticeTarget) => void }) {
  const [items, setItems] = useState<PracticeSetSummary[]>([]), [error, setError] = useState(''), [loading, setLoading] = useState(true)
  useEffect(() => { let live = true; void listPracticeSets(target.course, target.lesson).then(value => { if (live) setItems(value) }).catch(reason => { if (live) setError((reason as Error).message) }).finally(() => { if (live) setLoading(false) }); return () => { live = false } }, [JSON.stringify(target)])
  return <>{loading && <p role="status">正在读取本节精确修订的习题…</p>}{error && <p role="alert">{error}</p>}{!loading && !error && !items.length && <p>尚无已审核习题。此小节修订暂无匹配的参考习题集。</p>}<div className="command-list">{items.map(item => <button key={`${item.ref.id}:${item.ref.revision}`} onClick={() => open({ course_ref: target.course, lesson_ref: target.lesson, practice_ref: item.ref })}>{item.title} · {item.question_count} 题 · r{item.ref.revision}</button>)}</div></>
}
