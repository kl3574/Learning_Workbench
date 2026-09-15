import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { LearningProgress } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { readRoutes, readRouteProgress, type RouteRecord } from './routeClient'
export function useRoutes(workspace: string | null, paused: boolean, version = 0) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const key = `${workspace}:${access}`, [refreshVersion, refresh] = useState(0)
  const [state, setState] = useState<{ key: string; records: RouteRecord[]; progress: LearningProgress | null; error: string; loading: boolean }>({ key: '', records: [], progress: null, error: '', loading: false })
  const epoch = useRef(0)
  useEffect(() => {
    const owner = ++epoch.current
    if (!workspace || paused) return
    setState({ key, records: [], progress: null, error: '', loading: true })
    void Promise.all([readRoutes(), readRouteProgress()]).then(([records, progress]) => { if (owner === epoch.current) setState({ key, records, progress, error: '', loading: false }) }).catch(reason => { if (owner === epoch.current) setState({ key, records: [], progress: null, error: reason instanceof Error ? reason.message : '路线尚未读回。', loading: false }) })
    return () => { ++epoch.current }
  }, [workspace, key, paused, version, refreshVersion])
  const visible = !paused && state.key === key
  return { records: visible ? state.records : [], progress: visible ? state.progress : null, error: visible ? state.error : '', loading: !paused && (!visible || state.loading), refresh: () => refresh(value => value + 1) }
}
