import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { fixture, fixtureRef, findLesson, sameRef, type SyntheticLesson } from '../features/fixture'
import { ConflictComparison } from './ConflictComparison'
import { ImportWorkflow } from '../features/imports/ImportWorkflow'
import { Dialog, Splitter } from './Controls'
import { Navigation } from './Navigation'
import { Reader } from './Reader'
import { Tutor } from './Tutor'
import { getSessionGeneration } from '../api/client'
import { navigationItems, openTab, type Navigation as NavigationKey, type ViewContext } from './model'
import { readDirectory, saveDirectory, readLastReading, saveLastReading } from './uiCache'
import { useWorkbench } from './useWorkbench'
import type { ContentRef, Selection } from '../../../../packages/contracts/generated/types'
import { CourseDirectory } from '../features/reader/CourseDirectory'
import { CourseRevisions } from '../features/reader/CourseRevisions'
import { CoursePicker } from '../features/reader/CoursePicker'
import { ReaderDocument } from '../features/reader/ReaderDocument'
import { contextTarget, readTarget, readerHref, type ReaderTarget } from '../features/reader/target'
import { openReader, referenceConflictMessage } from '../features/reader/navigation'
import { resolveAnchor } from '../features/reader/resolveAnchor'
import { PracticePreview } from '../features/practice/PracticePreview'
import { PracticeView, type PracticeViewState } from '../features/practice/PracticeView'
import { LessonPracticeLinks } from '../features/practice/LessonPracticeLinks'
import { openPractice, practiceTarget, practiceHref, readPracticeTarget, type PracticeTarget } from '../features/practice/target'
import { AssessmentPreview } from '../features/assessment/AssessmentPreview'
import { AssessmentView, type AssessmentViewState } from '../features/assessment/AssessmentView'
import { AssessmentNavigation } from '../features/assessment/AssessmentNavigation'
import { OperationHelp } from '../features/assessment/OperationHelp'
import { useWorkspacePolicy } from '../features/assessment/useWorkspacePolicy'
import { assessmentTarget, readAssessmentTarget, assessmentHref, openAssessment, type AssessmentTarget } from '../features/assessment/target'
import type { AttemptSnapshot } from '../../../../packages/contracts/generated/api-types'
import { NotesPanel } from '../features/notes/NotesPanel'
const auxiliaryText: Record<string, string> = {
  '创建路线': '正式路线编辑尚未实现；未来会校验精确引用和先修环。当前没有保存或发布动作。',
  '导出备份': '备份导出尚未实现，当前不会生成无效备份或下载成功回执。',
  '设置': '当前提供商未配置。密钥设置尚未开放，浏览器不保存或显示密钥。',
  '笔记': '正式笔记需要精确内容块与修订持久化，将在内容阶段开放。问题草稿已可按对象在本机浏览器保留。',
  '创作': '创作、独立审校与发布尚未实现。模型生成不会直接覆盖正式教材。',
}
export function Shell() {
  const { session, set, status, error, drafts, updateDraft, reconnect, draftConflicts, draftSaving, draftErrors, chooseDraft, draftResolving, workspaceId, recoverable, restorePending, comparison, retainLocal, draftBases, draftStored } = useWorkbench()
  const policy = useWorkspacePolicy(workspaceId)
  const [assessmentStates, setAssessmentStates] = useState<Record<string, AssessmentViewState>>({})
  const assessmentStatesRef = useRef(assessmentStates); assessmentStatesRef.current = assessmentStates
  const [assessmentQuestion, setAssessmentQuestion] = useState<{ tab: string; id: string; sequence: number } | null>(null)
  const [width, setWidth] = useState(innerWidth)
  const [drawer, setDrawer] = useState<'nav' | 'agent' | null>(null)
  const [dialog, setDialog] = useState<string | null>(null)
  const [commandSearch, setCommandSearch] = useState('')
  const [readerLinkError, setReaderLinkError] = useState('')
  const [historyWarning, setHistoryWarning] = useState('')
  const [closing, setClosing] = useState<string | null>(null)
  const [progressVersion, setProgressVersion] = useState(0)
  const [realTitles, setRealTitles] = useState<Record<string, { title: string; resolved: boolean }>>({})
  const [noteSelection, setNoteSelection] = useState<Selection | null>(null)
  const [noteState, setNoteState] = useState({ dirty: false, safe: true })
  const [closingNotes, setClosingNotes] = useState(false)
  const [practiceStates, setPracticeStates] = useState<Record<string, PracticeViewState>>({})
  const practiceStatesRef = useRef(practiceStates); practiceStatesRef.current = practiceStates
  const [practiceQuestion, setPracticeQuestion] = useState<{ tab: string; id: string; sequence: number } | null>(null)
  const [practiceLesson, setPracticeLesson] = useState<ReaderTarget | null>(null)
  const deepOpened = useRef<string | null>(null)
  const focus = session.nav_collapsed && session.agent_collapsed
  const setFocus = (enabled: boolean) => set(old => ({ ...old, nav_collapsed: enabled, agent_collapsed: enabled }))
  const loaded = sameRef(session.course_ref, fixture.course.ref)
  const latestDrafts = useRef(drafts); latestDrafts.current = drafts
  const active = session.tabs.find(tab => tab.id === session.active_tab_id)
  const tabLabel = (tab: typeof session.tabs[number]) => findLesson(tab.context.active_ref)?.title ?? `${realTitles[tab.id]?.title || (assessmentTarget(tab.context) ? tab.context.view_kind === 'assessment_review' ? '测试复盘' : tab.context.attempt_id ? '测试作答' : '测试范围' : tab.context.active_ref.id)} · r${tab.context.active_ref.revision}`
  const activeLesson = findLesson(active?.context.active_ref)
  const activeTitle = activeLesson?.title ?? (active && realTitles[active.id]?.title) ?? active?.context.active_ref.id ?? ''
  const activePractice = active ? practiceTarget(active.context) : null
  const activeAssessment = active ? assessmentTarget(active.context) : null
  const subjectLocked = !policy.known || !!policy.independentId
  const canLeave = () => { if (active && (practiceStatesRef.current[active.id]?.safe === false || assessmentStatesRef.current[active.id]?.safe === false)) { setHistoryWarning('当前作答尚未安全保存到本机，请保持页面打开并重试；未切换对象。'); return false }; return true }
  const hasDraft = (id: string) => !!latestDrafts.current[id] || !!practiceStatesRef.current[id]?.dirty || practiceStatesRef.current[id]?.safe === false || !!assessmentStatesRef.current[id]?.dirty || assessmentStatesRef.current[id]?.safe === false
  const openAux = (name: string) => { if (subjectLocked && !['设置', '快捷键', '命令面板'].includes(name)) { setHistoryWarning('当前测试策略限制此操作。可返回自己的测试、提交或明确放弃。'); return }; if (name === '打开测试记录') { navigate('assessment'); return }; if (name === '笔记') { setNoteSelection(active?.context.selection ?? null); setNoteState({ dirty: false, safe: true }) }; setDialog(name) }
  const closeDialog = () => { if (dialog === '笔记' && (noteState.dirty || !noteState.safe)) setClosingNotes(true); else setDialog(null) }
  const clearReaderLink = () => { if ((new URLSearchParams(location.search).has('reader') || new URLSearchParams(location.search).has('practice') || new URLSearchParams(location.search).has('assessment'))) history.pushState(null, '', '/') }
  const chooseCourse = (ref: ContentRef) => { if (!canLeave()) return; setReaderLinkError(''); clearReaderLink(); set(old => ({ ...old, course_ref: ref, navigation: 'textbook', active_tab_id: null, directory_scroll: readDirectory(workspaceId, ref.id, 'textbook') })); setDialog(null) }
  const openReal = (target: ReaderTarget, pinned = false) => {
    if (!canLeave()) return
    let opened = false
    set(old => {
      const result = openReader(old, target, pinned, hasDraft)
      if (result.kind === 'conflict') { setReaderLinkError(referenceConflictMessage); return old }
      opened = true; return result.session
    })
    if (!opened) return
    setReaderLinkError('')
    const href = readerHref(target)
    if (location.pathname + location.search + location.hash !== href) history.pushState(null, '', href)
    setDrawer(null)
  }
  const openExercise = (target: PracticeTarget, pinned = false) => {
    if (!canLeave()) return
    let opened = false
    set(old => { const result = openPractice(old, target, pinned, hasDraft); if (result.kind === 'conflict') { setReaderLinkError(referenceConflictMessage); return old }; opened = true; return result.session })
    if (!opened) return
    setReaderLinkError(''); const href = practiceHref(target); if (location.pathname + location.search !== href) history.pushState(null, '', href); setDrawer(null); setDialog(null)
  }
  const openTest = (target: AssessmentTarget, pinned = false) => {
    if (!canLeave()) return
    let opened = false
    set(old => { const result = openAssessment(old, target, pinned, hasDraft); if (result.kind === 'conflict') { setReaderLinkError(referenceConflictMessage); return old }; opened = true; return result.session })
    if (!opened) return
    setReaderLinkError(''); const href = assessmentHref(target)
    if (location.pathname + location.search + location.hash !== href) history.pushState(null, '', href)
    setDrawer(null)
  }
  const resumeTest = (snapshot: AttemptSnapshot) => {
    const existing = session.tabs.map(tab => assessmentTarget(tab.context)).find(target => target?.attempt_id === snapshot.id)
    openTest(existing ?? { assessment_ref: snapshot.assessment_ref, attempt_id: snapshot.id, ...(session.course_ref && snapshot.preflight.course_refs.some(ref => sameRef(session.course_ref, ref)) ? { course_ref: session.course_ref } : {}) }, true)
  }
  const navigationCallbacks = useRef({ openReal, openExercise, openTest }); navigationCallbacks.current = { openReal, openExercise, openTest }
  useEffect(() => {
    if (!workspaceId || status === 'connecting' || deepOpened.current === workspaceId) return
    deepOpened.current = workspaceId
    try { const assessment = readAssessmentTarget(); const exercise = readPracticeTarget(); const target = readTarget(); if ([assessment, exercise, target].filter(Boolean).length > 1) throw new Error('链接同时声明多个学习对象，未猜测目标。'); if (assessment) navigationCallbacks.current.openTest(assessment, true); else if (exercise) navigationCallbacks.current.openExercise(exercise, true); else if (target) navigationCallbacks.current.openReal(target, true) } catch (reason) { setHistoryWarning((reason as Error).message) }
  }, [workspaceId, status])
  useEffect(() => {
    const read = () => { try { const assessment = readAssessmentTarget(); const exercise = readPracticeTarget(); const target = readTarget(); if ([assessment, exercise, target].filter(Boolean).length > 1) throw new Error('链接同时声明多个学习对象，未猜测目标。'); if (assessment) navigationCallbacks.current.openTest(assessment, true); else if (exercise) navigationCallbacks.current.openExercise(exercise, true); else if (target) navigationCallbacks.current.openReal(target, true) } catch (reason) { setHistoryWarning((reason as Error).message) } }
    addEventListener('popstate', read); return () => removeEventListener('popstate', read)
  }, [workspaceId])
  const openNoteAnchor = async (selection: Selection) => {
    if (!session.course_ref) { setHistoryWarning('请先选择包含此笔记的教材。'); return }
    try { const target = await resolveAnchor(selection.ref, session.course_ref); openReal(target, true); if (noteState.dirty) setClosingNotes(true); else setDialog(null) } catch (reason) { setHistoryWarning((reason as Error).message) }
  }

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
  const loadFixture = () => { clearReaderLink(); set(old => ({ ...old, course_ref: fixtureRef(fixture.course.ref), expanded_keys: [...old.expanded_keys, `${fixture.course.id}:textbook:synthetic_chapter_1`] })); setDialog(null) }
  const navigate = (navigation: NavigationKey) => { if (!canLeave()) return; clearReaderLink(); set(old => { saveDirectory(workspaceId, old.course_ref?.id ?? null, old.navigation, old.directory_scroll); return { ...old, navigation, active_tab_id: null, directory_scroll: readDirectory(workspaceId, old.course_ref?.id ?? null, navigation) } }); setDrawer(null) }
  const toggleSide = (side: 'nav' | 'agent') => {
    if (side === 'nav' ? width < 820 : !desktop) { setDrawer(side); return }
    set(old => ({ ...old, [`${side}_collapsed`]: !old[`${side}_collapsed`] }))
  }
  const activateTab = (tab: typeof session.tabs[number]) => { if (!canLeave()) return; const assessment = assessmentTarget(tab.context); if (assessment) { openTest(assessment, tab.pinned); return }; const exercise = practiceTarget(tab.context); if (exercise) { openExercise(exercise, tab.pinned); return }; const target = contextTarget(tab.context, session.course_ref); if (target && !findLesson(tab.context.active_ref)) openReal(target, tab.pinned); else { clearReaderLink(); set(old => ({ ...old, active_tab_id: tab.id, course_ref: fixtureRef(fixture.course.ref) })) } }
  const closeTab = (id: string) => { if (practiceStatesRef.current[id]?.safe === false || assessmentStatesRef.current[id]?.safe === false) return; set(old => { const tabs = old.tabs.filter(tab => tab.id !== id); return { ...old, tabs, active_tab_id: old.active_tab_id === id ? tabs.at(-1)?.id ?? null : old.active_tab_id } }); setClosing(null) }
  const syntheticNav = <Navigation session={session} set={set} loaded={loaded} onOpen={openLesson} lastLesson={findLesson(readLastReading(workspaceId, fixture.course.id, 'textbook'))} onNavigate={navigate} onLoad={loadFixture} onAux={openAux} />
  const nav = subjectLocked || session.navigation === 'assessment' ? <AssessmentNavigation set={set} session={session} workspace={workspaceId} locked={policy.independentId} known={policy.known} open={openTest} resume={resumeTest} navigate={navigate} aux={openAux} selection={active && activeAssessment ? assessmentStates[active.id] : undefined} select={id => { if (active) setAssessmentQuestion(old => ({ tab: active.id, id, sequence: (old?.sequence ?? 0) + 1 })); setDrawer(null) }} /> : loaded ? syntheticNav : <CourseDirectory session={session} workspace={workspaceId} version={progressVersion} set={set} open={openReal} navigate={navigate} aux={openAux} loadSynthetic={loadFixture} practice={openExercise} practiceSelection={active && activePractice && practiceStates[active.id] ? { ref: activePractice.practice_ref, current: practiceStates[active.id].questionId, questions: practiceStates[active.id].questions, select: id => { setPracticeQuestion(old => ({ tab: active.id, id, sequence: (old?.sequence ?? 0) + 1 })); setDrawer(null) } } : undefined} />
  const reviewAccess = active && activeAssessment ? assessmentStates[active.id]?.reviewAccess : undefined
  const currentReview = reviewAccess?.access === getSessionGeneration() ? reviewAccess : undefined
  const tutorScope = active && activeAssessment ? (assessmentStates[active.id]?.status && assessmentStates[active.id]?.status !== 'active' ? currentReview?.policy?.tutor_scope : assessmentStates[active.id]?.policy?.tutor_scope) : undefined
  const tutor = subjectLocked || active && activeAssessment && tutorScope !== 'academic' ? <OperationHelp independent={!!policy.independentId} checking={!policy.known} /> : <Tutor review={currentReview?.context ?? undefined} practice={active ? practiceStates[active.id] : undefined} synthetic={!!activeLesson} context={active?.context ?? null} title={activeTitle} resolved={!!activeLesson || !!(active && realTitles[active.id]?.resolved)} baseDraft={draftBases[draftId] ?? null} storedDraft={draftStored[draftId] ?? ''} draft={drafts[draftId] ?? ''} onDraft={text => updateDraft(draftId, text)} conflicts={draftConflicts[draftId] ?? []} saving={!!draftSaving[draftId]} enabled={!!workspaceId && status !== 'connecting' && !draftResolving[draftId]} error={draftErrors[draftId] ?? draftErrors._storage ?? ''} choose={candidate => void chooseDraft(draftId, candidate)} />
  const commands = [
    { title: '打开对象', action: () => { setDialog('打开对象') } },
    { title: '开始练习', action: () => { setDialog(null); navigate('practice') } },
    ...['导入', '创建路线', '打开测试记录', '导出备份'].map(title => ({ title, action: () => { setDialog(null); openAux(title) } })),
    { title: '切换导航栏', action: () => { setDialog(null); toggleSide('nav') } },
    { title: '切换 Agent 栏', action: () => { setDialog(null); toggleSide('agent') } },
    { title: '切换专注模式', action: () => { setDialog(null); setFocus(!focus) } },
    { title: '查看快捷键', action: () => setDialog('快捷键') },
  ]
  return <div className={`app-shell ${focus ? 'focus-mode' : ''}`}>
    <a href="#reader-main" className="skip-link">跳到学习内容</a>
    <header className="topbar"><a className="brand" href="#" onClick={event => { event.preventDefault(); navigate('route') }}><span className="brand-symbol" aria-hidden="true">径</span><strong>知径</strong><span className="brand-subtitle">学习工作台</span></a><button className="command-trigger" onClick={() => setDialog('命令面板')}><span aria-hidden="true">⌕</span> 搜索与命令 <kbd>Ctrl ⇧ P</kbd></button><div className="topbar-tools"><button onClick={() => toggleSide('nav')} aria-label="切换导航栏" aria-expanded={width < 820 ? drawer === 'nav' : navVisible}>目录</button><button onClick={() => toggleSide('agent')} aria-label="切换 Agent 栏" aria-expanded={!desktop ? drawer === 'agent' : agentVisible}>Agent</button><button className="focus-trigger" onClick={() => setFocus(!focus)} aria-pressed={focus}>{focus ? '退出专注' : '专注'}</button><button className="import-trigger" onClick={() => openAux('导入')}>导入</button></div></header>
    {historyWarning && <div className="save-alert" role="status">{historyWarning}</div>}
    {error && <div className={`save-alert ${status === 'conflict' ? 'conflict' : ''}`} role="status"><span>{error}</span><button onClick={() => void reconnect(status === 'conflict')}>{status === 'conflict' ? '读取服务端会话，保留草稿' : '重试连接'}</button></div>}
    {status === 'conflict' && comparison && <ConflictComparison comparison={comparison} retainLocal={retainLocal} useServer={() => void reconnect(true)} />}
    {recoverable.length > 0 && <div className="save-alert" role="status"><span>发现其他窗口的待同步 UI 快照；原始快照保留。</span>{recoverable.map((snapshot, index) => <button key={snapshot.key} onClick={() => restorePending(snapshot)}>恢复待同步快照 {index + 1}</button>)}</div>}
    <div className="workbench-grid" style={{ '--nav-width': navVisible ? `${session.nav_width}px` : '0px', '--agent-width': agentVisible ? `${session.agent_width}px` : '0px', '--nav-divider': width >= 820 && !focus ? '6px' : '0px', '--agent-divider': desktop && !focus ? '6px' : '0px' } as CSSProperties}>
      <aside id="nav-pane" className="nav-pane" aria-label="课程导航" hidden={!navVisible}>{navVisible && nav}</aside>
      {width >= 820 && !focus ? <Splitter side="nav" value={session.nav_width} otherWidth={agentVisible ? session.agent_width : 0} collapsed={!navVisible} onResize={value => set(old => ({ ...old, nav_width: value }))} toggle={() => toggleSide('nav')} /> : <span />}
      <main id="reader-main" className="reader-main" tabIndex={-1}><div className="tab-bar" role="tablist" aria-label="打开的学习对象" onKeyDown={event => { if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return; const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("[role=tab]")); const current = tabs.indexOf(event.target as HTMLButtonElement); if (current < 0) return; event.preventDefault(); const index = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length; tabs[index].focus(); tabs[index].click() }}><button className={`home-tab ${!active ? 'active' : ''}`} role="tab" tabIndex={!active ? 0 : -1} aria-selected={!active} onClick={() => { if (!canLeave()) return; clearReaderLink(); set(old => ({ ...old, active_tab_id: null })) }}>{navigationItems.find(item => item.id === session.navigation)?.label}</button>{session.tabs.map(tab => <div className={`object-tab ${tab.id === active?.id ? 'active' : ''}`} key={tab.id}><button role="tab" tabIndex={tab.id === active?.id ? 0 : -1} aria-selected={tab.id === active?.id} title={tabLabel(tab)} onClick={() => activateTab(tab)} onDoubleClick={() => set(old => ({ ...old, tabs: old.tabs.map(item => item.id === tab.id ? { ...item, pinned: true } : item) }))}>{tab.pinned && <span aria-label="已固定">⌖ </span>}{tabLabel(tab)}{hasDraft(tab.id) && <span aria-label="有问题草稿"> •</span>}</button><button className="tab-pin" aria-label={`固定标签 ${tabLabel(tab)}`} onClick={() => set(old => ({ ...old, tabs: old.tabs.map(item => item.id === tab.id ? { ...item, pinned: !item.pinned } : item) }))}>{tab.pinned ? '⌖' : '⋄'}</button><button className="tab-close" aria-label={`关闭标签 ${tabLabel(tab)}`} onClick={() => hasDraft(tab.id) ? setClosing(tab.id) : closeTab(tab.id)}>×</button></div>)}</div>{readerLinkError ? <div className="reader-scroll"><div className="empty-content" role="alert"><h1>无法打开此精确链接</h1><p>{readerLinkError}</p><button onClick={() => { setReaderLinkError(''); if (active) activateTab(active); else clearReaderLink() }}>返回原标签</button></div></div> : subjectLocked && !activeAssessment || policy.independentId && activeAssessment?.attempt_id && activeAssessment.attempt_id !== policy.independentId ? <div className="reader-scroll"><div className="empty-content"><h1>{policy.known ? '独立测试期间，学科材料暂受限制' : '正在核验测试访问策略'}</h1><p>{policy.error || '可以从目录返回自己的测试，继续作答、提交或明确放弃。已有草稿保持独立保存。'}</p><button onClick={policy.refresh}>重新核验工作区策略</button></div></div> : activeAssessment && active && workspaceId ? activeAssessment.attempt_id ? <AssessmentView open={openTest} reader={subjectLocked ? undefined : openReal} course={subjectLocked ? undefined : chooseCourse} key={active.id} workspace={workspaceId} target={{ ...activeAssessment, attempt_id: activeAssessment.attempt_id }} tab={active} requestedQuestion={assessmentQuestion?.tab === active.id ? assessmentQuestion : undefined} loaded={(title, resolved) => setRealTitles(old => old[active.id]?.title === title && old[active.id]?.resolved === resolved ? old : { ...old, [active.id]: { title, resolved } })} onScroll={offset => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === active.id ? { ...tab, scroll_offset: offset } : tab) }))} onState={value => setAssessmentStates(old => JSON.stringify(old[active.id]) === JSON.stringify(value) ? old : { ...old, [active.id]: value })} /> : <AssessmentPreview course={chooseCourse} key={active.id} workspace={workspaceId} target={activeAssessment} open={openTest} loaded={(title, resolved) => setRealTitles(old => old[active.id]?.title === title && old[active.id]?.resolved === resolved ? old : { ...old, [active.id]: { title, resolved } })} /> : !active && session.navigation === 'assessment' ? <div className="reader-scroll"><div className="empty-content"><div className="eyebrow">测试</div><h1>选择测试，核对范围与模式</h1><p>从测试目录查看真实内容状态和最近作答记录。明确开始后才创建冻结实例；提交后可查看真实评分、历史版本与复盘。</p><button onClick={() => setDrawer('nav')}>打开测试目录</button></div></div> : activePractice && active && workspaceId ? activePractice.session_id ? <PracticeView requestedQuestion={practiceQuestion?.tab === active.id ? practiceQuestion : undefined} key={active.id} workspace={workspaceId} target={{ ...activePractice, session_id: activePractice.session_id }} tab={active} reader={openReal} loaded={(title, resolved) => setRealTitles(old => old[active.id]?.title === title && old[active.id]?.resolved === resolved ? old : { ...old, [active.id]: { title, resolved } })} onScroll={offset => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === active.id ? { ...tab, scroll_offset: offset } : tab) }))} onState={value => setPracticeStates(old => JSON.stringify(old[active.id]) === JSON.stringify(value) ? old : { ...old, [active.id]: value })} /> : <PracticePreview key={active.id} workspace={workspaceId} target={activePractice} open={openExercise} reader={openReal} loaded={(title, resolved) => setRealTitles(old => old[active.id]?.title === title && old[active.id]?.resolved === resolved ? old : { ...old, [active.id]: { title, resolved } })} /> : !active && session.navigation === 'practice' && !loaded ? <div className="reader-scroll"><div className="empty-content"><div className="eyebrow">习题</div><h1>选择习题，开始一次练习</h1><p>从左侧当前课程的习题目录选择参考题集。明确开始后才创建作答会话，参考解答保持隐藏。</p><button onClick={() => openAux('课程切换')}>选择课程</button></div></div> : loaded ? <Reader session={session} workspaceId={workspaceId} loaded={loaded} onLoad={loadFixture} onOpen={openLesson} onSelect={selection => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === old.active_tab_id ? { ...tab, context: { ...tab.context, selection } } : tab) }))} onScroll={offset => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === old.active_tab_id ? { ...tab, scroll_offset: offset } : tab) }))} onAux={openAux} /> : <ReaderDocument session={session} workspace={workspaceId} onOpen={openReal} onSelect={selection => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === old.active_tab_id ? { ...tab, context: { ...tab.context, selection } } : tab) }))} onScroll={offset => set(old => ({ ...old, tabs: old.tabs.map(tab => tab.id === old.active_tab_id ? { ...tab, scroll_offset: offset } : tab) }))} onNote={selection => { setNoteSelection(selection); setDialog('笔记') }} onLoaded={(title, resolved) => { if (active) setRealTitles(old => old[active.id]?.title === title && old[active.id]?.resolved === resolved ? old : { ...old, [active.id]: { title, resolved } }) }} progressVersion={progressVersion} progressChanged={() => setProgressVersion(value => value + 1)} onAux={openAux} loadSynthetic={loadFixture} practice={target => { setPracticeLesson(target); setDialog('本节习题') }} />}</main>
      {desktop && !focus ? <Splitter side="agent" value={session.agent_width} otherWidth={navVisible ? session.nav_width : 0} collapsed={!agentVisible} onResize={value => set(old => ({ ...old, agent_width: value }))} toggle={() => toggleSide('agent')} /> : <span />}
      <aside id="agent-pane" className="agent-pane" aria-label="Agent 助教" hidden={!agentVisible}>{agentVisible && tutor}</aside>
    </div>
    <footer className="statusbar" role="status"><span className={status === 'saved' ? 'saved' : ''}>{status === 'saved' ? '✓ UI 会话已保存' : status === 'saving' ? '会话保存中…' : status === 'connecting' ? '连接本机服务…' : status === 'conflict' ? '会话版本冲突' : '离线 · UI 待同步'}</span><span>{active ? `内容修订 ${active.context.active_ref.revision}` : '尚未选择对象'}</span><span>{policy.independentId ? '独立测试进行中 · 工作区材料受限' : activeAssessment ? assessmentStates[active?.id ?? '']?.summary ?? '测试预览 · 尚未开始' : activePractice ? practiceStates[active?.id ?? '']?.summary ?? '练习预览 · 未作答' : loaded ? '合成示例 · 无学习证据' : '正常学习'} · 本机</span></footer>
    {drawer && <Dialog title={drawer === 'nav' ? '课程目录' : 'Agent 助教'} className={`drawer drawer-${drawer}`} close={() => setDrawer(null)}>{drawer === 'nav' ? nav : tutor}</Dialog>}
    {dialog && <Dialog title={dialog} className={dialog === '导入' ? 'import-dialog' : dialog === '笔记' ? 'notes-dialog' : ''} close={closeDialog}>{subjectLocked && !['设置', '快捷键', '命令面板', '导入'].includes(dialog) ? <p>当前测试策略限制此材料与操作。已有草稿保留；请先返回测试并明确提交或放弃。</p> : dialog === '导入' ? workspaceId ? <ImportWorkflow key={workspaceId} workspaceId={workspaceId} paused={subjectLocked} close={() => setDialog(null)} openCourse={chooseCourse} /> : <p>工作区会话尚未连接。连接成功后可上传文件或恢复已有导入。</p> : dialog === '命令面板' ? <><label className="sr-only" htmlFor="command-search">筛选命令</label><input id="command-search" className="command-search" value={commandSearch} onChange={event => setCommandSearch(event.target.value)} placeholder="输入命令名称…" /><div className="command-list">{commands.filter(command => command.title.includes(commandSearch)).map(command => <button key={command.title} onClick={command.action}>{command.title}<span>↵</span></button>)}</div></> : dialog === '快捷键' ? <ul className="shortcut-list"><li>Ctrl / ⌘ + Shift + P：命令面板</li><li>分隔条：← / → 每次调整 16px</li><li>Home / End：到达宽度边界</li><li>Enter：折叠或恢复侧栏</li><li>Esc：关闭抽屉、对话框或退出专注</li><li>Tab / Shift + Tab：移动焦点</li></ul> : dialog === '笔记' ? workspaceId ? <NotesPanel workspace={workspaceId} selection={noteSelection} initialRefId={noteSelection?.ref.id ?? (active?.context.active_ref.entity === 'block' ? active.context.active_ref.id : undefined)} openAnchor={selection => void openNoteAnchor(selection)} onState={setNoteState} onSaved={() => setProgressVersion(value => value + 1)} /> : <p>请先连接本机会话。</p> : dialog === '本节习题' ? practiceLesson ? <LessonPracticeLinks target={practiceLesson} open={openExercise} /> : <p>请先打开真实教材小节。</p> : dialog === '教材修订' ? session.course_ref ? <CourseRevisions course={session.course_ref} choose={chooseCourse} /> : <p>请先选择教材。</p> : dialog === '课程切换' ? <CoursePicker choose={chooseCourse} loadSynthetic={loadFixture} /> : dialog === '打开对象' ? loaded ? <div className="command-list">{fixture.lessons.map(lesson => <button key={lesson.id} onClick={() => { openLesson(lesson, true); setDialog(null) }}>{lesson.title}</button>)}</div> : <CoursePicker choose={chooseCourse} loadSynthetic={loadFixture} /> : <><p>{auxiliaryText[dialog] ?? '此辅助能力尚未实现。'}</p><p className="muted">能力状态：未实现 · 没有执行业务写入。</p></>}</Dialog>}
    {closingNotes && <Dialog title="保留未同步笔记" close={() => setClosingNotes(false)}><p>笔记仍有未同步内容。可返回编辑并保存到服务端，或明确保留已保存的本机草稿后关闭。</p><button disabled={!noteState.safe} onClick={() => { setClosingNotes(false); setDialog(null) }}>保留本机笔记草稿并关闭</button><button onClick={() => setClosingNotes(false)}>返回编辑</button>{!noteState.safe && <p role="alert">本机草稿尚未安全保存，请保持窗口打开并重试。</p>}</Dialog>}
    {closing && (assessmentStates[closing]?.dirty || assessmentStates[closing]?.safe === false) ? <Dialog title="保留未同步测试作答" close={() => setClosing(null)}><p>测试仍有本机未同步候选。关闭不会提交或放弃，也不会修改冻结作答。</p><button disabled={!assessmentStates[closing]?.safe || draftSaving[closing] || !!draftErrors[closing]} onClick={() => closeTab(closing)}>保留本机测试作答并关闭</button><button onClick={() => setClosing(null)}>返回测试作答</button>{!assessmentStates[closing]?.safe && <p role="alert">本机候选尚未安全保存，请保持当前页面打开。</p>}</Dialog> : closing && (practiceStates[closing]?.dirty || practiceStates[closing]?.safe === false) ? <Dialog title="保留未同步作答" close={() => setClosing(null)}><p>本次练习仍有未同步作答。只有本机草稿已安全保存时才允许关闭；提交快照不会因此改变。</p><button disabled={!practiceStates[closing]?.safe || draftSaving[closing] || !!draftErrors[closing]} onClick={() => closeTab(closing)}>保留本机作答并关闭</button><button onClick={() => setClosing(null)}>返回练习</button>{!practiceStates[closing]?.safe && <p role="alert">本机作答尚未安全保存，请返回练习并重试。</p>}</Dialog> : closing && <Dialog title="保留问题草稿" close={() => setClosing(null)}><p>该对象有尚未发送的问题草稿。关闭标签前选择如何处理。</p><div className="dialog-actions"><button className="primary-button" disabled={draftSaving[closing] || !!draftErrors[closing]} onClick={() => closeTab(closing)}>保留本地草稿并关闭</button><button onClick={() => { updateDraft(closing, ''); closeTab(closing) }}>放弃草稿并关闭</button><button onClick={() => setClosing(null)}>取消</button></div></Dialog>}
  </div>
}
