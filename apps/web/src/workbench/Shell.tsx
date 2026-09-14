import { useEffect, useState, type CSSProperties } from 'react'
import { fixture, fixtureRef, findLesson, sameRef, type SyntheticLesson } from '../features/fixture'
import { ConflictComparison } from './ConflictComparison'
import { ImportWorkflow } from '../features/imports/ImportWorkflow'
import { Dialog, Splitter } from './Controls'
import { Navigation } from './Navigation'
import { Reader } from './Reader'
import { Tutor } from './Tutor'
import { navigationItems, openTab, type Navigation as NavigationKey, type ViewContext } from './model'
import { readDirectory, saveDirectory, readLastReading, saveLastReading } from './uiCache'
import { useWorkbench } from './useWorkbench'
const auxiliaryText: Record<string, string> = {
  '创建路线': '正式路线编辑尚未实现；未来会校验精确引用和先修环。当前没有保存或发布动作。',
  '开始练习': '当前没有已审核练习，尚不能创建作答会话。',
  '打开测试记录': '当前没有测试记录。测试功能尚待后续阶段实现。',
  '导出备份': '备份导出尚未实现，当前不会生成无效备份或下载成功回执。',
  '设置': '当前提供商未配置。密钥设置尚未开放，浏览器不保存或显示密钥。',
  '笔记': '正式笔记需要精确内容块与修订持久化，将在内容阶段开放。问题草稿已可按对象在本机浏览器保留。',
  '创作': '创作、独立审校与发布尚未实现。模型生成不会直接覆盖正式教材。',
}
export function Shell() {
  const { session, set, status, error, drafts, updateDraft, reconnect, draftConflicts, draftSaving, draftErrors, chooseDraft, draftResolving, workspaceId, recoverable, restorePending, comparison, retainLocal, draftBases, draftStored } = useWorkbench()
  const [width, setWidth] = useState(innerWidth)
  const [drawer, setDrawer] = useState<'nav' | 'agent' | null>(null)
  const [dialog, setDialog] = useState<string | null>(null)
  const [commandSearch, setCommandSearch] = useState('')
  const [historyWarning, setHistoryWarning] = useState('')
  const [closing, setClosing] = useState<string | null>(null)
  const focus = session.nav_collapsed && session.agent_collapsed
  const setFocus = (enabled: boolean) => set(old => ({ ...old, nav_collapsed: enabled, agent_collapsed: enabled }))
  const loaded = sameRef(session.course_ref, fixture.course.ref)
  const active = session.tabs.find(tab => tab.id === session.active_tab_id)
  const activeLesson = findLesson(active?.context.active_ref)
  useEffect(() => { if (activeLesson && workspaceId && !saveLastReading(workspaceId, fixture.course.id, 'textbook', fixtureRef(activeLesson.ref))) setHistoryWarning('最后阅读对象尚未保存：浏览器缓存不可用。') }, [activeLesson?.id, workspaceId])
  const draftId = active?.id ?? `empty_${session.navigation}`
  const desktop = width >= 1280
  const navVisible = width >= 820 && !session.nav_collapsed && !focus
  const agentVisible = desktop && !session.agent_collapsed && !focus
  useEffect(() => { const resize = () => { setWidth(innerWidth); setDrawer(null) }; addEventListener('resize', resize); return () => removeEventListener('resize', resize) }, [])
  useEffect(() => { const shortcut = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'p') { event.preventDefault(); setDialog('命令面板') } if (event.key === 'Escape' && focus) setFocus(false) }; addEventListener('keydown', shortcut); return () => removeEventListener('keydown', shortcut) }, [focus])
  const openLesson = (lesson: SyntheticLesson, pinned = false) => {
    const context: ViewContext = { view_kind: 'lesson', active_ref: fixtureRef(lesson.ref), attached_refs: [], selection: null, attempt_id: null }
    set(old => { const readingSession = { ...old, navigation: 'textbook' as const }; const next = openTab(readingSession, context, pinned, id => !!drafts[id]); const key = `${fixture.course.id}:${readingSession.navigation}:synthetic_chapter_${lesson.chapter}`; return { ...next, expanded_keys: next.expanded_keys.includes(key) ? next.expanded_keys : [...next.expanded_keys, key] } })
    setDrawer(null)
  }
  const loadFixture = () => { set(old => ({ ...old, course_ref: fixtureRef(fixture.course.ref), expanded_keys: [...old.expanded_keys, `${fixture.course.id}:textbook:synthetic_chapter_1`] })); setDialog(null) }
  const navigate = (navigation: NavigationKey) => { set(old => { saveDirectory(workspaceId, old.course_ref?.id ?? null, old.navigation, old.directory_scroll); return { ...old, navigation, active_tab_id: null, directory_scroll: readDirectory(workspaceId, old.course_ref?.id ?? null, navigation) } }); setDrawer(null) }
  const toggleSide = (side: 'nav' | 'agent') => {
    if (side === 'nav' ? width < 820 : !desktop) { setDrawer(side); return }
    set(old => ({ ...old, [`${side}_collapsed`]: !old[`${side}_collapsed`] }))
  }
  const closeTab = (id: string) => { set(old => { const tabs = old.tabs.filter(tab => tab.id !== id); return { ...old, tabs, active_tab_id: old.active_tab_id === id ? tabs.at(-1)?.id ?? null : old.active_tab_id } }); setClosing(null) }
  const nav = <Navigation session={session} set={set} loaded={loaded} onOpen={openLesson} lastLesson={findLesson(readLastReading(workspaceId, fixture.course.id, 'textbook'))} onNavigate={navigate} onLoad={loadFixture} onAux={setDialog} />
  const tutor = <Tutor context={active?.context ?? null} title={activeLesson?.title ?? active?.context.active_ref.id ?? ''} resolved={!!activeLesson} baseDraft={draftBases[draftId] ?? null} storedDraft={draftStored[draftId] ?? ''} draft={drafts[draftId] ?? ''} onDraft={text => updateDraft(draftId, text)} conflicts={draftConflicts[draftId] ?? []} saving={!!draftSaving[draftId]} enabled={!!workspaceId && status !== 'connecting' && !draftResolving[draftId]} error={draftErrors[draftId] ?? draftErrors._storage ?? ''} choose={candidate => void chooseDraft(draftId, candidate)} />
  const commands = [
    { title: '打开对象', action: () => { setDialog('打开对象') } },
    ...['导入', '创建路线', '开始练习', '打开测试记录', '导出备份'].map(title => ({ title, action: () => setDialog(title) })),
    { title: '切换导航栏', action: () => { setDialog(null); toggleSide('nav') } },
    { title: '切换 Agent 栏', action: () => { setDialog(null); toggleSide('agent') } },
    { title: '切换专注模式', action: () => { setDialog(null); setFocus(!focus) } },
    { title: '查看快捷键', action: () => setDialog('快捷键') },
  ]
  return <div className={`app-shell ${focus ? 'focus-mode' : ''}`}>
    <a href="#reader-main" className="skip-link">跳到学习内容</a>
    <header className="topbar"><a className="brand" href="#" onClick={event => { event.preventDefault(); navigate('route') }}><span className="brand-symbol" aria-hidden="true">径</span><strong>知径</strong><span className="brand-subtitle">学习工作台</span></a><button className="command-trigger" onClick={() => setDialog('命令面板')}><span aria-hidden="true">⌕</span> 搜索与命令 <kbd>Ctrl ⇧ P</kbd></button><div className="topbar-tools"><button onClick={() => toggleSide('nav')} aria-label="切换导航栏" aria-expanded={width < 820 ? drawer === 'nav' : navVisible}>目录</button><button onClick={() => toggleSide('agent')} aria-label="切换 Agent 栏" aria-expanded={!desktop ? drawer === 'agent' : agentVisible}>Agent</button><button className="focus-trigger" onClick={() => setFocus(!focus)} aria-pressed={focus}>{focus ? '退出专注' : '专注'}</button><button className="import-trigger" onClick={() => setDialog('导入')}>导入</button></div></header>
    {historyWarning && <div className="save-alert" role="status">{historyWarning}</div>}
    {error && <div className={`save-alert ${status === 'conflict' ? 'conflict' : ''}`} role="status"><span>{error}</span><button onClick={() => void reconnect(status === 'conflict')}>{status === 'conflict' ? '读取服务端会话，保留草稿' : '重试连接'}</button></div>}
    {status === 'conflict' && comparison && <ConflictComparison comparison={comparison} retainLocal={retainLocal} useServer={() => void reconnect(true)} />}
    {recoverable.length > 0 && <div className="save-alert" role="status"><span>发现其他窗口的待同步 UI 快照；原始快照保留。</span>{recoverable.map((snapshot, index) => <button key={snapshot.key} onClick={() => restorePending(snapshot)}>恢复待同步快照 {index + 1}</button>)}</div>}
    <div className="workbench-grid" style={{ '--nav-width': navVisible ? `${session.nav_width}px` : '0px', '--agent-width': agentVisible ? `${session.agent_width}px` : '0px', '--nav-divider': width >= 820 && !focus ? '6px' : '0px', '--agent-divider': desktop && !focus ? '6px' : '0px' } as CSSProperties}>
      <aside id="nav-pane" className="nav-pane" aria-label="课程导航" hidden={!navVisible}>{navVisible && nav}</aside>
      {width >= 820 && !focus ? <Splitter side="nav" value={session.nav_width} otherWidth={agentVisible ? session.agent_width : 0} collapsed={!navVisible} onResize={value => set(old => ({ ...old, nav_width: value }))} toggle={() => toggleSide('nav')} /> : <span />}
      <main id="reader-main" className="reader-main" tabIndex={-1}><div className="tab-bar" role="tablist" aria-label="打开的学习对象" onKeyDown={event => { if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return; const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("[role=tab]")); const current = tabs.indexOf(event.target as HTMLButtonElement); if (current < 0) return; event.preventDefault(); const index = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length; tabs[index].focus(); tabs[index].click() }}><button className={`home-tab ${!active ? 'active' : ''}`} role="tab" tabIndex={!active ? 0 : -1} aria-selected={!active} onClick={() => set(old => ({ ...old, active_tab_id: null }))}>{navigationItems.find(item => item.id === session.navigation)?.label}</button>{session.tabs.map(tab => <div className={`object-tab ${tab.id === active?.id ? 'active' : ''}`} key={tab.id}><button role="tab" tabIndex={tab.id === active?.id ? 0 : -1} aria-selected={tab.id === active?.id} title={findLesson(tab.context.active_ref)?.title ?? tab.context.active_ref.id} onClick={() => set(old => ({ ...old, active_tab_id: tab.id }))} onDoubleClick={() => set(old => ({ ...old, tabs: old.tabs.map(item => item.id === tab.id ? { ...item, pinned: true } : item) }))}>{tab.pinned && <span aria-label="已固定">⌖ </span>}{findLesson(tab.context.active_ref)?.title ?? tab.context.active_ref.id}{drafts[tab.id] && <span aria-label="有问题草稿"> •</span>}</button><button className="tab-pin" aria-label={`固定标签 ${findLesson(tab.context.active_ref)?.title ?? tab.context.active_ref.id}`} onClick={() => set(old => ({ ...old, tabs: old.tabs.map(item => item.id === tab.id ? { ...item, pinned: !item.pinned } : item) }))}>{tab.pinned ? '⌖' : '⋄'}</button><button className="tab-close" aria-label={`关闭标签 ${findLesson(tab.context.active_ref)?.title ?? tab.context.active_ref.id}`} onClick={() => drafts[tab.id] ? setClosing(tab.id) : closeTab(tab.id)}>×</button></div>)}</div><Reader session={session} workspaceId={workspaceId} loaded={loaded} onLoad={loadFixture} onOpen={openLesson} onSelect={selection => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === old.active_tab_id ? { ...tab, context: { ...tab.context, selection } } : tab) }))} onScroll={offset => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === old.active_tab_id ? { ...tab, scroll_offset: offset } : tab) }))} onAux={setDialog} /></main>
      {desktop && !focus ? <Splitter side="agent" value={session.agent_width} otherWidth={navVisible ? session.nav_width : 0} collapsed={!agentVisible} onResize={value => set(old => ({ ...old, agent_width: value }))} toggle={() => toggleSide('agent')} /> : <span />}
      <aside id="agent-pane" className="agent-pane" aria-label="Agent 助教" hidden={!agentVisible}>{agentVisible && tutor}</aside>
    </div>
    <footer className="statusbar" role="status"><span className={status === 'saved' ? 'saved' : ''}>{status === 'saved' ? '✓ UI 会话已保存' : status === 'saving' ? '会话保存中…' : status === 'connecting' ? '连接本机服务…' : status === 'conflict' ? '会话版本冲突' : '离线 · UI 待同步'}</span><span>{active ? `内容修订 ${active.context.active_ref.revision}` : '尚未选择对象'}</span><span>{loaded ? '合成示例 · 无学习证据' : '正常学习'} · 本机</span></footer>
    {drawer && <Dialog title={drawer === 'nav' ? '课程目录' : 'Agent 助教'} className={`drawer drawer-${drawer}`} close={() => setDrawer(null)}>{drawer === 'nav' ? nav : tutor}</Dialog>}
    {dialog && <Dialog title={dialog} className={dialog === '导入' ? 'import-dialog' : ''} close={() => setDialog(null)}>{dialog === '导入' ? workspaceId ? <ImportWorkflow key={workspaceId} workspaceId={workspaceId} close={() => setDialog(null)} /> : <p>工作区会话尚未连接。连接成功后可上传文件或恢复已有导入。</p> : dialog === '命令面板' ? <><label className="sr-only" htmlFor="command-search">筛选命令</label><input id="command-search" className="command-search" value={commandSearch} onChange={event => setCommandSearch(event.target.value)} placeholder="输入命令名称…" /><div className="command-list">{commands.filter(command => command.title.includes(commandSearch)).map(command => <button key={command.title} onClick={command.action}>{command.title}<span>↵</span></button>)}</div></> : dialog === '快捷键' ? <ul className="shortcut-list"><li>Ctrl / ⌘ + Shift + P：命令面板</li><li>分隔条：← / → 每次调整 16px</li><li>Home / End：到达宽度边界</li><li>Enter：折叠或恢复侧栏</li><li>Esc：关闭抽屉、对话框或退出专注</li><li>Tab / Shift + Tab：移动焦点</li></ul> : dialog === '课程切换' ? <><p>正式课程摘要与精确引用可在导入结果查看。正式阅读与目录尚未接通；这里可以独立加载合成 UI 示例。</p><button className="primary-button" onClick={loadFixture}>加载合成示例课程</button>{loaded && <button onClick={() => { set(old => ({ ...old, course_ref: null, tabs: old.tabs.filter(tab => !tab.context.active_ref.id.startsWith('synthetic_')), active_tab_id: null })); setDialog(null) }}>退出合成示例</button>}</> : dialog === '打开对象' ? loaded ? <div className="command-list">{fixture.lessons.map(lesson => <button key={lesson.id} onClick={() => { openLesson(lesson, true); setDialog(null) }}>{lesson.title}</button>)}</div> : <p>正式阅读入口尚未接通。可在导入结果查看实际课程摘要，或加载合成示例体验布局。</p> : <><p>{auxiliaryText[dialog] ?? '此辅助能力尚未实现。'}</p><p className="muted">能力状态：未实现 · 没有执行业务写入。</p></>}</Dialog>}
    {closing && <Dialog title="保留问题草稿" close={() => setClosing(null)}><p>该对象有尚未发送的问题草稿。关闭标签前选择如何处理。</p><div className="dialog-actions"><button className="primary-button" disabled={draftSaving[closing] || !!draftErrors[closing]} onClick={() => closeTab(closing)}>保留本地草稿并关闭</button><button onClick={() => { updateDraft(closing, ''); closeTab(closing) }}>放弃草稿并关闭</button><button onClick={() => setClosing(null)}>取消</button></div></Dialog>}
  </div>
}
