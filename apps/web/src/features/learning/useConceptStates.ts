import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ConceptStateResponse } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, request, subscribeSessionAccess } from '../../api/client'
import { validateConceptStates } from './conceptModel'
export function useConceptStates(workspace: string | null, paused: boolean, courseId?: string, version = 0) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration), key = `${workspace}:${access}:${courseId ?? 'all'}`
  const [state, setState] = useState<{ key: string; value: ConceptStateResponse | null; error: string; loading: boolean }>({ key: '', value: null, error: '', loading: false }), [refreshVersion, refresh] = useState(0), epoch = useRef(0)
  useEffect(() => {
    const current = ++epoch.current
    if (!workspace || paused) return
    setState({ key, value: null, error: '', loading: true })
    void request('GET /api/v1/learning/concept-states', undefined, undefined, { query: courseId ? { course_id: courseId } : {} }).then(value => validateConceptStates(value)).then(value => { if (current === epoch.current) setState({ key, value, error: '', loading: false }) }).catch(reason => { if (current === epoch.current) setState({ key, value: null, error: reason instanceof Error ? reason.message : '概念状态尚未读回。', loading: false }) })
    return () => { ++epoch.current }
  }, [key, workspace, paused, courseId, version, refreshVersion])
  const visible = !paused && state.key === key
  return { value: visible ? state.value : null, error: visible ? state.error : '', loading: !paused && (!visible || state.loading), refresh: () => refresh(value => value + 1) }
}
