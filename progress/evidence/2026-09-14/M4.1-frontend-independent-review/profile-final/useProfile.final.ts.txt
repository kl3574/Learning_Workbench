import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { LearnerProfile } from '../../../../../packages/contracts/generated/types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { decodeProfileDraft, editProfileDraft, newProfileDraft, profileDirty, profileDraftKey, profileFields, profileStore, useProfileJournal, validateProfile, type ProfileEnvelope, type ProfileFields } from './profileDrafts'

export type ProfilePort = { read: () => Promise<LearnerProfile>; save: (value: ProfileEnvelope) => Promise<LearnerProfile> }
export function useProfile(workspace: string, paused: boolean, port: ProfilePort) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = `${workspace}:${access}`, scope = useRef({ workspace, owner, paused }); scope.current = { workspace, owner, paused }
  const journal = useProfileJournal(workspace)
  const [editor, setEditor] = useState<ProfileEnvelope | null>(null), live = useRef(editor); live.current = editor
  const [observed, setObserved] = useState<{ owner: string; profile: LearnerProfile } | null>(null)
  const [claimed, setClaimed] = useState(false), [conflict, setConflict] = useState(false)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const version = useRef(0), operation = useRef(0)
  const owns = (captured: string) => scope.current.owner === captured && !scope.current.paused
  const persist = (value: ProfileEnvelope) => { version.current++; live.current = value; setEditor(value); journal.save(value) }
  const record = journal.records[profileDraftKey]
  const candidates: { value: ProfileEnvelope; text: string }[] = []
  let decodeError = ''
  for (const raw of new Set(record ? [record.text, ...record.conflicts.map(item => item.text)] : [])) {
    try { const value = decodeProfileDraft(raw, workspace); if (profileDirty(value)) candidates.push({ value, text: raw }) } catch (reason) { decodeError = reason instanceof Error ? reason.message : '画像草稿无法读取，原数据保留。' }
  }
  const editorText = editor ? JSON.stringify(editor) : null
  const foreignTexts = new Set(candidates.filter(candidate => candidate.text !== editorText).map(candidate => candidate.text))
  // Entering an unchanged form is not an unsent user edit. Keep its stored
  // branch, but only actual competing edits require an explicit choice. A
  // newly observed primary from another page also requires that choice even
  // when this page had already entered edit mode.
  const needsRecovery = candidates.length > 0 && (!claimed || foreignTexts.size > 0)
  const remote = !paused && observed?.owner === owner ? observed.profile : null
  const conflicts = record?.conflicts.filter(item => foreignTexts.has(item.text)) ?? []
  const safe = journal.ready && !journal.unsafe && !decodeError && !journal.error
  const dirty = !!editor && profileDirty(editor) || candidates.length > 0

  const refresh = useCallback(async () => {
    if (scope.current.paused) return
    const captured = scope.current.owner, sequence = ++operation.current
    setBusy(true)
    try {
      const value = validateProfile(await port.read(), scope.current.workspace)
      if (!owns(captured) || sequence !== operation.current) return
      setObserved({ owner: captured, profile: value }); setError('')
      if (live.current && profileDirty(live.current)) setConflict(live.current.base.revision !== value.revision)
    } catch (reason) { if (owns(captured) && sequence === operation.current) setError(`画像尚未读回；已有本机候选保留。${reason instanceof Error ? reason.message : ''}`) }
    finally { if (owns(captured) && sequence === operation.current) setBusy(false) }
  }, [port])
  useEffect(() => { live.current = null; setEditor(null); setClaimed(false); setConflict(false); version.current++; ++operation.current; setObserved(null); setError('') }, [workspace])
  useEffect(() => { ++operation.current; setBusy(false); if (!paused) void refresh(); return () => { ++operation.current } }, [owner, paused, refresh])

  const begin = () => { if (!remote || paused || !journal.ready || needsRecovery || conflicts.length) return; setClaimed(true); persist(newProfileDraft(remote)); setConflict(false) }
  const edit = (fields: ProfileFields) => { if (!live.current || paused || busy || conflicts.length || needsRecovery) return; persist(editProfileDraft(live.current, fields)); setError('') }
  const restore = async (candidate: { value: ProfileEnvelope; text: string }) => {
    if (paused || busy || journal.saving) return
    const captured = owner, startingVersion = version.current, sequence = ++operation.current
    setBusy(true)
    try {
      const persisted = (await profileStore.load(workspace))[profileDraftKey]
      if (!persisted || ![persisted.text, ...persisted.conflicts.map(item => item.text)].includes(candidate.text)) throw new Error('该候选尚未从本机存储读回，请重试保存后再恢复。')
      const latest = validateProfile(await port.read(), workspace)
      if (!owns(captured) || sequence !== operation.current || version.current !== startingVersion) throw new Error('恢复期间归属或输入已变化；较新的输入与原候选均保留。')
      const value = record?.conflicts.length ? await journal.resolve(profileDraftKey, candidate.text) : decodeProfileDraft(candidate.text, workspace)
      if (!owns(captured) || sequence !== operation.current || version.current !== startingVersion) return
      live.current = value; setEditor(value); version.current++; setClaimed(true); setObserved({ owner: captured, profile: latest }); setConflict(value.base.revision !== latest.revision); setError('')
    } catch (reason) { if (owns(captured)) setError(reason instanceof Error ? reason.message : '恢复失败，原候选仍保留。') }
    finally { if (owns(captured) && sequence === operation.current) setBusy(false) }
  }
  const save = async () => {
    const candidate = live.current
    if (!candidate || !profileDirty(candidate) || paused || busy || !safe || needsRecovery || conflicts.length) return
    const captured = owner, sequence = ++operation.current
    setBusy(true); setError('')
    try {
      const stored = (await profileStore.load(workspace))[profileDraftKey]
      if (!stored || ![stored.text, ...stored.conflicts.map(item => item.text)].includes(JSON.stringify(candidate))) throw new Error('本次命令尚未持久化，不发送；请重试本机保存。')
      if (!owns(captured) || sequence !== operation.current) return
      const response = validateProfile(await port.save(candidate), workspace)
      const acknowledged = decodeProfileDraft(JSON.stringify({ ...candidate, acknowledged: response }), workspace)
      // Only the same command may acknowledge the current editing branch. A
      // newer candidate may already be durable after a policy refresh; routing
      // an old receipt through journal.save would silently replace that branch.
      // Superseded commands remain replayable with their original server key.
      if (scope.current.workspace === workspace && live.current?.command_id === candidate.command_id) {
        journal.save(acknowledged); live.current = acknowledged; setEditor(acknowledged); version.current++; setConflict(false)
      }
      if (!owns(captured) || sequence !== operation.current) return
      setObserved({ owner: captured, profile: response })
      setError('')
    } catch (reason) {
      if (!owns(captured) || sequence !== operation.current) return
      if (reason instanceof ApiError && reason.status === 412) {
        setConflict(true)
        setObserved(null)
        try { const current = validateProfile(await port.read(), workspace); if (owns(captured) && sequence === operation.current) setObserved({ owner: captured, profile: current }) } catch { /* An unknown remote remains explicit; do not manufacture a baseline. */ }
      }
      if (owns(captured)) setError(`画像尚未确认保存。原基准、候选与命令身份仍保留；可重试原命令。${reason instanceof Error ? reason.message : ''}`)
    } finally { if (owns(captured) && sequence === operation.current) setBusy(false) }
  }
  const rebase = (keepLocal: boolean) => {
    if (!remote || !live.current || paused || busy || !safe || conflicts.length || needsRecovery) return
    const value = newProfileDraft(remote)
    if (keepLocal) value.fields = structuredClone(live.current.fields)
    persist(value); setClaimed(true); setConflict(false); setError(keepLocal ? '已采用读回的服务端基准；请明确保存本页内容。' : '已采用服务端画像，本机其他候选仍保留。')
  }
  const retryLocal = () => { if (live.current) journal.save(live.current) }
  const displayed = !paused && (!editor || editor.workspace_id === workspace) ? editor ?? (remote ? newProfileDraft(remote) : null) : null
  return { editor: displayed, remote, begin, edit, refresh, restore, save, rebase, retryLocal, candidates, needsRecovery, conflicts, conflict, busy, dirty, safe, journal, error, decodeError, claimed, fields: displayed?.fields ?? null, saved: !!editor?.acknowledged || !editor && !!remote, changed: !!editor && JSON.stringify(editor.fields) !== JSON.stringify(profileFields(editor.acknowledged ?? editor.base)) }
}
