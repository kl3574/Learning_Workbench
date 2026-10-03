import { lazy, Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { request } from '../../api/client'
import type { Course, Lesson, Selection } from '../../../../../packages/contracts/generated/types'
import type { LearningProgress } from '../../../../../packages/contracts/generated/api-types'
import type { Session } from '../../workbench/model'
import { readReaderView, saveReaderView, saveLastReading } from '../../workbench/uiCache'
import { contextTarget, sameRef, type ReaderTarget } from './target'
import { readBlock, readCourse, readLesson, readProgress, type LoadedBlock } from './contentClient'
import { selectionFromDOM, selectionFromSource } from './selection'
import { SourcePanel } from './SourcePanel'
import './reader.css'
const Markdown = lazy(() => import('../../shared/Markdown').then(value => ({ default: value.Markdown })))
type DocumentData = { targetKey: string; course: Course; lesson: Lesson; blocks: LoadedBlock[]; stale: boolean }
export function ReaderDocument({ session, workspace, onOpen, onScroll, onSelect, onNote, onLoaded, progressVersion, progressChanged, onAux, loadSynthetic, practice }: { session: Session; workspace: string | null; onOpen: (target: ReaderTarget, pinned?: boolean) => void; onScroll: (offset: number) => void; onSelect: (value: Selection | null) => void; onNote: (selection: Selection) => void; onLoaded: (title: string, resolved: boolean) => void; progressVersion: number; progressChanged: () => void; onAux: (name: string) => void; loadSynthetic: () => void; practice: (target: ReaderTarget) => void }) {
  const active = session.tabs.find(tab => tab.id === session.active_tab_id)
  const target = active ? contextTarget(active.context, session.course_ref) : null
  const targetKey = JSON.stringify(target)
  const owner = useRef({ key: '', generation: 0 })
  if (owner.current.key !== `${workspace}:${targetKey}`) owner.current = { key: `${workspace}:${targetKey}`, generation: owner.current.generation + 1 }
  useEffect(() => () => { owner.current.generation++ }, [])
  const [storedData, setData] = useState<DocumentData | null>(null)
  const data = storedData?.targetKey === targetKey ? storedData : null
  const [progress, setProgress] = useState<LearningProgress | null>(null)
  const [error, setError] = useState('')
  const [warning, setWarning] = useState('')
  const [busy, setBusy] = useState(false)
  const [version, setVersion] = useState(0)
  const scroll = useRef<HTMLDivElement>(null)
  const view = useRef(readReaderView(workspace, active?.id ?? 'none'))
  const restoration = useRef({ key: '', offset: 0, ready: false, permitFocus: false })
  const callbacks = useRef({ onSelect, onLoaded }); callbacks.current = { onSelect, onLoaded }
  if (restoration.current.key !== `${workspace}:${active?.id}`) {
    restoration.current = { key: `${workspace}:${active?.id}`, offset: active?.scroll_offset ?? 0, ready: false, permitFocus: !document.querySelector('dialog[open]') }
    view.current = readReaderView(workspace, active?.id ?? 'none')
  }
  useEffect(() => {
    let live = true; setData(null); setProgress(null); setError(''); setWarning(''); setBusy(false); callbacks.current.onLoaded('', false)
    restoration.current.ready = false
    if (!workspace || !active || !target) return
    void (async () => {
      const [course, lesson, current, readings] = await Promise.all([readCourse(target.course), readLesson(target.lesson), request('GET /api/v1/objects/{id}/current', undefined, undefined, { path: { id: active.context.active_ref.id } }), readProgress(target.course.id)])
      if (!course.lesson_refs.some(ref => sameRef(ref, target.lesson)) || (target.block && !lesson.block_refs.some(ref => sameRef(ref, target.block)))) throw new Error('此精确课程、章节和内容块的所属关系不匹配；未猜测另一条阅读路径。')
      const blocks: LoadedBlock[] = []
      for (const ref of lesson.block_refs) { if (!live) return; blocks.push(await readBlock(ref)) }
      if (!live) return
      if (target.view === 'worked_example' && blocks.find(block => sameRef(block.block_ref, target.block))?.block.kind !== 'worked_example') throw new Error('此链接声称的例题类型与真实内容块不符；原始引用保留。')
      setData({ targetKey, course, lesson, blocks, stale: !sameRef(current, active.context.active_ref) }); setProgress(readings)
      callbacks.current.onLoaded(target.block ? blocks.find(block => sameRef(block.block_ref, target.block))?.block.title ?? lesson.title : lesson.title, true)
      if (!saveLastReading(workspace, target.course.id, 'textbook', active.context.active_ref)) setWarning('最后阅读对象仅保留在本页：浏览器缓存不可用。')
    })().catch(reason => { if (live) setError((reason as Error).message) })
    return () => { live = false }
  }, [targetKey, workspace, version, active?.id])
  useEffect(() => {
    if (!target || !progressVersion) return
    let live = true; setBusy(true)
    const generation = owner.current.generation
    void readProgress(target.course.id).then(value => { if (live && generation === owner.current.generation) setProgress(value) }).catch(reason => { if (live && generation === owner.current.generation) setWarning(`阅读记录刷新失败：${(reason as Error).message}`) }).finally(() => { if (live && generation === owner.current.generation) setBusy(false) })
    return () => { live = false }
  }, [progressVersion, targetKey])
  const restore = useCallback(() => {
    const element = scroll.current
    if (!element || !active) return
    for (const details of element.querySelectorAll<HTMLDetailsElement>('details[data-view-key]')) details.open = view.current.expandedDetails.includes(details.dataset.viewKey!)
    if (restoration.current.offset > 0 || view.current.positionKnown) element.scrollTop = restoration.current.offset
    else if (target?.block) element.querySelector(`#block-${CSS.escape(target.block.id)}-r${target.block.revision}`)?.scrollIntoView({ block: 'start' })
    if (view.current.focusKey && restoration.current.permitFocus && !document.querySelector('dialog[open]')) element.querySelector<HTMLElement>(`[data-focus-key="${CSS.escape(view.current.focusKey)}"]`)?.focus({ preventScroll: true })
    restoration.current.ready = true
    view.current.positionKnown = true
    if (!saveReaderView(workspace, active.id, view.current)) setWarning('首次定位状态仅保留在本页：浏览器缓存不可用。')
  }, [targetKey, active?.id])
  const saveView = () => { if (active && !saveReaderView(workspace, active.id, view.current)) setWarning('展开或焦点状态未能保存：浏览器缓存不可用。') }
  useEffect(() => {
    const element = scroll.current
    const toggle = (event: Event) => {
      if (!restoration.current.ready || !(event.target instanceof HTMLDetailsElement) || !event.target.dataset.viewKey) return
      view.current.expandedDetails = Array.from(element?.querySelectorAll<HTMLDetailsElement>('details[data-view-key][open]') ?? []).map(detail => detail.dataset.viewKey!)
      if (active && !saveReaderView(workspace, active.id, view.current)) setWarning('展开状态未能保存。')
    }
    element?.addEventListener('toggle', toggle, true)
    return () => element?.removeEventListener('toggle', toggle, true)
  }, [active?.id, workspace])
  useEffect(() => {
    const capture = () => {
      const selection = window.getSelection()
      if (!data || !selection || selection.isCollapsed || !scroll.current?.contains(selection.anchorNode)) return
      const element = selection.anchorNode instanceof Element ? selection.anchorNode : selection.anchorNode?.parentElement
      const root = element?.closest<HTMLElement>('[data-reader-block]')
      const block = data.blocks.find(value => value.block.id === root?.dataset.readerBlock)
      if (!root || !block) return
      const result = selectionFromDOM(root, selection, block.block_ref, block.body)
      if (result.kind === 'selected') { callbacks.current.onSelect(result.selection); setWarning('') }
      else if (result.kind === 'rejected') { callbacks.current.onSelect(null); setWarning(result.message) }
    }
    document.addEventListener('selectionchange', capture)
    return () => document.removeEventListener('selectionchange', capture)
  }, [data])
  const action = async (kind: 'read_marked' | 'bookmark_set', value: boolean) => {
    if (!progress || !target || !active) return
    setBusy(true); setWarning('')
    const generation = owner.current.generation
    try {
      await request('POST /api/v1/learning/actions', { kind, ref: kind === 'read_marked' ? target.lesson : active.context.active_ref, expected_revision: progress.revision, value }, { 'Idempotency-Key': crypto.randomUUID() })
      const updated = await readProgress(target.course.id)
      if (generation === owner.current.generation) { setProgress(updated); setWarning('服务端已保存阅读操作。'); progressChanged() }
    } catch (reason) {
      if (generation !== owner.current.generation) return
      if (reason && typeof reason === 'object' && 'status' in reason && reason.status === 412) {
        try { const latest = await readProgress(target.course.id); if (generation === owner.current.generation) { setProgress(latest); setWarning('阅读记录基准已变化，已读取最新状态。请核对后再次明确提交；没有自动重放操作。') } } catch (failure) { if (generation === owner.current.generation) setWarning(`无法读取最新阅读记录：${(failure as Error).message}。`) }
      } else setWarning(`阅读操作未确认保存：${(reason as Error).message}。`)
    } finally { if (generation === owner.current.generation) setBusy(false) }
  }
  const read = !!target && !!progress?.readings.some(item => sameRef(item.ref, target.lesson) && item.read)
  const bookmarked = !!active && !!progress?.bookmarks.some(item => sameRef(item.ref, active.context.active_ref) && item.value)
  const position = data?.course.lesson_refs.findIndex(ref => target && sameRef(ref, target.lesson)) ?? -1
  return <div className="reader-scroll" ref={scroll} onScroll={event => { if (restoration.current.ready) { restoration.current.offset = event.currentTarget.scrollTop; onScroll(event.currentTarget.scrollTop) } }}>
    {!active ? <div className="empty-content"><div className="eyebrow">知径 / {session.navigation === 'route' ? '学习路线' : '教材'}</div><h1>{session.navigation === 'route' ? '从一个学习目标开始' : '选择一节，开始阅读'}</h1><p>从课程切换中选择已导入教材，或导入自己的材料。浏览正文不会自动记为已读。</p><div className="empty-actions"><button className="primary-button" onClick={() => onAux('课程切换')}>选择已导入课程</button><button onClick={() => onAux('导入')}>导入资料</button><button onClick={loadSynthetic}>浏览合成示例课程 →</button></div></div> : !target ? <div className="empty-content"><h1>阅读引用待解析</h1><p>此标签缺少精确课程或章节所属关系，原始引用与草稿仍保留。</p></div> : error ? <div className="empty-content" role="alert"><h1>暂时无法打开这个对象</h1><p>{error}</p><p>{active.context.active_ref.id} · 修订 {active.context.active_ref.revision}</p><button onClick={() => setVersion(value => value + 1)}>重试读取准确修订</button></div> : !data ? <p role="status" className="empty-content">正在读取准确修订与正文…</p> : <article className="reader-content real-reader" onFocusCapture={event => { const key = (event.target as HTMLElement).dataset.focusKey; if (key && restoration.current.ready) { view.current.focusKey = key; saveView() } }}>
      <div className="breadcrumbs">{data.course.title} › {data.course.sections?.find(section => section.lesson_ids.includes(data.lesson.id))?.title ?? '课程'} › {data.lesson.title}</div><h1>{data.lesson.title}</h1><div className="reader-meta">教材修订 {target.course.revision} · 小节修订 {target.lesson.revision} · 尚未审校 · 未诊断</div>{data.stale && <p className="stale-notice">正在阅读旧修订。旧正文、选文与笔记引用保留；未自动改为当前版本。</p>}
      <div className="reader-actions"><button disabled={busy || !progress} onClick={() => void action('read_marked', !read)}>{read ? '撤销本节已读标记' : '明确标记本节已读'}</button><button disabled={busy || !progress} onClick={() => void action('bookmark_set', !bookmarked)}>{bookmarked ? '移除此对象书签' : '为此对象添加书签'}</button><button disabled={!active.context.selection} onClick={() => active.context.selection && onNote(active.context.selection)}>为当前选文记笔记</button><button onClick={() => onAux('笔记')}>查看笔记</button><button onClick={() => practice(target)}>本节习题</button></div>{warning && <p className="stale-notice" role="status">{warning}</p>}
      <Suspense fallback={<p role="status">正在加载本地数学排版…</p>}>{data.blocks.map(block => <section className={`reader-block block-${block.block.kind}`} id={`block-${block.block.id}-r${block.block.revision}`} key={block.block.id} data-block-ref={JSON.stringify(block.block_ref)}><h2>{block.block.kind === 'worked_example' ? '例题 · ' : ''}{block.block.title}</h2><div className="reader-markdown" data-reader-block={block.block.id}><Markdown sourceKey={`${block.block.id}-r${block.block.revision}`}>{block.body}</Markdown></div><details data-view-key={`original-${block.block.id}`} className="reader-original"><summary data-focus-key={`original-${block.block.id}`}>原始 Markdown 与精确选文</summary><p>这里显示服务端保存的原文。渲染文本或公式无法对应时，可以在原文中选择范围；不猜测偏移。</p><textarea readOnly aria-label={`原始 Markdown：${block.block.title}`} value={block.body} onSelect={event => { const element = event.currentTarget; const result = selectionFromSource(block.block_ref, block.body, element.selectionStart, element.selectionEnd); if (result.kind === 'selected') { onSelect(result.selection); setWarning('已从原始 Markdown 建立准确选文。') } else if (result.kind === 'rejected') setWarning(result.message) }} /></details><SourcePanel value={block} refresh={() => setVersion(value => value + 1)} /></section>)}<ReaderReady onReady={restore} /></Suspense>
      <div className="reader-pagination"><button data-focus-key="reader-previous" disabled={position <= 0} onClick={() => onOpen({ course: target.course, lesson: data.course.lesson_refs[position - 1] })}>← 上一节</button><button data-focus-key="reader-next" disabled={position < 0 || position >= data.course.lesson_refs.length - 1} onClick={() => onOpen({ course: target.course, lesson: data.course.lesson_refs[position + 1] })}>下一节 →</button></div>
    </article>}
  </div>
}
function ReaderReady({ onReady }: { onReady: () => void }) { useLayoutEffect(onReady, [onReady]); return null }
