import { describe, expect, it } from 'vitest'
import { emptySession, tabIdentity } from '../../workbench/model'
import { readerContext, type ReaderTarget } from './target'
import { openReader } from './navigation'
const target: ReaderTarget = { course: { entity: 'course', id: 'course_one', revision: 1, sha256: 'a'.repeat(64) }, lesson: { entity: 'lesson', id: 'lesson_one', revision: 1, sha256: 'b'.repeat(64) }, block: { entity: 'block', id: 'block_one', revision: 1, sha256: 'c'.repeat(64) }, view: 'worked_example' }
describe('reader navigation preserves the specified tab identity and frozen references', () => {
  it.each(['course', 'lesson', 'block'] as const)('rejects a conflicting %s reference before touching original session', field => { const existing = openReader(emptySession(), target, true, () => true).session; const incoming = structuredClone(target); incoming[field]!.sha256 = 'd'.repeat(64); expect(tabIdentity(readerContext(incoming))).toBe(tabIdentity(readerContext(target))); const result = openReader(existing, incoming, true, () => true); expect(result.kind).toBe('conflict'); expect(result.session).toBe(existing); expect(result.session.course_ref).toEqual(target.course); expect(result.session.tabs).toHaveLength(1) })
  it('accepts equivalent key ordering and keeps a saved selection and zero position', () => { const initial = openReader(emptySession(), target, true, () => false).session; const reordered = { ...target, block: { sha256: target.block!.sha256, revision: 1, id: 'block_one', entity: 'block' as const } }; const result = openReader(initial, reordered, false, () => false); expect(result.kind).toBe('opened'); expect(result.session.tabs[0]).toEqual(initial.tabs[0]) })
})
