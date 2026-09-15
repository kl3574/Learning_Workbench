import { afterEach, expect, test, vi } from 'vitest'
const request = vi.hoisted(() => vi.fn())
vi.mock('../../api/client', async original => ({ ...await original<typeof import('../../api/client')>(), request }))
import { recommendationClient, strongIfMatch } from './recommendationClient'
import { newDecision } from './decisionDrafts'
import { testPage, testRecommendation } from './testFixtures'
afterEach(() => request.mockReset())
test('transport preserves exact two-field body, original command key and decision strong hash on every replay', async () => {
  const item = testRecommendation(), value = newDecision(item, 'workspace_client', { decision: 'dismissed', reason: '原命令 🧠é' })
  request.mockResolvedValue({ id: item.id, revision: 2, applied: true })
  await recommendationClient.save(value); await recommendationClient.save(value)
  expect(request.mock.calls).toEqual(Array(2).fill(['POST /api/v1/recommendations/{id}/decision', { decision: 'dismissed', reason: '原命令 🧠é' }, { 'Idempotency-Key': value.command_id, 'If-Match': `"${item.decision_sha256}"` }, { path: { id: item.id } }]))
  for (const bad of ['*', `W/"${item.decision_sha256}"`, `"${item.decision_sha256}"`, `${item.decision_sha256},${item.decision_sha256}`, 'a'.repeat(63)]) expect(() => strongIfMatch(bad)).toThrow('强版本标签')
})
test('historical restoration reads only the exact recommendation id and refuses another list identity', async () => {
  const item = testRecommendation(); request.mockResolvedValue(testPage([item])); expect(await recommendationClient.read(item.id)).toEqual(item)
  expect(request).toHaveBeenLastCalledWith('GET /api/v1/recommendations', undefined, undefined, { query: { recommendation_id: item.id } })
  request.mockResolvedValue(testPage([testRecommendation('recommendation_other')])); await expect(recommendationClient.read(item.id)).rejects.toThrow('唯一历史身份')
})
