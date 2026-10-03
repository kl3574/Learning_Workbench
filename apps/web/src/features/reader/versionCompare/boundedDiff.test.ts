import { expect, test } from 'vitest'
import { boundedLineDiff } from './boundedDiff'

test('compares exact lines without trimming Unicode, mathematical symbols or the final newline', () => {
  expect(boundedLineDiff('common\nα ≤ β\nend', 'common\nα < β\nend')).toEqual({ kind: 'diff', changes: [
    { kind: 'same', text: 'common\n' }, { kind: 'removed', text: 'α ≤ β\n' }, { kind: 'added', text: 'α < β\n' }, { kind: 'same', text: 'end' },
  ] })
  expect(boundedLineDiff('α\n', 'α')).toEqual({ kind: 'diff', changes: [{ kind: 'removed', text: 'α\n' }, { kind: 'added', text: 'α' }] })
})
test('bounded work falls back to original parallel text for either excessive characters or lines', () => {
  expect(boundedLineDiff('x'.repeat(100001), 'x').kind).toBe('parallel')
  expect(boundedLineDiff('x\n'.repeat(2001), 'y').kind).toBe('parallel')
})
