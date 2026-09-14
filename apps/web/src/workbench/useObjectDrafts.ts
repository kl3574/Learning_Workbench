import { useCallback, useEffect, useRef, useState } from 'react'
import { load, save, subscribe, type DraftRecord, type DraftConflict } from './DraftStore'
export function useObjectDrafts(workspace: string | null) {
  const [bases, setBases] = useState<Record<string, string | null>>({})
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [conflicts, setConflicts] = useState<Record<string, DraftConflict[]>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [resolving, setResolving] = useState<Record<string, boolean>>({})
  const selecting = useRef(new Set<string>())
  const records = useRef<Record<string, DraftRecord>>({})
  const queued = useRef(new Map<string, string>())
  const busy = useRef(new Set<string>())
  const preferredLocal = useRef(new Map<string, string>())
  const dirty = useRef(new Map<string, string>())
  const owner = useRef(workspace)
  owner.current = workspace
  const refresh = useCallback(async () => {
    if (!workspace) return
    try {
      const loaded = await load(workspace)
      if (owner.current !== workspace) return
      for (const [id, record] of Object.entries(loaded)) if (!busy.current.has(id) && !dirty.current.has(id)) records.current[id] = record
      setDrafts(old => ({ ...old, ...Object.fromEntries(Object.entries(loaded).filter(([id]) => !busy.current.has(id) && !dirty.current.has(id) && !preferredLocal.current.has(id)).map(([id, record]) => [id, record.text])) }))
      setConflicts(Object.fromEntries(Object.entries(loaded).map(([id, record]) => [id, record.conflicts])))
    } catch (error) { setErrors(old => ({ ...old, _storage: `无法读取本地草稿：${(error as Error).message}` })) }
  }, [workspace])
  useEffect(() => {
    records.current = {}; queued.current.clear(); busy.current.clear(); dirty.current.clear(); preferredLocal.current.clear(); setDrafts({}); setBases({}); setConflicts({}); setErrors({}); setSaving({})
    void refresh()
    if (workspace) return subscribe(workspace, () => { void refresh() })
  }, [workspace, refresh])
  useEffect(() => {
    const protect = (event: BeforeUnloadEvent) => { if (busy.current.size || queued.current.size || dirty.current.size) { event.preventDefault(); event.returnValue = '' } }
    addEventListener('beforeunload', protect); return () => removeEventListener('beforeunload', protect)
  }, [])
  const updateDraft = (id: string, text: string) => {
    if (selecting.current.has(id)) return
    dirty.current.set(id, text)
    setDrafts(old => ({ ...old, [id]: text }))
    if (!workspace) { setErrors(old => ({ ...old, [id]: '尚未确认工作区，草稿仅在当前页面内存中。建立本机会话后再保存。' })); return }
    queued.current.set(id, text)
    if (busy.current.has(id)) return
    busy.current.add(id); setSaving(old => ({ ...old, [id]: true }))
    void (async () => {
      try {
        while (queued.current.has(id) && owner.current === workspace) {
          const candidate = queued.current.get(id)!; queued.current.delete(id)
          const known = records.current[id]
          const expected = known?.conflicts.length ? 0 : known?.revision ?? 0
          const result = await save(workspace, id, candidate, expected)
          if (owner.current !== workspace) return
          records.current[id] = result.record
          setConflicts(old => ({ ...old, [id]: result.record.conflicts }))
          setErrors(old => ({ ...old, [id]: '' }))
          if (dirty.current.get(id) === candidate) dirty.current.delete(id)
          if (result.kind === 'conflict') {
            preferredLocal.current.set(id, candidate)
            if (!known?.conflicts.length) setBases(old => ({ ...old, [id]: known?.text ?? null }))
            // The conflict candidate was committed in the same IDB transaction.
            // Further typing remains another explicit candidate, never an implicit overwrite.
            if (queued.current.has(id)) {
              const newer = queued.current.get(id)!; queued.current.delete(id)
              const kept = await save(workspace, id, newer, expected)
              records.current[id] = kept.record; preferredLocal.current.set(id, newer); if (dirty.current.get(id) === newer) dirty.current.delete(id); setConflicts(old => ({ ...old, [id]: kept.record.conflicts }))
            }
            break
          }
        }
      } catch (error) { setErrors(old => ({ ...old, [id]: `草稿未能保存，文本保留在当前页面：${(error as Error).message}` })) }
      finally { busy.current.delete(id); setSaving(old => ({ ...old, [id]: false })) }
    })()
  }
  const chooseDraft = async (id: string, candidate: DraftConflict | null) => {
    if (!workspace || !records.current[id] || busy.current.has(id)) return
    selecting.current.add(id); busy.current.add(id); setResolving(old => ({ ...old, [id]: true }))
    const current = records.current[id]
    try {
      const result = await save(workspace, id, candidate?.text ?? current.text, current.revision, current.conflicts.map(conflict => conflict.id))
      if (owner.current !== workspace) return
      records.current[id] = result.record
      dirty.current.delete(id)
      if (result.kind === 'saved') preferredLocal.current.delete(id)
      else { preferredLocal.current.set(id, result.conflict.text); setBases(old => ({ ...old, [id]: current.text })) }
      setDrafts(old => ({ ...old, [id]: result.kind === 'saved' ? result.record.text : result.conflict.text }))
      setConflicts(old => ({ ...old, [id]: result.record.conflicts }))
      setErrors(old => ({ ...old, [id]: '' }))
    } catch (error) { if (owner.current === workspace) setErrors(old => ({ ...old, [id]: `冲突选择尚未保存：${(error as Error).message}` })) } finally { if (owner.current === workspace) { selecting.current.delete(id); busy.current.delete(id); setResolving(old => ({ ...old, [id]: false })) } }
  }
  return { drafts, updateDraft, draftConflicts: conflicts, draftSaving: saving, draftErrors: errors, draftResolving: resolving, draftBases: bases, draftStored: Object.fromEntries(Object.entries(records.current).map(([id, record]) => [id, record.text])), chooseDraft }
}
