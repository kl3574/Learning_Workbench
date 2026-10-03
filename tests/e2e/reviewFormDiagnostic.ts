import { writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import type { Page, TestInfo } from '../../apps/web/node_modules/@playwright/test'

// Used only by the original synthetic review-form-memory browser fixture, after
// its original assertion has failed. Never collect session tokens or commands.
export async function retainReviewFormDiagnostic(page: Page, info: TestInfo, draftId: string) {
  const pending = page.evaluate(async id => {
    const panel = document.querySelector('.review-panel')
    const dom = panel ? Array.from(panel.querySelectorAll<HTMLElement>('section[aria-label^="恢复的临时审核表单"]')).map(region => ({
      label: region.getAttribute('aria-label'), heading: region.querySelector('h4')?.textContent ?? null,
      fields: Array.from(region.querySelectorAll<HTMLTextAreaElement | HTMLSelectElement>('textarea,select')).map(field => ({ label: field.getAttribute('aria-label'), value: field.value, disabled: field.disabled })),
    })) : null
    const response = await fetch('/api/v1/session', { credentials: 'same-origin' })
    if (!response.ok) return { dom, memory: null, memory_state: 'permission_read_failed' }
    const session = await response.json()
    if (session.role !== 'author' || session.active_independent_attempt_id !== null || session.active_open_book_attempt_id !== null
      || typeof session.workspace_id !== 'string' || typeof session.actor_session_id !== 'string') return { dom, memory: null, memory_state: 'permission_not_confirmed' }
    const path = '/src/features/draftReview/reviewFormMemory.ts'
    const memory = await import(path)
    const forms = memory.originalReviewForms(session.workspace_id, 'import', session.actor_session_id) as {
      kind: 'create' | 'decision'; candidate: { draft_id: string; draft_revision: number; candidate_sha256: string }; value: object
    }[]
    return { dom, memory_state: 'fresh_original_actor_read', memory: forms.map(form => ({
      kind: form.kind, candidate: form.candidate, expected_draft: form.candidate.draft_id === id, value: form.value,
    })) }
  }, draftId)
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    const actual = await Promise.race([pending, new Promise<never>((_resolve, reject) => { timer = setTimeout(() => reject(new Error('diagnostic_timeout')), 1000) })])
    const serialized = JSON.stringify(actual)
    writeFileSync(info.outputPath('review-form-memory-diagnostic.json'), JSON.stringify({
      scope: 'After original assertion failure in an original synthetic fixture; DOM sampled before the fresh permission read and page memory afterward; these are distinct observations, not an atomic or earlier failure-time state. Fresh session values are not recorded. No automatic decision or form mutation.',
      draft_id: draftId, observed_at: new Date().toISOString(), observation_sha256: createHash('sha256').update(serialized).digest('hex'), observation: actual,
    }, null, 2))
  } catch {
    try { writeFileSync(info.outputPath('review-form-memory-diagnostic.json'), JSON.stringify({ scope: 'Synthetic fixture diagnostic only', draft_id: draftId, observation: null, state: 'unavailable_or_timeout' })) } catch { /* Keep the original assertion failure. */ }
  } finally { clearTimeout(timer) }
}
