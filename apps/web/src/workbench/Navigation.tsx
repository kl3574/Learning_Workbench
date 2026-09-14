import { useEffect, useRef, useState } from 'react'
import { fixture, findLesson, type SyntheticLesson } from '../features/fixture'
import { navigationItems, type Navigation as NavigationKey, type Session } from './model'
export function Navigation({ session, set, loaded, onOpen, onNavigate, onLoad, onAux }: { session: Session; set: (update: (old: Session) => Session) => void; loaded: boolean; onOpen: (lesson: SyntheticLesson, pinned?: boolean) => void; onNavigate: (navigation: NavigationKey) => void; onLoad: () => void; onAux: (name: string) => void }) {
  const [search, setSearch] = useState('')
  const [fullTitles, setFullTitles] = useState(false)
  const scroll = useRef<HTMLDivElement>(null)
  const beforeSearch = useRef(0)
  const nav = session.navigation
  const active = session.tabs.find(tab => tab.id === session.active_tab_id)?.context.active_ref.id
  useEffect(() => { setSearch('') }, [nav])
  useEffect(() => { if (scroll.current) scroll.current.scrollTop = session.directory_scroll }, [loaded])
  const key = (id: string) => `${fixture.course.id}:${nav}:${id}`
  const expanded = (id: string) => session.expanded_keys.includes(key(id))
  const toggle = (id: string) => set(old => ({ ...old, expanded_keys: expanded(id) ? old.expanded_keys.filter(item => item !== key(id)) : [...old.expanded_keys, key(id)] }))
  const title = nav === 'textbook' ? '当前教材目录' : nav === 'route' ? '路线阶段' : nav === 'practice' ? '习题目录' : '测试目录'
  return <div className="navigation-content">
    <section className="course-summary"><div className="eyebrow">当前课程</div><button className="course-switch" onClick={() => onAux('课程切换')}>{loaded ? fixture.course.title : '尚未选择课程'} <span aria-hidden="true">⌄</span></button>
      <p>{loaded ? '合成示例 · 8 章 / 48 节' : '从自己的学习目标开始'}</p>
      <div className="course-progress">{loaded ? '正式阅读记录 0 / 48 · 未诊断' : '暂无阅读记录 · 未诊断'}</div>
      {loaded && <button className="continue" onClick={() => onOpen(findLesson(active) ?? fixture.lessons[1])}>继续浏览示例 <span aria-hidden="true">→</span></button>}
    </section>
    <nav aria-label="学习主导航" className="primary-navigation">{navigationItems.map(item => <button key={item.id} onClick={() => onNavigate(item.id)} aria-current={nav === item.id ? 'page' : undefined}><span className="nav-icon" aria-hidden="true">{item.glyph}</span><span>{item.label}</span>{item.id === 'textbook' && <small>含例题</small>}{item.id === 'practice' && <small>含解答</small>}</button>)}</nav>
    <section className="directory-section" aria-label={title}><div className="directory-heading"><h2>{title}</h2>{loaded && <button className="text-button" aria-pressed={fullTitles} onClick={() => setFullTitles(!fullTitles)}>{fullTitles ? '紧凑标题' : '完整标题'}</button>}</div>
      {loaded && (nav === 'route' || nav === 'textbook') && <label className="directory-search"><span className="sr-only">搜索当前目录</span><input value={search} placeholder="搜索章节、小节" onChange={event => { if (!search) beforeSearch.current = scroll.current?.scrollTop ?? 0; setSearch(event.target.value); if (!event.target.value) requestAnimationFrame(() => { if (scroll.current) scroll.current.scrollTop = beforeSearch.current }) }} />{search && <button aria-label="清除目录搜索" onClick={() => { setSearch(''); requestAnimationFrame(() => { if (scroll.current) scroll.current.scrollTop = beforeSearch.current }) }}>×</button>}</label>}
      <div className="directory-scroll" ref={scroll} onScroll={event => { if (!search) { const offset = event.currentTarget.scrollTop; set(old => old.directory_scroll === offset ? old : { ...old, directory_scroll: offset }) } }}>
      {!loaded ? <div className="directory-empty"><p>课程导入后，目录会显示在这里。</p><button className="text-button" onClick={onLoad}>加载合成示例课程</button></div> : nav === 'practice' || nav === 'assessment' ? <div className="directory-empty"><p>{nav === 'practice' ? '尚无已审核习题' : '尚无已发布测试'}</p><small>示例课程只包含阅读布局材料。</small></div> : <nav aria-label="上下文目录"><ul className="chapters">{fixture.chapters.map(chapter => {
        const lessons = fixture.lessons.filter(lesson => chapter.lessonIds.includes(lesson.id) && (!search || `${chapter.title} ${lesson.title}`.includes(search)))
        if (!lessons.length) return null
        return <li key={chapter.id}><div className="chapter-row"><button className="disclosure" aria-label={`${expanded(chapter.id) ? '折叠' : '展开'}${chapter.title}`} aria-expanded={!!search || expanded(chapter.id)} onClick={() => toggle(chapter.id)}>{search || expanded(chapter.id) ? '⌄' : '›'}</button><a href={`#${chapter.id}`} onClick={event => { event.preventDefault(); onOpen(lessons[0]) }}>{nav === 'route' ? chapter.title.replace('第 ', '阶段 ').replace(' 章', '') : chapter.title}</a></div>
        {(search || expanded(chapter.id)) && <ul className="lessons">{lessons.map(lesson => <li key={lesson.id}><a className={`lesson-link ${fullTitles ? 'full-title' : ''}`} href={`#${lesson.id}`} aria-current={active === lesson.id ? 'page' : undefined} title={lesson.title} onClick={event => { event.preventDefault(); onOpen(lesson) }} onDoubleClick={() => onOpen(lesson, true)}><span className="lesson-state" aria-label={lesson.sampleState === 'read' ? '已读（合成展示）' : lesson.sampleState === 'stale' ? '过期引用（合成展示）' : '未读'}>{lesson.sampleState === 'read' ? '✓' : lesson.sampleState === 'stale' ? '↻' : '○'}</span><span className="lesson-label">{lesson.title}</span></a>{search && <small className="search-breadcrumb">{chapter.title}</small>}</li>)}</ul>}</li>
      })}</ul>{search && !fixture.lessons.some(lesson => `${fixture.chapters[lesson.chapter - 1].title} ${lesson.title}`.includes(search)) && <p className="directory-empty">没有匹配的章节。</p>}</nav>}
      </div>
    </section>
    <footer className="navigation-tools">{['笔记', '创作', '设置'].map(name => <button key={name} onClick={() => onAux(name)}>{name}</button>)}</footer>
  </div>
}
