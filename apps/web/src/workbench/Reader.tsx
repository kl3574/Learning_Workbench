import { lazy, Suspense, useEffect, useRef } from 'react'
import { fixture, findLesson, type SyntheticLesson } from '../features/fixture'
const Markdown = lazy(() => import('../shared/Markdown').then(module => ({ default: module.Markdown })))
import type { Session, ViewContext } from './model'
export function Reader({ session, loaded, onLoad, onOpen, onSelect, onScroll, onAux }: { session: Session; loaded: boolean; onLoad: () => void; onOpen: (lesson: SyntheticLesson) => void; onSelect: (selection: ViewContext['selection']) => void; onScroll: (offset: number) => void; onAux: (name: string) => void }) {
  const active = session.tabs.find(tab => tab.id === session.active_tab_id)
  const lesson = findLesson(active?.context.active_ref.id)
  const reader = useRef<HTMLDivElement>(null)
  useEffect(() => { if (reader.current) reader.current.scrollTop = active?.scroll_offset ?? 0 }, [active?.id])
  const navigation = session.navigation
  return <div className="reader-scroll" ref={reader} onScroll={event => { if (active) onScroll(event.currentTarget.scrollTop) }}>
    {lesson && active ? <article className="reader-content" onMouseUp={() => {
      const selection = window.getSelection(); if (!selection || selection.isCollapsed || !reader.current?.contains(selection.anchorNode)) return
      const quote = selection.toString().slice(0, 12000)
      // Synthetic preview keeps the actual visible selection, not a fabricated block locator.
      // Persistent anchored notes arrive with M2's exact content-block source mapping.
      const fullText = lesson.body; const start = fullText.indexOf(quote)
      if (start < 0) return
      onSelect({ ref: active.context.active_ref, exact_quote: quote, prefix: fullText.slice(Math.max(0, start - 40), start), suffix: fullText.slice(start + quote.length, start + quote.length + 40), start_codepoint: Array.from(fullText.slice(0, start)).length, end_codepoint: Array.from(fullText.slice(0, start)).length + Array.from(quote).length })
    }}><div className="breadcrumbs">合成示例课程 <span>›</span> 第 {lesson.chapter} 章 <span>›</span> {lesson.chapter}.{lesson.number}</div><div className="synthetic-notice">合成示例 · 仅用于界面验收，不是正式教材或学习证据</div><h1>{lesson.title}</h1><div className="reader-meta">修订 {active.context.active_ref.revision} <span>·</span> 未诊断 <span>·</span> {lesson.sampleState === 'stale' ? '过期引用展示 · 需要复核' : lesson.sampleState === 'read' ? '已读展示（合成）' : '未读'}</div>{lesson.sampleState === 'stale' && <aside className="stale-notice">此处展示过期引用状态；当前引用与草稿保留，未自动迁移到其他修订。</aside>}<Suspense fallback={<p role="status">正在载入本地数学排版…</p>}><Markdown>{lesson.body}</Markdown></Suspense><div className="reader-pagination"><button disabled={fixture.lessons.indexOf(lesson) === 0} onClick={() => onOpen(fixture.lessons[fixture.lessons.indexOf(lesson) - 1])}>← 上一节</button><button disabled={fixture.lessons.indexOf(lesson) === fixture.lessons.length - 1} onClick={() => onOpen(fixture.lessons[fixture.lessons.indexOf(lesson) + 1])}>下一节 →</button></div></article> : active ? <div className="empty-content"><div className="eyebrow">引用待解析</div><h1>暂时无法打开这个对象</h1><p>已保留对象 {active.context.active_ref.id} 的修订 {active.context.active_ref.revision} 和草稿。当前阶段无法读取它的正式内容。</p></div> : <div className="empty-content"><div className="eyebrow">知径 / {navigation === 'route' ? '学习路线' : navigation === 'textbook' ? '教材' : navigation === 'practice' ? '习题' : '测试题'}</div><h1>{navigation === 'route' ? loaded ? '把目标连成一条学习路线' : '从一个学习目标开始' : navigation === 'textbook' ? loaded ? '选择一节，开始阅读' : '你的教材，将从这里展开' : navigation === 'practice' ? '尚无已审核习题' : '尚无已发布测试'}</h1><p>{navigation === 'route' ? '路线帮助你安排阅读、练习和独立测试。当前还没有正式路线，也没有学习证据。' : navigation === 'textbook' ? '教材包含定义、推导与例题；内容会保留来源与准确修订。' : navigation === 'practice' ? '习题与解答会在审核后提供。练习参与和独立测试证据分别记录。' : '独立测试与辅助练习分开记录。当前没有可以开始的测试。'}</p><div className="empty-actions">{!loaded && <button className="primary-button" onClick={onLoad}>浏览合成示例课程 <span aria-hidden="true">→</span></button>}{loaded && (navigation === 'route' || navigation === 'textbook') && <button className="primary-button" onClick={() => onOpen(fixture.lessons[1])}>打开示例小节 →</button>}<button onClick={() => onAux('导入')}>查看导入能力</button></div><div className="empty-footnote"><strong>你的资料保持在本机</strong><p>导入与正式路线编辑尚待后续阶段实现。合成示例只用于体验工作台布局，不会创建成绩或阅读记录。</p></div></div>}
  </div>
}
