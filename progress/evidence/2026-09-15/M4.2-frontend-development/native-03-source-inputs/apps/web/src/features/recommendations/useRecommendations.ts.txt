import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { RecommendationPage } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { validatePage } from './recommendationModel'
export type RecommendationQuery = { course_id?: string; cursor?: string }
export type RecommendationListPort = { list: (query: RecommendationQuery) => Promise<RecommendationPage> }
export function useRecommendations(workspace: string, paused: boolean, course: string | undefined, port: RecommendationListPort) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = JSON.stringify([workspace, access, course ?? null]), current = useRef({ owner, paused }); current.current = { owner, paused }
  const [state, setState] = useState<{ owner: string; value: RecommendationPage | null; loading: boolean; error: string }>({ owner, value: null, loading: false, error: '' })
  const [version, setVersion] = useState(0), epoch = useRef(0)
  const visible = !paused && state.owner === owner ? state.value : null
  useEffect(() => {
    const sequence = ++epoch.current
    setState({ owner, value: null, loading: !paused, error: '' })
    if (!paused) void port.list({ ...(course ? { course_id: course } : {}) }).then(validatePage).then(value => {
      if (sequence === epoch.current && current.current.owner === owner && !current.current.paused) setState({ owner, value, loading: false, error: '' })
    }).catch(reason => {
      if (sequence === epoch.current && current.current.owner === owner && !current.current.paused) setState({ owner, value: null, loading: false, error: `推荐尚未读回。${reason instanceof Error ? reason.message : ''}` })
    })
    return () => { ++epoch.current }
  }, [owner, paused, port, course, version])
  const more = async () => {
    if (paused || state.loading || !visible?.next_cursor) return
    const sequence = ++epoch.current, previous = visible
    setState(old => ({ ...old, loading: true, error: '' }))
    try {
      const page = validatePage(await port.list({ ...(course ? { course_id: course } : {}), cursor: visible.next_cursor }))
      if (sequence !== epoch.current || current.current.owner !== owner || current.current.paused) return
      if (page.snapshot_id !== previous.snapshot_id || page.generated_at !== previous.generated_at || page.rule_version !== previous.rule_version || JSON.stringify(page.rule_parameters) !== JSON.stringify(previous.rule_parameters) || page.items.some(item => previous.items.some(old => old.id === item.id)) || page.next_cursor === previous.next_cursor) throw new Error('后续页不属于同一冻结批次或游标未推进，请重新读取。')
      const items = [...previous.items, ...page.items].map(item => page.projection_state === 'ready' ? item : { ...item, staleness: 'stale' as const })
      setState({ owner, value: { ...page, items }, loading: false, error: '' })
    } catch (reason) { if (sequence === epoch.current && current.current.owner === owner && !current.current.paused) setState({ owner, value: null, loading: false, error: `推荐分页尚未读回，请重新读取完整批次。${reason instanceof Error ? reason.message : ''}` }) }
  }
  return { value: visible, error: !paused && state.owner === owner ? state.error : '', loading: !paused && (state.owner !== owner || state.loading), refresh: () => setVersion(value => value + 1), more }
}
