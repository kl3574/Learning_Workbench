import { describe, expect, test } from 'vitest'
import type { AuthoringDraftView } from '../../../../../packages/contracts/generated/api-types'
import { checkedAuthoring } from './authoringCommands'

// Wire-contract fixture only; these synthetic hashes grant no owner authority.
const draft = (): AuthoringDraftView => ({
  owner: 'authoring', candidate: { draft_id: 'draft_synthetic', draft_revision: 1, entity: 'block', candidate_sha256: 'a'.repeat(64) },
  source_job_id: 'job_synthetic', state: 'draft', published_ref: null, base_ref: null, body_sha256: 'b'.repeat(64),
  payload: { version: 'worked-example-candidate-v1', kind: 'worked_example', title: '合成合同例题', body_markdown: '原文 2',
    symbols: [{ name: 'n', tex: 'n', domain: 'finite real', dimension: '1' }], declared_source_refs: [], numeric_plan: { version: 'finite-arithmetic-v1', seed: null, variables: [],
      assertions: [{ id: 'assertion_two', expression: '1+1', expected: 2, atol: 0, rtol: 0, unit: '1' }] } },
  validation: { schema: 'PASS', references: 'PASS', symbol_declarations: 'PASS', issues: [], mathematical: 'NOT_RUN', sources: 'NOT_RUN', independent_pedagogy: 'NOT_RUN' },
  numeric_check_ids: [], warnings: [],
})
const published = (): AuthoringDraftView => ({ ...draft(), state: 'published', published_ref: { entity: 'block', id: 'block_actual', revision: 1, sha256: 'c'.repeat(64) } })

describe('single authoring current publication contract', () => {
  test('accepts required draft/null and published/exact-block while preserving candidate bytes', () => {
    for (const value of [draft(), published()]) {
      const read = checkedAuthoring<AuthoringDraftView>('AuthoringDraftView', value)
      expect(read).toEqual(value)
      expect(read).not.toBe(value)
      expect(read.candidate).toEqual(draft().candidate)
      expect(read.payload).toEqual(draft().payload)
    }
  })

  test.each(['missing', 'published_null', 'draft_ref', 'non_block', 'candidate_ref', 'extra', 'ref_extra', 'boolean_revision'])('rejects %s without adapting old records', fault => {
    const value: Record<string, unknown> = structuredClone(published())
    if (fault === 'missing') delete value.published_ref
    if (fault === 'published_null') value.published_ref = null
    if (fault === 'draft_ref') value.state = 'draft'
    if (fault === 'non_block') (value.published_ref as Record<string, unknown>).entity = 'lesson'
    if (fault === 'candidate_ref') value.published_ref = value.candidate
    if (fault === 'extra') value.publication_receipt = 'unowned'
    if (fault === 'ref_extra') (value.published_ref as Record<string, unknown>).current = true
    if (fault === 'boolean_revision') (value.published_ref as Record<string, unknown>).revision = true
    const original = structuredClone(value)
    expect(() => checkedAuthoring('AuthoringDraftView', value)).toThrow()
    expect(value).toEqual(original)
  })

  test('does not silently repair an old draft response missing the new required field', () => {
    const value: Record<string, unknown> = draft()
    delete value.published_ref
    expect(() => checkedAuthoring('AuthoringDraftView', value)).toThrow()
    expect(value).not.toHaveProperty('published_ref')
  })
})
