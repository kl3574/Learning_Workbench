import type { ProfileWrite } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import type { ProfilePort } from './useProfile'
import type { ProfileEnvelope } from './profileDrafts'
export function profileWrite(value: ProfileEnvelope): ProfileWrite {
  const fields = value.fields
  if (!/^[1-9][0-9]*$/.test(fields.weekly_minutes) || Number(fields.weekly_minutes) > 10080 || !Number.isSafeInteger(Number(fields.weekly_minutes))) throw new Error('每周时间请填写 1–10080 的整数分钟，不使用空值或小数。')
  if (!fields.language.trim()) throw new Error('请填写学习语言。')
  return { ...fields, weekly_minutes: Number(fields.weekly_minutes), expected_revision: value.base.revision }
}
export const profileClient: ProfilePort = {
  read: () => request('GET /api/v1/learner/profile', undefined),
  save: value => request('PUT /api/v1/learner/profile', profileWrite(value), { 'Idempotency-Key': value.command_id }),
}
