import { useRef, useState } from 'react'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import { DraftPreview } from './DraftPreview'
import { EncodingPreview } from './EncodingPreview'
import { FailedOriginal } from './FailedOriginal'
import { ReviewWarnings } from './ReviewWarnings'
import { UploadForm } from './UploadForm'
import { useImportWorkflow } from './useImportWorkflow'
import { validImportId } from './recovery'
import './imports.css'

const statusLabels = { staged: '原件已暂存', parsing: '正在解析', preview_ready: '预览已就绪，等待确认', committed: '已确认入库', cancelled: '已取消', failed: '导入失败' }
const jobLabels = { queued: '排队中', running: '运行中', awaiting_approval: '等待确认', completed: '任务已完成', failed: '任务失败', cancelled: '任务已取消' }

export function ImportWorkflow({ workspaceId, paused = false, close, openCourse }: { workspaceId: string; paused?: boolean; close: () => void; openCourse?: (ref: ContentRef) => void }) {
  const state = useImportWorkflow(workspaceId, paused)
  const [manualId, setManualId] = useState('')
  const snapshot = state.snapshot
  const blockers = snapshot?.warnings.some(warning => warning.severity === 'error') ?? false
  const warningsAccepted = snapshot?.warnings.filter(warning => warning.severity === 'warning').every(warning => state.accepted.includes(warning.code)) ?? false
  const mappingValid = state.mapping.every(item => validImportId(item.old_id) && validImportId(item.new_id))
    && new Set(state.mapping.map(item => item.old_id)).size === state.mapping.length
    && new Set(state.mapping.map(item => item.new_id)).size === state.mapping.length
  const courseRefs: ContentRef[] = state.result?.course_refs ?? (snapshot?.status === 'committed' && state.job?.status === 'completed' ? state.job.result_refs.filter(ref => ref.entity === 'course') : [])
  const activeTest = !!state.auth?.active_independent_attempt_id
  const canCommit = snapshot?.status === 'preview_ready' && !state.busy && !state.draftBusy && !!state.draft && !blockers && warningsAccepted && mappingValid && state.confirmed && !activeTest
  const suspended = paused || !state.accessReady
  const lastOperation = useRef<{ role: 'author' | 'learner' | null; status: keyof typeof statusLabels | null }>({ role: null, status: null })
  if (!suspended) lastOperation.current = { role: state.auth?.role ?? lastOperation.current.role, status: snapshot?.status ?? lastOperation.current.status }
  const operationRole = !state.roleChanging && state.auth ? state.auth.role : lastOperation.current.role
  return <div className="import-workflow">
    <UploadForm suspended={suspended || !!state.active} disabled={state.busy || !state.auth || activeTest} courses={state.courses} moreCourses={!!state.courseCursor} onMoreCourses={() => void state.loadCourses()} submit={state.upload} />
    {suspended ? <div role="status">{operationRole && <p>操作角色：{operationRole === 'author' ? '作者' : '学习者'}（上次确认，正在重新核验）</p>}{lastOperation.current.status && <p>上次确认的流程状态：<span>{statusLabels[lastOperation.current.status]}</span>；当前不能预览或确认。</p>}<p>正在核验导入访问权限。测试限制期间，材料预览与原件下载暂不可用。</p><p>当前导入记录、已选择的本机文件与未提交设置仍保留。权限恢复后会重新读取服务端内容。</p></div> : <>
    <div className="import-role"><span>操作角色：{state.auth ? state.auth.role === 'author' ? '作者' : '学习者' : '正在核对会话…'}</span><button disabled={!state.auth || state.busy || activeTest} onClick={() => void state.changeRole()}>{state.auth?.role === 'author' ? '切换为学习者角色' : '切换为作者角色'}</button></div>
    <p className="muted">含私有材料的学习包及原件需要作者角色；切换角色须由你明确操作。</p>
    {activeTest && <p role="alert" className="import-error">独立测试进行中，导入、预览与原件下载暂不可用。</p>}
    {state.error && <div className="import-error" role="alert"><p>{state.error}</p>{state.active ? <button disabled={state.busy} onClick={() => void state.retry()}>重试读取导入状态</button> : <button disabled={state.busy} onClick={() => void state.connect()}>重新连接导入服务</button>}</div>}
    {state.cacheError && <p className="import-warning" role="status">{state.cacheError}</p>}
    {state.busy && <p role="status">正在等待服务端响应…</p>}
    {!state.active && <>
      <details open={state.recovery.length > 0}><summary>恢复已有导入</summary><p className="muted">浏览器只保存任务 ID。原件、正文、警告和提交结果均从服务端重新读取。</p>
        {state.recovery.length > 0 && <div className="import-history">{state.recovery.map(item => <button key={item.importId} disabled={state.busy || !state.auth} onClick={() => void state.resume(item)}>恢复 {item.importId}</button>)}</div>}
        <div className="import-fields"><label>服务端导入 ID<input value={manualId} onChange={event => setManualId(event.target.value)} /></label></div>
        <button disabled={state.busy || !state.auth || !validImportId(manualId)} onClick={() => void state.resume({ importId: manualId })}>读取已有导入</button>
      </details>
    </>}
    {state.active && <>
      <dl className="import-details"><dt>导入 ID</dt><dd>{state.active.importId}</dd>{state.active.jobId && <><dt>任务 ID</dt><dd>{state.active.jobId}</dd></>}<dt>当前状态</dt><dd role="status">{snapshot ? statusLabels[snapshot.status] : '正在读取服务端状态'}</dd>{snapshot && <><dt>原件 SHA-256</dt><dd><code className="import-hash">{snapshot.input_sha256}</code></dd></>}</dl>
      {state.job && <div className="import-notice"><p>{jobLabels[state.job.status]} · {state.job.progress.label}</p>{state.job.progress.total !== null && state.job.progress.total > 0 ? <progress className="import-progress" max={state.job.progress.total} value={state.job.progress.completed} /> : state.job.status === 'running' ? <progress className="import-progress" /> : null}{state.job.error && <p className="import-error">{state.job.error.message}</p>}</div>}
      {snapshot?.status === 'preview_ready' && <>
        <h3>{snapshot.candidate_summary.course_title}</h3><p>候选包含 {snapshot.candidate_summary.lesson_count} 个小节、{snapshot.candidate_summary.block_count} 个内容块；未解析引用 {snapshot.candidate_summary.unresolved_refs.length}。</p>{snapshot.candidate_summary.unresolved_refs.length > 0 && <ul>{snapshot.candidate_summary.unresolved_refs.map(id => <li key={id}>{id}</li>)}</ul>}
        <ReviewWarnings warnings={snapshot.warnings} accepted={state.accepted} change={state.setAccepted} disabled={state.busy} />
        {snapshot.preview_refs.length > 0 ? <DraftPreview ids={snapshot.preview_refs} selected={state.selectedDraftId} draft={state.draft} source={state.source} sourceError={state.sourceError} accessEpoch={state.accessEpoch} loading={state.draftBusy} error={state.draftError} choose={id => void state.loadDraft(id)} /> : <p className="import-warning">服务端尚未提供可读取的候选，无法核对正文。</p>}
        <details><summary>确认对象 ID 映射</summary><p>仅填写你已核实的精确对象对应关系。留空表示不请求 ID 重映射；服务端仍会检查冲突和引用。</p><div className="import-mappings">{state.mapping.map((item, index) => <div className="import-mapping" key={index}><label>原对象 ID<input value={item.old_id} disabled={state.busy} onChange={event => state.setMapping(state.mapping.map((old, position) => position === index ? { ...old, old_id: event.target.value } : old))} /></label><label>新对象 ID<input value={item.new_id} disabled={state.busy} onChange={event => state.setMapping(state.mapping.map((old, position) => position === index ? { ...old, new_id: event.target.value } : old))} /></label><button disabled={state.busy} onClick={() => state.setMapping(state.mapping.filter((_, position) => position !== index))}>移除此映射</button></div>)}</div><div className="import-buttons"><button disabled={state.busy} onClick={() => state.setMapping([...state.mapping, { old_id: '', new_id: '' }])}>添加精确映射</button></div>{!mappingValid && <p className="import-error">ID 必须有效，且原 ID、新 ID 均不能重复。</p>}</details>
        <label className="import-confirm"><input type="checkbox" checked={state.confirmed} disabled={state.busy} onChange={event => state.setConfirmed(event.target.checked)} /><span>我已核对本次候选、警告和原件 SHA-256，确认按当前 ID 映射入库。导入不代表内容已经审校。</span></label>
        <div className="import-buttons"><button className="primary-button" disabled={!canCommit || !snapshot.preview_refs.length || !!state.draftError} onClick={() => void state.commit()}>确认导入当前候选</button></div>
      </>}
      {snapshot && snapshot.status !== 'preview_ready' && snapshot.warnings.length > 0 && <ReviewWarnings warnings={snapshot.warnings} accepted={state.accepted} change={state.setAccepted} disabled />}
      {snapshot?.status === 'failed' && snapshot.warnings.some(warning => warning.code === 'ENCODING_CHOICE_REQUIRED') && <EncodingPreview key={snapshot.id} originalFile={state.originalFile} onOriginalFile={state.rememberOriginalFile} expectedHash={snapshot.input_sha256} accessEpoch={state.accessEpoch} />}
      {snapshot?.status === 'failed' && !snapshot.warnings.some(warning => warning.code === 'ENCODING_CHOICE_REQUIRED') && <FailedOriginal key={snapshot.id} originalFile={state.originalFile} onOriginalFile={state.rememberOriginalFile} expectedHash={snapshot.input_sha256} accessEpoch={state.accessEpoch} />}
      {(snapshot?.status === 'committed' || state.result) && <div className="import-result" role="status"><h3>导入已提交</h3><p>以下为服务端返回的正式课程引用，可打开精确课程目录开始阅读。</p>{courseRefs.length ? <ul>{courseRefs.map(ref => <li key={`${ref.id}:${ref.revision}`}><strong>{state.committedCourses.find(course => course.id === ref.id && course.revision === ref.revision)?.title ?? ref.id}</strong><br />{ref.id} · 修订 {ref.revision}<code className="import-hash">{ref.sha256}</code>{openCourse && <button onClick={() => openCourse(ref)}>打开已导入课程</button>}</li>)}</ul> : <p>服务端确认已提交；当前恢复信息没有关联任务的课程引用。已保留导入状态，不会把暂存候选当成正式引用。</p>}{state.result && <p>迁移回执：{state.result.migration_receipt_id}</p>}<button onClick={close}>完成并关闭导入</button></div>}
      {snapshot?.status === 'cancelled' && <p className="import-notice">服务端已取消本次导入；没有通过取消操作删除正式课程。</p>}
      {snapshot?.status === 'failed' && <div className="import-warning"><p>失败任务已经终止，原件仍保留在服务端。请修正原件后重新上传。</p><button onClick={close}>关闭并更换原件</button></div>}
      {snapshot && !['committed', 'cancelled', 'failed'].includes(snapshot.status) && <div className="import-buttons"><button disabled={state.busy || activeTest} onClick={() => void state.cancel()}>取消本次导入</button></div>}
      <p className="muted">关闭窗口不会确认或取消任务。下次打开“导入”可从恢复记录继续。</p>
    </>}
    </>}
  </div>
}
