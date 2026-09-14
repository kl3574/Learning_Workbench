import { expect, test } from 'vitest'
import { emptySession, openTab } from './model'
import { preserveUntouchedSelections } from './selectionMerge'
const ref = { entity: 'block' as const, id: 'block_original', revision: 1, sha256: 'a'.repeat(64) }
const base = openTab(emptySession(), { view_kind: 'lesson', active_ref: ref, attached_refs: [], selection: null, attempt_id: null }, true, () => false)
const selection = { ref, exact_quote: '原创选区', prefix: '', suffix: '', start_codepoint: 0, end_codepoint: 4 }
const remote = { ...base, tabs: base.tabs.map(tab => ({ ...tab, context: { ...tab.context, selection } })) }
test('retaining projected layout preserves an untouched hidden original selection', () => { const merged = preserveUntouchedSelections({ ...base, nav_collapsed: true }, base, remote); expect(merged.nav_collapsed).toBe(true); expect(merged.tabs[0].context.selection).toEqual(selection); expect(base.tabs[0].context.selection).toBeNull() })
test('never transfers selection to a changed exact reference or fabricates an unknown baseline', () => { const changed = { ...base, tabs: base.tabs.map(tab => ({ ...tab, context: { ...tab.context, active_ref: { ...ref, sha256: 'b'.repeat(64) } } })) }; expect(preserveUntouchedSelections(changed, base, remote).tabs[0].context.selection).toBeNull(); expect(preserveUntouchedSelections(base, null, remote).tabs[0].context.selection).toBeNull() })
test('a deliberate full-view clear stays a clear', () => { expect(preserveUntouchedSelections(base, remote, remote).tabs[0].context.selection).toBeNull() })
