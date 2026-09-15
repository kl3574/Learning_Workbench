import { request } from '../../api/client'
import type { DecisionPort } from './useDecisions'
import type { RecommendationListPort } from './useRecommendations'
import { validatePage } from './recommendationModel'
import type { RecommendationNavigationPort } from './useRecommendationNavigation'
export function strongIfMatch(sha256: string): string {
  if (!/^[a-f0-9]{64}$/.test(sha256)) throw new Error('推荐决定缺少已读回的强版本标签，未发送。')
  return `"${sha256}"`
}
async function inspect(id: string) { return validatePage(await request('GET /api/v1/recommendations', undefined, undefined, { query: { recommendation_id: id } })) }
export const recommendationClient: DecisionPort & RecommendationListPort & RecommendationNavigationPort = {
  inspect,
  list: async query => validatePage(await request('GET /api/v1/recommendations', undefined, undefined, { query: { ...query, limit: 20 } })),
  read: async id => {
    const page = await inspect(id)
    if (page.items.length !== 1 || page.items[0].id !== id) throw new Error('服务端没有读回原推荐的唯一历史身份，未替换成当前列表项。')
    return page.items[0]
  },
  save: value => request('POST /api/v1/recommendations/{id}/decision', { decision: value.fields.decision, reason: value.fields.reason }, { 'Idempotency-Key': value.command_id, 'If-Match': strongIfMatch(value.base.decision_sha256) }, { path: { id: value.base.id } }),
}
