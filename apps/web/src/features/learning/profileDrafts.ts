import type { LearnerProfile, SelfAssessment } from '../../../../../packages/contracts/generated/types'
import { DraftStore } from '../../workbench/DraftStore'
import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
import { validId } from '../assessment/target'

export type ProfileFields = {
  goals: string[]; goal_concept_ids: string[]; weekly_minutes: string; language: string
  preferred_difficulty: 'beginner' | 'intermediate' | 'advanced'
  self_assessments: { concept_id: string; level: SelfAssessment['level'] }[]
}
export type ProfileEnvelope = { version: 1; workspace_id: string; base: LearnerProfile; fields: ProfileFields; command_id: string; acknowledged: LearnerProfile | null }
const profileKeys = ['workspace_id', 'revision', 'goals', 'goal_concept_ids', 'weekly_minutes', 'language', 'preferred_difficulty', 'self_assessments']
const fieldKeys = profileKeys.slice(2)
const levels = ['not_learned', 'encountered', 'independent_use']
const difficulties = ['beginner', 'intermediate', 'advanced']
const object = (value: unknown): Record<string, unknown> => { if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('画像草稿结构无效，原记录仍保留。'); return value as Record<string, unknown> }
function keys(value: Record<string, unknown>, allowed: string[], required = allowed) { if (Object.keys(value).some(key => !allowed.includes(key)) || required.some(key => !(key in value))) throw new Error('画像草稿字段不匹配，原记录仍保留。') }
const text = (value: unknown): value is string => typeof value === 'string' && new TextDecoder().decode(new TextEncoder().encode(value)) === value
function ids(value: unknown) { if (!Array.isArray(value) || !value.every(validId) || new Set(value).size !== value.length) throw new Error('概念身份无效或重复，原候选仍保留。') }
function self(value: unknown, persisted: boolean) {
  if (!Array.isArray(value)) throw new Error('自报条目结构无效。')
  const seen = new Set<string>()
  for (const item of value) {
    const row = object(item); keys(row, persisted ? ['concept_id', 'level', 'origin', 'updated_at'] : ['concept_id', 'level'], persisted ? ['concept_id', 'level', 'updated_at'] : ['concept_id', 'level'])
    if (!validId(row.concept_id) || seen.has(row.concept_id) || !levels.includes(String(row.level))) throw new Error('自报概念或等级无效。')
    seen.add(row.concept_id)
    if (persisted && (row.origin !== undefined && row.origin !== 'self_report' || typeof row.updated_at !== 'string' || !/Z$/.test(row.updated_at) || !Number.isFinite(Date.parse(row.updated_at)))) throw new Error('自报来源或时间无效。')
  }
}
export function validateProfile(value: unknown, workspace: string): LearnerProfile {
  const row = object(value); keys(row, profileKeys, ['workspace_id', 'revision'])
  if (!validId(workspace) || row.workspace_id !== workspace || !Number.isSafeInteger(row.revision) || Number(row.revision) < 1) throw new Error('画像工作区或服务端修订无效。')
  if (row.goals !== undefined && (!Array.isArray(row.goals) || !row.goals.every(text))) throw new Error('学习目标无效。')
  if (row.goal_concept_ids !== undefined) ids(row.goal_concept_ids)
  if (row.weekly_minutes !== undefined && (!Number.isSafeInteger(row.weekly_minutes) || Number(row.weekly_minutes) < 1 || Number(row.weekly_minutes) > 10080)) throw new Error('每周学习时间无效。')
  if (row.language !== undefined && !text(row.language) || row.preferred_difficulty !== undefined && !difficulties.includes(String(row.preferred_difficulty))) throw new Error('语言或难度无效。')
  if (row.self_assessments !== undefined) self(row.self_assessments, true)
  return value as LearnerProfile
}
export function profileFields(value: LearnerProfile): ProfileFields { return { goals: [...(value.goals ?? [])], goal_concept_ids: [...(value.goal_concept_ids ?? [])], weekly_minutes: String(value.weekly_minutes ?? 120), language: value.language ?? 'zh-CN', preferred_difficulty: value.preferred_difficulty ?? 'beginner', self_assessments: (value.self_assessments ?? []).map(item => ({ concept_id: item.concept_id, level: item.level })) } }
export function decodeProfileDraft(raw: string, workspace: string): ProfileEnvelope {
  const row = object(JSON.parse(raw)); keys(row, ['version', 'workspace_id', 'base', 'fields', 'command_id', 'acknowledged'])
  if (row.version !== 1 || row.workspace_id !== workspace || !validId(row.command_id)) throw new Error('画像草稿归属或命令身份无效，未采用这份候选。')
  const base = validateProfile(row.base, workspace), fields = object(row.fields); keys(fields, fieldKeys)
  if (!Array.isArray(fields.goals) || !fields.goals.every(text) || !text(fields.weekly_minutes) || !text(fields.language) || !difficulties.includes(String(fields.preferred_difficulty))) throw new Error('画像编辑字段无效，原记录仍保留。')
  ids(fields.goal_concept_ids); self(fields.self_assessments, false)
  if (row.acknowledged !== null) {
    const ack = validateProfile(row.acknowledged, workspace)
    if (ack.revision !== base.revision + 1 || JSON.stringify(profileFields(ack)) !== JSON.stringify(fields)) throw new Error('画像保存回执不对应原命令，未标记为已保存。')
  }
  return row as unknown as ProfileEnvelope
}
export const profileDirty = (value: ProfileEnvelope) => value.acknowledged === null && JSON.stringify(value.fields) !== JSON.stringify(profileFields(value.base))
export const profileDraftKey = 'learner-profile'
export const profileStore = new DraftStore({ name: 'learning-workbench.profile-drafts.v1' })
export const useProfileJournal = createResponseDraftJournal({ store: profileStore, decode: decodeProfileDraft, dirty: profileDirty, key: () => profileDraftKey })
export function newProfileDraft(profile: LearnerProfile): ProfileEnvelope { return { version: 1, workspace_id: profile.workspace_id, base: structuredClone(profile), fields: profileFields(profile), command_id: `profile_${crypto.randomUUID()}`, acknowledged: null } }
export function editProfileDraft(value: ProfileEnvelope, fields: ProfileFields): ProfileEnvelope { return { ...value, base: structuredClone(value.acknowledged ?? value.base), fields: structuredClone(fields), command_id: `profile_${crypto.randomUUID()}`, acknowledged: null } }
