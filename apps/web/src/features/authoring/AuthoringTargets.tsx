import { useEffect, useRef, useState } from 'react'
import type { ContentRef, CourseSummary } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { readCourse } from '../reader/contentClient'
import { refKey, sameRef } from '../reader/target'

export type GroupTargets = { concepts: ContentRef[]; lesson: ContentRef | null }
type Choice = { ref: ContentRef; title: string }
export function AuthoringTargets({ value, change, practice, busy, denied }: { value: GroupTargets; change: (value: GroupTargets) => void; practice: boolean; busy: boolean; denied: (reason: unknown) => void }) {
  const [courses, setCourses] = useState<CourseSummary[]>([]), [cursor, setCursor] = useState<string | null>(null)
  const [choices, setChoices] = useState<Choice[]>([]), [pending, setPending] = useState(false), [error, setError] = useState('')
  const live = useRef(true), sequence = useRef(0)
  useEffect(() => { live.current = true; return () => { live.current = false; ++sequence.current } }, [])
  const load = async (course?: ContentRef, more = false) => {
    if (pending || busy) return
    const generation = ++sequence.current; setPending(true); setError(''); if (course) setChoices([])
    try {
      if (course) {
        const [metadata, outline] = await Promise.all([readCourse(course), request('GET /api/v1/courses/{id}/outline', undefined, undefined, { path: { id: course.id }, query: { revision: course.revision } })])
        if (!sameRef(outline.course_ref, course)) throw new Error('课程目录引用不一致。')
        const lessons = outline.sections.flatMap(section => section.lessons)
        if (lessons.some(lesson => !metadata.lesson_refs.some(ref => sameRef(ref, lesson.ref)))) throw new Error('小节不属于这份课程。')
        const next = [...lessons.map(lesson => ({ ref: lesson.ref, title: lesson.title })), ...(metadata.concept_refs ?? []).map(ref => ({ ref, title: ref.id }))]
        if (next.some(item => !['lesson', 'concept'].includes(item.ref.entity)) || new Set(next.map(item => refKey(item.ref))).size !== next.length) throw new Error('目标目录存在重复或无效引用。')
        if (live.current && generation === sequence.current) setChoices(next)
      } else {
        const page = await request('GET /api/v1/courses', undefined, undefined, { query: { limit: 20, ...(more && cursor ? { cursor } : {}) } })
        const next = more ? [...courses, ...page.items] : page.items
        if (new Set(next.map(item => refKey(item.ref))).size !== next.length || more && page.next_cursor === cursor) throw new Error('课程分页重复。')
        if (live.current && generation === sequence.current) { setCourses(next); setCursor(page.next_cursor) }
      }
    } catch (reason) { if (live.current && generation === sequence.current) { setError('本次目录未读取成功；已选准确引用保留。'); denied(reason) } }
    finally { if (live.current && generation === sequence.current) setPending(false) }
  }
  const selectConcept = (ref: ContentRef) => {
    if (value.concepts.some(item => item.id === ref.id && item.revision === ref.revision) || value.concepts.length >= 32) return
    change({ ...value, concepts: [...value.concepts, ref] })
  }
  return <section aria-label="明确选择已有目标"><h4>已有概念与小节</h4><p>目标只采用你选择的准确修订。目录不会自动加入教材正文或先修材料；题组至少选择一个已有概念。</p>
    <button disabled={busy || pending} onClick={() => void load()}>读取课程目录以选择目标</button>
    {courses.map(course => <button key={refKey(course.ref)} disabled={busy || pending} onClick={() => void load(course.ref)}>{course.title} · r{course.ref.revision} · 选择目标</button>)}
    {cursor && <button disabled={busy || pending} onClick={() => void load(undefined, true)}>继续读取目标课程</button>}
    {pending && <p role="status">正在读取目标目录…</p>}{error && <p role="alert">{error}</p>}
    {choices.filter(item => item.ref.entity === 'concept' || practice).map(item => <button key={refKey(item.ref)} disabled={busy || pending || item.ref.entity === 'concept' && (value.concepts.length >= 32 || value.concepts.some(ref => ref.id === item.ref.id && ref.revision === item.ref.revision))} onClick={() => item.ref.entity === 'concept' ? selectConcept(item.ref) : change({ ...value, lesson: item.ref })}>{item.ref.entity === 'concept' ? '加入概念' : '选择所属小节'}：{item.title} · r{item.ref.revision}</button>)}
    <p>已选概念 {value.concepts.length} / 32</p>{value.concepts.map(ref => <p key={refKey(ref)}>{ref.id} · r{ref.revision} <button disabled={busy} onClick={() => change({ ...value, concepts: value.concepts.filter(item => !sameRef(item, ref)) })}>移除概念 {ref.id} r{ref.revision}</button></p>)}
    {practice && <p>习题集所属小节：{value.lesson ? `${value.lesson.id} · r${value.lesson.revision}` : '尚未选择'}{value.lesson && <button disabled={busy} onClick={() => change({ ...value, lesson: null })}>清除所属小节</button>}</p>}
  </section>
}
