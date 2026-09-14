import { useEffect, useRef, useState } from 'react'
import { request } from '../../api/client'
import { readLocal, writeLocal, removeLocal } from '../../workbench/uiCache'
import { readPracticeTarget } from './practiceClient'
import type { PracticeTarget } from './target'
import type { ReaderTarget } from '../reader/target'
export function PracticePreview({ workspace, target, open, reader, loaded }: { workspace: string; target: PracticeTarget; open: (target: PracticeTarget, pinned?: boolean) => void; reader: (target: ReaderTarget) => void; loaded: (title: string, resolved: boolean) => void }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof readPracticeTarget>> | null>(null)
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const active = useRef(true), generation = useRef(0)
  const callbacks = useRef({ loaded, open }); callbacks.current = { loaded, open }
  const [retry, setRetry] = useState(0)
  useEffect(() => { active.current = true; const owner = ++generation.current; setData(null); setError(''); callbacks.current.loaded('', false); void readPracticeTarget(target).then(value => { if (active.current && owner === generation.current) { setData(value); callbacks.current.loaded(value.summary.title, true) } }).catch(reason => { if (active.current && owner === generation.current) setError((reason as Error).message) }); return () => { active.current = false; ++generation.current } }, [workspace, JSON.stringify(target), retry])
  const start = async () => {
    if (!data || busy) return
    setBusy(true); setError(''); const owner = generation.current
    const key = `learning-workbench.${workspace}.practice-create.${target.practice_ref.id}.${target.practice_ref.revision}.${target.practice_ref.sha256}`
    let idempotency = readLocal(key)
    if (!idempotency || !/^[a-f0-9-]{36}$/.test(idempotency)) { idempotency = crypto.randomUUID(); if (!writeLocal(key, idempotency)) { setError('无法安全保留创建命令，请恢复本机缓存后重试；尚未创建会话。'); setBusy(false); return } }
    try {
      const session = await request('POST /api/v1/practice/sessions', { practice_ref: target.practice_ref }, { 'Idempotency-Key': idempotency })
      if (active.current && owner === generation.current) { callbacks.current.open({ ...target, session_id: session.id }, true); removeLocal(key) }
    } catch (reason) { if (active.current && owner === generation.current) setError(`开始练习未确认：${(reason as Error).message}。保留同一创建命令，重试不会另建重复会话。`) }
    finally { if (active.current && owner === generation.current) setBusy(false) }
  }
  return <div className="reader-scroll"><article className="reader-content practice-preview"><div className="eyebrow">习题 · 自主练习</div><h1>{data?.summary.title ?? '正在解析精确习题集'}</h1>{error && <p role="alert">{error}</p>}{!data && <button onClick={() => setRetry(value => value + 1)}>重试精确习题引用</button>}{data && <><p className="breadcrumbs">{data.course.title} › {data.lesson.title}</p><p>{data.summary.question_count} 题 · 题集修订 {target.practice_ref.revision}</p><p>明确开始后才创建作答会话。练习包含尚需审查的导入内容；题面与参考解答不会在此自动取得审核批准。</p><p>本阶段提交保留作答并标记待审查，尚不评分。练习与提示、参考解答暴露都不作为独立测试证据。</p><div className="reader-actions"><button className="primary-button" disabled={busy} onClick={() => void start()}>{busy ? '正在创建练习会话…' : '开始此练习'}</button><button onClick={() => reader({ course: target.course_ref, lesson: target.lesson_ref })}>返回对应教材</button></div><details><summary>精确题集引用</summary><code>{target.practice_ref.id} · r{target.practice_ref.revision}<br />SHA-256 {target.practice_ref.sha256}</code></details></>}</article></div>
}
