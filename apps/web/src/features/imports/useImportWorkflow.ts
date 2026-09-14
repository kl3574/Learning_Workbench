import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSessionGeneration, request, subscribeSessionAccess } from '../../api/client'
import type { ContentRef, Course } from '../../../../../packages/contracts/generated/types'
import type { CoursePage, DraftSnapshot, IdMapping, ImportCommit, ImportKind, ImportSnapshot, JobSnapshot, SessionSnapshot, SourceSnapshot } from './contracts'
import { recoverImports, rememberImport, type RecoveryId } from './recovery'

const parameters = (id: string) => ({ path: { id } })
const mutationHeaders = () => ({ 'Idempotency-Key': crypto.randomUUID() })
const message = (error: unknown) => error instanceof Error ? error.message : '服务请求未完成，请重试。'

export function useImportWorkflow(workspaceId: string, paused = false) {
  const accessVersion = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration)
  const [projectionVersion, setProjectionVersion] = useState(-1)
  const [roleChanging, setRoleChanging] = useState(false)
  const pausedRef = useRef(paused)
  pausedRef.current = paused
  const [auth, setAuth] = useState<SessionSnapshot | null>(null)
  const [courses, setCourses] = useState<CoursePage['items']>([])
  const [courseCursor, setCourseCursor] = useState<string | null>(null)
  const [recovery, setRecovery] = useState<RecoveryId[]>([])
  const [cacheError, setCacheError] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [active, setActive] = useState<RecoveryId | null>(null)
  const activeRef = useRef(active)
  activeRef.current = active
  const [snapshot, setSnapshot] = useState<ImportSnapshot | null>(null)
  const [job, setJob] = useState<JobSnapshot | null>(null)
  const [draft, setDraft] = useState<DraftSnapshot | null>(null)
  const [selectedDraftId, setSelectedDraftId] = useState('')
  const [draftBusy, setDraftBusy] = useState(false)
  const [draftError, setDraftError] = useState('')
  const [source, setSource] = useState<SourceSnapshot | null>(null)
  const [sourceError, setSourceError] = useState('')
  const [result, setResult] = useState<ImportCommit | null>(null)
  const [committedCourses, setCommittedCourses] = useState<Course[]>([])
  const [accepted, setAccepted] = useState<string[]>([])
  const [mapping, setMapping] = useState<IdMapping>([])
  const [confirmed, setConfirmed] = useState(false)
  const live = useRef(true)
  const taskGeneration = useRef(0)
  const draftGeneration = useRef(0)
  const accessEpoch = useRef(0)
  const mutation = useRef(false)
  // Files are retained only for this mounted dialog, never browser storage.
  const originalFiles = useRef(new Map<string, File>())

  const reloadRecovery = useCallback(() => {
    const value = recoverImports(workspaceId)
    setRecovery(value.ids)
    if (value.error) setCacheError(value.error)
  }, [workspaceId])

  const connect = useCallback(async () => {
    if (pausedRef.current) return false
    const generation = taskGeneration.current, access = getSessionGeneration()
    setError('')
    const [identity, page] = await Promise.allSettled([
      request('GET /api/v1/session', undefined),
      request('GET /api/v1/courses', undefined, undefined, { query: { limit: 100 } }),
    ])
    if (!live.current || pausedRef.current || generation !== taskGeneration.current || access !== getSessionGeneration()) return false
    if (identity.status === 'fulfilled') {
      if (identity.value.workspace_id !== workspaceId) { setAuth(null); setError('工作区会话已变化，请关闭导入并重新连接。'); return false }
      setAuth(identity.value)
    } else { setAuth(null); setError(message(identity.reason)); return false }
    if (page.status === 'fulfilled') { setCourses(page.value.items); setCourseCursor(page.value.next_cursor) }
    else setError(message(page.reason))
    return !identity.value.active_independent_attempt_id
  }, [workspaceId])

  useEffect(() => {
    live.current = true
    reloadRecovery()
    const listener = () => reloadRecovery()
    addEventListener('storage', listener)
    return () => { live.current = false; taskGeneration.current++; draftGeneration.current++; originalFiles.current.clear(); removeEventListener('storage', listener) }
  }, [reloadRecovery])

  const loadCourses = async () => {
    if (!courseCursor) return
    try {
      const page = await request('GET /api/v1/courses', undefined, undefined, { query: { limit: 100, cursor: courseCursor } })
      if (live.current) { setCourses(previous => [...previous, ...page.items.filter(item => !previous.some(old => old.ref.id === item.ref.id))]); setCourseCursor(page.next_cursor) }
    } catch (reason) { if (live.current) setError(message(reason)) }
  }

  const loadCommitted = useCallback(async (refs: ContentRef[], generation: number) => {
    const values = await Promise.all(refs.filter(ref => ref.entity === 'course').map(ref => request('GET /api/v1/courses/{id}', undefined, undefined, { path: { id: ref.id }, query: { revision: ref.revision } })))
    if (live.current && generation === taskGeneration.current) setCommittedCourses(values)
  }, [])

  const refresh = useCallback(async (selection: RecoveryId, generation: number) => {
    const value = await request('GET /api/v1/imports/{id}', undefined, undefined, parameters(selection.importId))
    if (!live.current || generation !== taskGeneration.current) return
    setSnapshot(value)
    const task = selection.jobId ? await request('GET /api/v1/jobs/{id}', undefined, undefined, parameters(selection.jobId)) : null
    if (!live.current || generation !== taskGeneration.current) return
    setJob(task)
    if (value.status === 'committed' && task?.status === 'completed') await loadCommitted(task.result_refs, generation)
  }, [loadCommitted])

  useEffect(() => {
    const generation = ++taskGeneration.current
    draftGeneration.current++; accessEpoch.current++
    setProjectionVersion(-1); setAuth(null); setCourses([]); setCourseCursor(null)
    setSnapshot(null); setJob(null); setDraft(null); setSource(null); setSourceError(''); setSelectedDraftId('')
    setDraftError(''); setResult(null); setCommittedCourses([]); setError(''); setDraftBusy(false)
    if (paused) { setBusy(false); return }
    let current = true
    const valid = () => current && live.current && !pausedRef.current && generation === taskGeneration.current && accessVersion === getSessionGeneration()
    setBusy(true)
    void (async () => {
      try {
        const allowed = await connect()
        if (!valid()) return
        if (allowed && activeRef.current) await refresh(activeRef.current, generation)
      } catch (reason) { if (valid()) setError(message(reason)) }
      finally { if (valid()) { setBusy(false); setProjectionVersion(accessVersion) } }
    })()
    return () => { current = false }
  }, [paused, accessVersion, connect, refresh])

  const resume = async (selection: RecoveryId) => {
    if (pausedRef.current || mutation.current) return
    const generation = ++taskGeneration.current
    draftGeneration.current++
    setActive(selection); setSnapshot(null); setJob(null); setDraft(null); setSource(null); setSourceError(''); setSelectedDraftId('')
    setResult(null); setCommittedCourses([]); setAccepted([]); setMapping([]); setConfirmed(false); setError(''); setDraftError(''); setBusy(true)
    const warning = rememberImport(workspaceId, selection.importId, selection.jobId)
    if (warning) setCacheError(warning)
    reloadRecovery()
    try { await refresh(selection, generation) } catch (reason) { if (live.current && generation === taskGeneration.current) setError(message(reason)) }
    finally { if (live.current && generation === taskGeneration.current) setBusy(false) }
  }

  const retry = async () => {
    if (pausedRef.current || !active || mutation.current) return
    const generation = taskGeneration.current
    setError(''); setBusy(true)
    try { await refresh(active, generation) } catch (reason) { if (live.current && generation === taskGeneration.current) setError(message(reason)) }
    finally { if (live.current && generation === taskGeneration.current) setBusy(false) }
  }

  useEffect(() => {
    if (paused || projectionVersion !== accessVersion || !active || !snapshot || !['staged', 'parsing'].includes(snapshot.status) || error || busy) return
    const generation = taskGeneration.current
    const timer = setTimeout(() => {
      void refresh(active, generation).catch(reason => { if (live.current && generation === taskGeneration.current) setError(message(reason)) })
    }, 1200)
    return () => clearTimeout(timer)
  }, [active, snapshot, error, busy, refresh, paused, projectionVersion, accessVersion])

  const upload = async (file: File, kind: ImportKind, targetCourseId: string) => {
    if (pausedRef.current || !auth || mutation.current) return
    mutation.current = true; setBusy(true); setError('')
    const generation = ++taskGeneration.current
    try {
      const response = await request('POST /api/v1/imports', { file, kind, ...(targetCourseId ? { target_course_id: targetCourseId } : {}) }, mutationHeaders())
      // Persist the server task ID even when the dialog closed during upload.
      const warning = rememberImport(workspaceId, response.import_id, response.job.id)
      if (!live.current) return
      originalFiles.current.set(response.import_id, file)
      if (warning) setCacheError(warning)
      if (generation !== taskGeneration.current || pausedRef.current) { setActive({ importId: response.import_id, jobId: response.job.id }); reloadRecovery(); setError('原件已暂存，但访问策略已经变化。请重新读取导入状态后继续。'); return }
      mutation.current = false
      await resume({ importId: response.import_id, jobId: response.job.id })
    } catch (reason) { if (live.current && generation === taskGeneration.current) setError(message(reason)) }
    finally { mutation.current = false; if (live.current) setBusy(false) }
  }

  const loadDraft = useCallback(async (id: string) => {
    if (pausedRef.current) return
    const generation = ++draftGeneration.current
    setSelectedDraftId(id); setDraft(null); setSource(null); setSourceError(''); setDraftError(''); setDraftBusy(true)
    try {
      const value = await request('GET /api/v1/drafts/{id}', undefined, undefined, parameters(id))
      if (!live.current || generation !== draftGeneration.current) return
      setDraft(value)
      if ('metadata' in value.payload && 'source_id' in value.payload) {
        try {
          const original = await request('GET /api/v1/sources/{id}', undefined, undefined, parameters(value.payload.source_id))
          if (live.current && generation === draftGeneration.current) setSource(original)
        } catch (reason) {
          // A private original is independently guarded; its safe candidate
          // remains readable and is not mislabeled as a failed draft request.
          if (live.current && generation === draftGeneration.current) setSourceError(message(reason))
        }
      }
    } catch (reason) { if (live.current && generation === draftGeneration.current) setDraftError(message(reason)) }
    finally { if (live.current && generation === draftGeneration.current) setDraftBusy(false) }
  }, [])

  useEffect(() => {
    if (!paused && projectionVersion === accessVersion && snapshot?.status === 'preview_ready' && snapshot.preview_refs.length && !selectedDraftId) void loadDraft(snapshot.preview_refs[0])
  }, [snapshot, selectedDraftId, loadDraft, paused, projectionVersion, accessVersion])

  const changeRole = async () => {
    if (pausedRef.current || !auth || mutation.current) return
    mutation.current = true; setRoleChanging(true); setBusy(true); setError('')
    try {
      // The shared access generation invalidates every mounted projection.
      // Its effect re-reads this same import ID after the server role changes.
      await request('POST /api/v1/session/role', { role: auth.role === 'author' ? 'learner' : 'author' }, mutationHeaders())
    } catch (reason) { if (live.current) setError(message(reason)) }
    finally { mutation.current = false; if (live.current) setRoleChanging(false) }
  }

  const commit = async () => {
    if (!snapshot || snapshot.status !== 'preview_ready' || mutation.current || !confirmed) return
    mutation.current = true; setBusy(true); setError('')
    const generation = taskGeneration.current
    try {
      const value = await request('POST /api/v1/imports/{id}/commit', { expected_input_sha256: snapshot.input_sha256, accepted_warning_codes: accepted, id_mapping: mapping }, mutationHeaders(), parameters(snapshot.id))
      if (!live.current || generation !== taskGeneration.current) return
      setResult(value)
      await loadCommitted(value.course_refs, generation)
      if (active) await refresh(active, generation)
    } catch (reason) { if (live.current && generation === taskGeneration.current) setError(message(reason)) }
    finally { mutation.current = false; if (live.current && generation === taskGeneration.current) setBusy(false) }
  }

  const cancel = async () => {
    if (!snapshot || mutation.current) return
    mutation.current = true; setBusy(true); setError('')
    const generation = taskGeneration.current
    try {
      await request('POST /api/v1/imports/{id}/cancel', { expected_input_sha256: snapshot.input_sha256 }, mutationHeaders(), parameters(snapshot.id))
      if (active) await refresh(active, generation)
    } catch (reason) { if (live.current && generation === taskGeneration.current) setError(message(reason)) }
    finally { mutation.current = false; if (live.current && generation === taskGeneration.current) setBusy(false) }
  }

  const rememberOriginalFile = (file: File | null) => {
    const id = activeRef.current?.importId
    if (!id) return
    if (file) originalFiles.current.set(id, file)
    else originalFiles.current.delete(id)
  }

  return { rememberOriginalFile, auth, roleChanging, accessReady: !paused && !auth?.active_independent_attempt_id && !roleChanging && projectionVersion === accessVersion, accessEpoch, originalFile: active ? originalFiles.current.get(active.importId) ?? null : null, connect, courses, courseCursor, loadCourses, recovery, cacheError, error, busy, active, snapshot, job, draft, source, sourceError, selectedDraftId, draftBusy, draftError, result, committedCourses, accepted, setAccepted, mapping, setMapping, confirmed, setConfirmed, upload, resume, retry, loadDraft, changeRole, commit, cancel }
}
