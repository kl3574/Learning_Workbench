import { request } from '../../api/client'
import type { ContentRef, Route } from '../../../../../packages/contracts/generated/types'
import type { PageRoute, RouteTargetBinding, LearningProgress } from '../../../../../packages/contracts/generated/api-types'
import { sameRef, refKey } from '../reader/target'
import { validateRoute } from './routeDrafts'
export type RouteRecord = { route: Route; ref: ContentRef; bindings: RouteTargetBinding[] }
export function routeRecords(page: PageRoute): RouteRecord[] {
  if (page.items.length !== page.item_refs.length) throw new Error('路线列表与精确引用数量不符，未采用该目录。')
  const expected: string[] = []
  const records = page.items.map((value, index) => {
    const route = validateRoute(value), ref = page.item_refs[index]
    if (ref.entity !== 'route' || ref.id !== route.id || ref.revision !== route.revision) throw new Error('路线内容与完整引用不符。')
    const bindings = route.steps.map(step => {
      const matches = page.targets.filter(item => sameRef(item.route_ref, ref) && item.step_id === step.id)
      if (matches.length !== 1 || !sameRef(matches[0].target_ref, step.target)) throw new Error('路线步骤缺少一致的精确目标绑定。')
      const binding = matches[0]; expected.push(`${refKey(ref)}:${step.id}`)
      for (const option of binding.navigation_options) {
        const target = option.kind === 'reader' ? option.block_ref ?? option.lesson_ref : option.kind === 'practice' ? option.practice_ref : option.assessment_ref
        if (!sameRef(target, step.target)) throw new Error('导航目标不对应此路线步骤，未打开其他对象。')
      }
      if (!!binding.navigation_options.length === !!binding.unresolved_reason) throw new Error('路线导航的解析状态不一致。')
      return binding
    })
    return { route, ref, bindings }
  })
  if (expected.length !== page.targets.length || new Set(expected).size !== expected.length) throw new Error('路线目录包含额外或重复步骤绑定。')
  return records
}
export async function readRoutes(): Promise<RouteRecord[]> {
  const records: RouteRecord[] = [], cursors = new Set<string>(); let cursor: string | null = null
  do {
    const page: PageRoute = await request('GET /api/v1/routes', undefined, undefined, { query: { limit: 100, ...(cursor ? { cursor } : {}) } })
    records.push(...routeRecords(page)); cursor = page.next_cursor
    if (cursor && cursors.has(cursor)) throw new Error('路线分页游标重复，请重新读取。')
    if (cursor) cursors.add(cursor)
  } while (cursor)
  if (new Set(records.map(item => refKey(item.ref))).size !== records.length) throw new Error('路线分页出现重复修订，请重新读取。')
  return records
}
export const readRouteProgress = (): Promise<LearningProgress> => request('GET /api/v1/learning/progress', undefined)
