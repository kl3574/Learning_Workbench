import { useEffect, useRef, useState } from 'react'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import { navigationItems, type Navigation, type Session } from '../../workbench/model'
import { readLastReading } from '../../workbench/uiCache'
import { useCourseDirectory, useDirectorySearch } from './useCourseDirectory'
import { sameRef, readerHref, type ReaderTarget } from './target'
export function CourseDirectory({ session, workspace, version, set, open, navigate, aux, loadSynthetic }: { session: Session; workspace: string | null; version: number; set: (change: (old: Session) => Session) => void; open: (target: ReaderTarget, pinned?: boolean) => void; navigate: (key: Navigation) => void; aux: (name: string) => void; loadSynthetic: () => void }) {
  const { course, outline, error, loading } = useCourseDirectory(session.course_ref, workspace, version)
  const [query, setQuery] = useState('')
  const [full, setFull] = useState(false)
  const search = useDirectorySearch(session.navigation === 'textbook' ? session.course_ref : null, query)
  const scroll = useRef<HTMLDivElement>(null)
  const ready = useRef(false)
  const beforeSearch = useRef(0)
  const selected = session.tabs.find(tab => tab.id === session.active_tab_id)?.context.active_ref
  const courseRef = session.course_ref
  const key = (id: string) => `${courseRef?.id}:${courseRef?.revision}:${session.navigation}:${id}`
  const toggle = (id: string) => set(old => ({ ...old, expanded_keys: old.expanded_keys.includes(key(id)) ? old.expanded_keys.filter(value => value !== key(id)) : [...old.expanded_keys, key(id)] }))
  useEffect(() => { setQuery(''); ready.current = false }, [courseRef?.id, courseRef?.revision, session.navigation])
  useEffect(() => {
    if (!outline || !scroll.current) return
    scroll.current.scrollTop = session.directory_scroll; ready.current = true
    const ancestors = outline.sections.flatMap(section => section.lessons.filter(lesson => sameRef(lesson.ref, selected) || lesson.blocks.some(block => sameRef(block.ref, selected))).flatMap(lesson => [key(section.id), key(lesson.ref.id)]))
    if (ancestors.some(value => !session.expanded_keys.includes(value))) set(old => ({ ...old, expanded_keys: [...new Set([...old.expanded_keys, ...ancestors])] }))
  }, [outline, selected?.id, selected?.revision, session.navigation])
  const targetFor = (ref: ContentRef): ReaderTarget | null => {
    if (!courseRef || !outline) return null
    for (const section of outline.sections) for (const lesson of section.lessons) {
      if (sameRef(lesson.ref, ref)) return { course: courseRef, lesson: lesson.ref }
      const block = lesson.blocks.find(block => sameRef(block.ref, ref))
      if (block) return { course: courseRef, lesson: lesson.ref, block: ref, view: block.kind === 'worked_example' ? 'worked_example' : 'lesson' }
    }
    return null
  }
  const link = (ref: ContentRef, title: string) => {
    const target = targetFor(ref)
    return target ? <a href={readerHref(target)} title={title} aria-current={sameRef(ref, selected) ? 'page' : undefined} onClick={event => { event.preventDefault(); open(target) }} onDoubleClick={() => open(target, true)}>{title}</a> : <span>{title} · 引用待解析</span>
  }
  const changeSearch = (value: string) => { if (!query) beforeSearch.current = scroll.current?.scrollTop ?? 0; setQuery(value); if (!value) requestAnimationFrame(() => { if (scroll.current) scroll.current.scrollTop = beforeSearch.current }) }
  const readings = outline?.sections.flatMap(section => section.lessons) ?? []
  const last = courseRef ? readLastReading(workspace, courseRef.id, 'textbook') : null
  const continueTarget = (last && targetFor(last)) || (readings[0] && targetFor(readings[0].ref))
  return <div className="navigation-content"><section className="course-summary"><div className="eyebrow">当前课程</div><button className="course-switch" onClick={() => aux('课程切换')}>{course?.title ?? (courseRef ? '正在解析所选课程' : '尚未选择课程')} <span aria-hidden="true">⌄</span></button><p>{course ? `${outline?.sections.length ?? '…'} 章 / ${course.lesson_refs.length} 节 · 尚未审校` : '从自己的学习目标开始'}</p><div className="course-progress">{outline ? `已阅读 ${readings.filter(item => item.reading_state === 'read').length} / ${readings.length} · 未诊断` : '暂无已读取的阅读记录 · 未诊断'}</div>{courseRef && <button className="text-button" onClick={() => aux('教材修订')}>查看教材修订</button>}{continueTarget && <button className="continue" onClick={() => open(continueTarget)}>继续阅读 →</button>}</section>
    <nav aria-label="学习主导航" className="primary-navigation">{navigationItems.map(item => <button key={item.id} aria-current={session.navigation === item.id ? 'page' : undefined} onClick={() => navigate(item.id)}><span className="nav-icon" aria-hidden="true">{item.glyph}</span><span>{item.label}</span>{item.id === 'textbook' && <small>含例题</small>}{item.id === 'practice' && <small>含解答</small>}</button>)}</nav>
    <section className="directory-section" aria-label="当前教材目录"><div className="directory-heading"><h2>{session.navigation === 'textbook' ? '当前教材目录' : '上下文目录'}</h2>{outline && session.navigation === 'textbook' && <button className="text-button" onClick={() => setFull(!full)}>{full ? '紧凑标题' : '完整标题'}</button>}</div>
      {outline && session.navigation === 'textbook' && <label className="directory-search"><span className="sr-only">搜索当前目录</span><input value={query} placeholder="搜索章节、小节、内容块标题" onChange={event => changeSearch(event.target.value)} />{query && <button aria-label="清除目录搜索" onClick={() => changeSearch('')}>×</button>}</label>}
      <div ref={scroll} className={`directory-scroll ${full ? 'directory-full' : ''}`} onScroll={event => { if (ready.current && !query) { const value = event.currentTarget.scrollTop; set(old => old.directory_scroll === value ? old : { ...old, directory_scroll: value }) } }}>
        {loading && <p role="status">正在读取精确课程目录…</p>}{error && <p role="alert">{error} 原引用仍保留。</p>}
        {!courseRef && <div className="directory-empty"><p>尚未选择教材。导入材料或选择已导入课程开始阅读。</p><button onClick={() => aux('导入')}>导入资料</button><button className="text-button" onClick={loadSynthetic}>加载合成示例课程</button></div>}
        {session.navigation !== 'textbook' ? <p className="directory-empty">{session.navigation === 'route' ? '尚无正式学习路线' : session.navigation === 'practice' ? '尚无已审核习题' : '尚无已发布测试'}</p> : query ? <nav aria-label="目录搜索结果">{search.loading && <p role="status">正在搜索此课程标题…</p>}{search.error && <p role="alert">{search.error}</p>}<ul className="chapters">{search.hits.map(hit => <li key={`${hit.ref.id}:${hit.ref.revision}`} className="directory-hit">{link(hit.ref, hit.title)}<small>{hit.ancestors.map(item => item.title).join(' › ')}</small></li>)}</ul>{!search.loading && !search.error && !search.hits.length && <p>没有匹配的目录标题。</p>}</nav> : outline && <nav aria-label="上下文目录"><ul className="chapters">{outline.sections.map(section => <li key={section.id}><div className="chapter-row"><button className="disclosure" aria-expanded={session.expanded_keys.includes(key(section.id))} aria-label={`${session.expanded_keys.includes(key(section.id)) ? '折叠' : '展开'}${section.title}`} onClick={() => toggle(section.id)}>{session.expanded_keys.includes(key(section.id)) ? '⌄' : '›'}</button>{section.lessons[0] && link(section.lessons[0].ref, section.title)}</div>{session.expanded_keys.includes(key(section.id)) && <ul className="lessons">{section.lessons.map(lesson => <li key={lesson.ref.id}><div className="real-lesson-row"><button className="disclosure" aria-expanded={session.expanded_keys.includes(key(lesson.ref.id))} aria-label={`展开内容块：${lesson.title}`} onClick={() => toggle(lesson.ref.id)}>›</button><span className="lesson-state" aria-label={lesson.reading_state === 'read' ? '已阅读' : lesson.reading_state === 'stale' ? '过期阅读记录' : '未读'}>{lesson.reading_state === 'read' ? '✓' : lesson.reading_state === 'stale' ? '↻' : '○'}</span>{link(lesson.ref, lesson.title)}</div>{session.expanded_keys.includes(key(lesson.ref.id)) && <ul className="block-links">{lesson.blocks.map(block => <li key={block.ref.id}>{link(block.ref, `${block.kind === 'worked_example' ? '例题 · ' : ''}${block.title}`)}</li>)}</ul>}</li>)}</ul>}</li>)}</ul></nav>}
      </div></section><footer className="navigation-tools">{['笔记', '创作', '设置'].map(name => <button key={name} onClick={() => aux(name)}>{name}</button>)}</footer></div>
}
