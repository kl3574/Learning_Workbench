import { lazy, Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { fixture, findLesson, type SyntheticLesson } from '../features/fixture'
const Markdown = lazy(() => import('../shared/Markdown').then(module => ({ default: module.Markdown })))
import { readReaderView, saveReaderView } from './uiCache'
import type { Session, ViewContext } from './model'
export function Reader({ session, loaded, onLoad, onOpen, onSelect, onScroll, onAux, workspaceId }: { session: Session; workspaceId: string | null; loaded: boolean; onLoad: () => void; onOpen: (lesson: SyntheticLesson) => void; onSelect: (selection: ViewContext['selection']) => void; onScroll: (offset: number) => void; onAux: (name: string) => void }) {
  const active = session.tabs.find(tab => tab.id === session.active_tab_id)
  const lesson = findLesson(active?.context.active_ref)
  const reader = useRef<HTMLDivElement>(null)
  const [cacheWarning, setCacheWarning] = useState(false)
  const [selectionWarning, setSelectionWarning] = useState('')
  const selectionSink = useRef(onSelect); selectionSink.current = onSelect
  const viewState = useRef({ workspace: workspaceId, tabId: active?.id, value: readReaderView(workspaceId, active?.id ?? 'none') })
  if (viewState.current.tabId !== active?.id || viewState.current.workspace !== workspaceId) viewState.current = { workspace: workspaceId, tabId: active?.id, value: readReaderView(workspaceId, active?.id ?? 'none') }
  const restoration = useRef({ id: active?.id, offset: active?.scroll_offset ?? 0, ready: false, permitFocus: !document.activeElement?.closest('dialog') })
  if (restoration.current.id !== active?.id) restoration.current = { id: active?.id, offset: active?.scroll_offset ?? 0, ready: false, permitFocus: !document.activeElement?.closest('dialog') }
  const restore = useCallback(() => {
    const element = reader.current
    if (!element) return
    for (const detail of element.querySelectorAll<HTMLDetailsElement>('details[data-view-key]')) detail.open = viewState.current.value.expandedDetails.includes(detail.dataset.viewKey ?? '')
    element.scrollTop = restoration.current.offset
    const focusKey = viewState.current.value.focusKey
    if (focusKey && restoration.current.permitFocus && !document.querySelector('dialog[open]')) element.querySelector<HTMLElement>(`[data-focus-key="${CSS.escape(focusKey)}"]`)?.focus({ preventScroll: true })
    restoration.current.ready = true
  }, [active?.id, workspaceId])
  const saveView = () => { if (active && !saveReaderView(workspaceId, active.id, viewState.current.value)) setCacheWarning(true) }
  useEffect(() => {
    const element = reader.current
    const onToggle = (event: Event) => {
      if (!active || !restoration.current.ready || !(event.target instanceof HTMLDetailsElement) || !event.target.dataset.viewKey) return
      viewState.current.value.expandedDetails = Array.from(element?.querySelectorAll<HTMLDetailsElement>('details[data-view-key][open]') ?? []).map(detail => detail.dataset.viewKey!)
      if (!saveReaderView(workspaceId, active.id, viewState.current.value)) setCacheWarning(true)
    }
    element?.addEventListener('toggle', onToggle, true)
    return () => element?.removeEventListener('toggle', onToggle, true)
  }, [active?.id, workspaceId])


  useEffect(() => {
    const updateSelection = () => {
      const selected = window.getSelection(); const element = reader.current
      if (!active || !lesson || !selected || selected.isCollapsed || !element?.contains(selected.anchorNode) || !element.contains(selected.focusNode)) return
      const quote = selected.toString().slice(0, 12000); const source = lesson.body; const start = source.indexOf(quote)
      if (start < 0 || source.indexOf(quote, start + 1) >= 0) {
        setSelectionWarning(start < 0 ? '选文无法唯一对应原始 Markdown，未附加上下文。' : '选文在原文中有多个匹配，未附加上下文；请选择更独特的片段。')
        selectionSink.current(null); return
      }
      setSelectionWarning('')
      selectionSink.current({ ref: active.context.active_ref, exact_quote: quote, prefix: source.slice(Math.max(0, start - 40), start), suffix: source.slice(start + quote.length, start + quote.length + 40), start_codepoint: Array.from(source.slice(0, start)).length, end_codepoint: Array.from(source.slice(0, start)).length + Array.from(quote).length })
    }
    document.addEventListener('selectionchange', updateSelection)
    reader.current?.addEventListener('keyup', updateSelection)
    const element = reader.current
    return () => { document.removeEventListener('selectionchange', updateSelection); element?.removeEventListener('keyup', updateSelection) }
  }, [active?.id, lesson?.body])
  const navigation = session.navigation
  return <div className="reader-scroll" ref={reader} onScroll={event => { if (active && restoration.current.ready) onScroll(event.currentTarget.scrollTop) }}>
    {lesson && active ? <article className="reader-content" onFocusCapture={event => { const key = (event.target as HTMLElement).dataset.focusKey; if (key && restoration.current.ready) { viewState.current.value.focusKey = key; saveView() } }}>{selectionWarning && <p className="stale-notice" role="status">{selectionWarning}</p>}{cacheWarning && <p className="stale-notice" role="status">当前标签的展开或焦点状态尚未保存：浏览器缓存不可用。</p>}<div className="breadcrumbs">合成示例课程 <span>›</span> 第 {lesson.chapter} 章 <span>›</span> {lesson.chapter}.{lesson.number}</div><div className="synthetic-notice">合成示例 · 仅用于界面验收，不是正式教材或学习证据</div><h1>{lesson.title}</h1><div className="reader-meta">修订 {active.context.active_ref.revision} <span>·</span> 未诊断 <span>·</span> {lesson.sampleState === 'stale' ? '过期引用展示 · 需要复核' : lesson.sampleState === 'read' ? '已读展示（合成）' : '未读'}</div>{lesson.sampleState === 'stale' && <aside className="stale-notice">此处展示过期引用状态；当前引用与草稿保留，未自动迁移到其他修订。</aside>}<Suspense fallback={<p role="status">正在载入本地数学排版…</p>}><Markdown>{lesson.body}</Markdown><ReaderReady key={active.id} onReady={restore} /></Suspense><div className="reader-pagination"><button data-focus-key="reader-previous" disabled={fixture.lessons.indexOf(lesson) === 0} onClick={() => onOpen(fixture.lessons[fixture.lessons.indexOf(lesson) - 1])}>← 上一节</button><button data-focus-key="reader-next" disabled={fixture.lessons.indexOf(lesson) === fixture.lessons.length - 1} onClick={() => onOpen(fixture.lessons[fixture.lessons.indexOf(lesson) + 1])}>下一节 →</button></div></article> : active ? <div className="empty-content"><div className="eyebrow">引用待解析</div><h1>暂时无法打开这个对象</h1><p>已保留对象 {active.context.active_ref.id} 的修订 {active.context.active_ref.revision} 和草稿。当前阶段无法读取它的正式内容。</p></div> : <div className="empty-content"><div className="eyebrow">知径 / {navigation === 'route' ? '学习路线' : navigation === 'textbook' ? '教材' : navigation === 'practice' ? '习题' : '测试题'}</div><h1>{navigation === 'route' ? loaded ? '把目标连成一条学习路线' : '从一个学习目标开始' : navigation === 'textbook' ? loaded ? '选择一节，开始阅读' : '你的教材，将从这里展开' : navigation === 'practice' ? '尚无已审核习题' : '尚无已发布测试'}</h1><p>{navigation === 'route' ? '路线帮助你安排阅读、练习和独立测试。当前还没有正式路线，也没有学习证据。' : navigation === 'textbook' ? '教材包含定义、推导与例题；内容会保留来源与准确修订。' : navigation === 'practice' ? '习题与解答会在审核后提供。练习参与和独立测试证据分别记录。' : '独立测试与辅助练习分开记录。当前没有可以开始的测试。'}</p><div className="empty-actions">{!loaded && <button className="primary-button" onClick={onLoad}>浏览合成示例课程 <span aria-hidden="true">→</span></button>}{loaded && (navigation === 'route' || navigation === 'textbook') && <button className="primary-button" onClick={() => onOpen(fixture.lessons[1])}>打开示例小节 →</button>}<button onClick={() => onAux('导入')}>查看导入能力</button></div><div className="empty-footnote"><strong>你的资料保持在本机</strong><p>导入与正式路线编辑尚待后续阶段实现。合成示例只用于体验工作台布局，不会创建成绩或阅读记录。</p></div></div>}
  </div>
}

function ReaderReady({ onReady }: { onReady: () => void }) { useLayoutEffect(onReady, [onReady]); return null }
