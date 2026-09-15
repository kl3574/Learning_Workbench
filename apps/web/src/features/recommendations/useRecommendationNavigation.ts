import { useLayoutEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { RecommendationPage, RecommendationView } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { refKey, sameRef } from '../reader/target'
import { navigationRefs, validatePage, type RecommendationNavigation } from './recommendationModel'
export type RecommendationNavigationPort = { inspect: (id: string) => Promise<RecommendationPage> }
const sameOption = (a: RecommendationNavigation, b: RecommendationNavigation) => a.kind === b.kind && navigationRefs(a).map(refKey).join('|') === navigationRefs(b).map(refKey).join('|')
export function useRecommendationNavigation(workspace: string, paused: boolean, closeSafe: boolean, context: string, port: RecommendationNavigationPort, open: (option: RecommendationNavigation) => void) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = JSON.stringify([workspace, access, context]), scope = useRef({ owner, paused, closeSafe }); scope.current = { owner, paused, closeSafe }
  const callback = useRef(open); callback.current = open
  const epoch = useRef(0), [state, setState] = useState({ owner, busy: false, error: '', staleIds: [] as string[] })
  // Commit the guard epoch before an enabled button can be clicked. A passive
  // readiness effect could otherwise invalidate that first valid navigation.
  useLayoutEffect(() => { ++epoch.current; setState(old => ({ owner, busy: false, error: '', staleIds: old.owner === owner ? old.staleIds : [] })); return () => { ++epoch.current } }, [owner, paused, closeSafe])
  const navigate = async (item: RecommendationView, option: RecommendationNavigation) => {
    if (scope.current.paused || !scope.current.closeSafe || state.busy || item.staleness !== 'current') return
    const captured = owner, sequence = ++epoch.current
    const current = () => sequence === epoch.current && scope.current.owner === captured && !scope.current.paused && scope.current.closeSafe
    setState(old => ({ owner: captured, busy: true, error: '', staleIds: old.owner === captured ? old.staleIds : [] }))
    try {
      const page = validatePage(await port.inspect(item.id))
      if (!current()) return
      if (page.items.length !== 1 || page.items[0].id !== item.id) throw new Error('未读回原推荐的唯一身份，未打开其他对象。')
      const latest = page.items[0]
      if (page.projection_state !== 'ready' || latest.staleness !== 'current') { setState(old => ({ ...old, staleIds: [...new Set([...old.staleIds, item.id])] })); throw new Error('推荐依据已过期，请查看最新推荐。历史原因与精确引用仍可核对。') }
      const exact = latest.navigation_options.find(value => sameOption(value, option))
      if (!sameRef(latest.target_ref, item.target_ref) || !exact) throw new Error('原推荐目标或所选教材父链已变化，请重新核对，未猜测最新对象。')
      if (!current()) return
      callback.current(exact)
    } catch (reason) { if (current()) setState(old => ({ ...old, owner: captured, busy: false, error: `尚未打开推荐内容。${reason instanceof Error ? reason.message : ''}` })) }
    finally { if (current()) setState(old => ({ ...old, busy: false })) }
  }
  return { navigate, busy: !paused && state.owner === owner && state.busy, error: !paused && state.owner === owner ? state.error : '', staleIds: !paused && state.owner === owner ? state.staleIds : [] }
}
