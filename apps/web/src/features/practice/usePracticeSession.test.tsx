import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterAll, afterEach, beforeAll, beforeEach, expect, test, vi } from 'vitest'
import type { PracticeResponsesSaved, PracticeSession, PracticeSolution } from '../../../../../packages/contracts/generated/api-types'
import type { QuestionPublic, ResponseDraft, ResponsesWrite } from '../../../../../packages/contracts/generated/types'
import type { PracticeTarget } from './target'

// Real React lifecycle and DraftStore transactions over fake-indexeddb; HTTP is
// controlled here. These are not browser, API, or SQLite acceptance tests.
const transport = vi.hoisted(() => ({ call: vi.fn() }))
vi.mock('../../api/client', () => ({ request: (...args: unknown[]) => transport.call(...args), getSessionGeneration: () => 0, subscribeSessionAccess: () => () => {} }))

// Public golden data produced by tests.practice_fixtures.practice_fixture and
// the strict backend PracticeSession DTO. No private solution enters a session.
const frozenTarget: PracticeTarget = {
  practice_ref: { entity: 'practice_set', id: 'practice_hookreview', revision: 1, sha256: '43d738cf2bf0b9f9e2f594e6c400ecb0aff8ba157d5da3742249e8ba8537cf87' },
  lesson_ref: { entity: 'lesson', id: 'lesson_hookreview', revision: 1, sha256: '08b9055571475f935104bc66a659c1f609b6698820239c987047cfa2279e275c' },
  course_ref: { entity: 'course', id: 'course_hookreview', revision: 1, sha256: 'c2f0e49c3c7edbd4de9379cfb7de3e6bf3af3238558b7ac460dfba47cf01939e' },
}
const questions: QuestionPublic[] = [
  { schema_version: '3.0.0', id: 'question_hookreview_0', revision: 1, entity: 'question', kind: 'single_choice', stem_markdown: '选择 $2+3$ 的结果。', choices: [{ id: 'choice_four', text_markdown: '4' }, { id: 'choice_five', text_markdown: '5' }], concept_ids: ['concept_hookreview'], skill: 'recall', exposure_group: 'exposure_hookreview_0', max_score: 1, input_instructions: '选择一个选项；练习尚未评分。' },
  { schema_version: '3.0.0', id: 'question_hookreview_1', revision: 1, entity: 'question', kind: 'text_blank', stem_markdown: '等式 $a+b=b+a$ 表达加法的哪一种性质？', choices: [], concept_ids: ['concept_hookreview'], skill: 'recall', exposure_group: 'exposure_hookreview_1', max_score: 1, input_instructions: '填写性质的中文名称。' },
  { schema_version: '3.0.0', id: 'question_hookreview_2', revision: 1, entity: 'question', kind: 'numeric', stem_markdown: '路程为 $12\\,\\mathrm{m}$，时间为 $3\\,\\mathrm{s}$，求速率。', choices: [], concept_ids: ['concept_hookreview'], skill: 'compute', exposure_group: 'exposure_hookreview_2', max_score: 1, input_instructions: '填写速率数值，单位为 m/s。' },
  { schema_version: '3.0.0', id: 'question_hookreview_3', revision: 1, entity: 'question', kind: 'calculation', stem_markdown: '矩形两条边长分别为 $2\\,\\mathrm{m}$ 和 $3\\,\\mathrm{m}$，求面积并写步骤。', choices: [], concept_ids: ['concept_hookreview'], skill: 'compute', exposure_group: 'exposure_hookreview_3', max_score: 1, input_instructions: '填写面积数值和推导，单位为 m²。' },
  { schema_version: '3.0.0', id: 'question_hookreview_4', revision: 1, entity: 'question', kind: 'expression', stem_markdown: '已知实变量函数 $f(x)=x^2$，写出其导函数。', choices: [], concept_ids: ['concept_hookreview'], skill: 'derive', exposure_group: 'exposure_hookreview_4', max_score: 1, input_instructions: '填写表达式，并在步骤中说明适用范围。' },
]
const questionHashes = [
  'adb1a8cbb65f88b011573d73afa57ff425103eb525ff45899b55175dcba1d27f',
  '534732119f2f1c1e2434070ee08265341f6a58fff0123cf6acec68d4e553418c',
  'a894eae9803513f0110eee5b335bb675eb9d7458975b4d548b2ff0d966bc7358',
  'd5d5416497ab8fb2e525b455fc654c032536ecc7d791c994cbc45eeff29f8c09',
  '84f93e0dcbcd97689c3bb1248653171f2d49c7e937f3ac38e69943d2caac4db3',
]
function session(id: string): PracticeSession {
  return {
    id, revision: 1, practice_ref: structuredClone(frozenTarget.practice_ref),
    lesson_ref: structuredClone(frozenTarget.lesson_ref), questions: structuredClone(questions),
    responses: [], status: 'active', exposure_event_ids: [], assisted: false, results: null,
    assistance: questions.map(question => ({ question_id: question.id, highest_hint_level: 0, solution_revealed: false })),
  }
}
function submittedSession(): PracticeSession {
  return {
    ...session('practice_session_A'), revision: 2, status: 'submitted',
    results: questions.map((question, index) => ({
      question_ref: { entity: 'question', id: question.id, revision: question.revision, sha256: questionHashes[index] },
      score: null, max_score: question.max_score ?? 1, status: 'needs_review',
      feedback_markdown: 'Synthetic pending review', solution_markdown: null,
    })),
  }
}

let hooks: typeof import('./usePracticeSession')
let drafts: typeof import('./practiceDrafts')
let remotes: Record<string, PracticeSession>
let puts: { id: string; body: ResponsesWrite }[]
let gets: string[]
let customPut: ((id: string, body: ResponsesWrite) => Promise<PracticeResponsesSaved>) | null
let customMutation: ((route: string, id: string) => Promise<PracticeSolution>) | null
let workspace: string

beforeAll(async () => {
  // DraftStore captures indexedDB in its constructor, so install it before
  // importing either production hook (the HTTP mock is already hoisted).
  vi.stubGlobal('indexedDB', new IDBFactory())
  hooks = await import('./usePracticeSession')
  drafts = await import('./practiceDrafts')
})
beforeEach(() => {
  remotes = { practice_session_A: session('practice_session_A'), practice_session_B: session('practice_session_B') }
  puts = []; gets = []; customPut = null; customMutation = null
  workspace = `workspace_${crypto.randomUUID().replaceAll('-', '')}`
  transport.call.mockImplementation(async (route: string, body: ResponsesWrite, _headers: unknown, options: { path: { id: string } }) => {
    const id = options.path.id
    if (route === 'GET /api/v1/practice/sessions/{id}') {
      gets.push(id)
      return structuredClone(remotes[id])
    }
    if (route === 'PUT /api/v1/practice/sessions/{id}/responses') {
      puts.push({ id, body: structuredClone(body) })
      if (customPut) return customPut(id, body)
      return acceptResponses(id, body)
    }
    if (customMutation) return customMutation(route, id)
    throw new Error(`Unexpected controlled route: ${route}`)
  })
})
afterEach(async () => { cleanup(); await delay(30) })
afterAll(async () => { await drafts.practiceDraftStore.close(); vi.unstubAllGlobals() })

function acceptResponses(id: string, body: ResponsesWrite): PracticeResponsesSaved {
  const current = remotes[id]
  if (current.revision !== body.expected_revision) throw Object.assign(new Error('Synthetic CAS conflict'), { status: 412 })
  remotes[id] = { ...current, revision: current.revision + 1, responses: structuredClone(body.responses) }
  return { id, revision: remotes[id].revision, saved_at: '2026-09-14T00:00:00Z' }
}
const target = (id: string) => ({ ...frozenTarget, session_id: id })
const answer = (text: string): ResponseDraft => ({ question_id: questions[0].id, answer: text, steps_markdown: '' })
const delay = (milliseconds: number) => new Promise<void>(resolve => setTimeout(resolve, milliseconds))
async function mount(id = 'practice_session_A') {
  const hook = renderHook(({ id }) => hooks.usePracticeSession(workspace, target(id)), { initialProps: { id } })
  await waitFor(() => expect(hook.result.current.state).toBe('saved'))
  await waitFor(() => expect(hook.result.current.commandReady).toBe(true))
  return hook
}
async function edit(hook: Awaited<ReturnType<typeof mount>>, text: string) {
  act(() => hook.result.current.update(answer(text)))
  await waitFor(() => expect(hook.result.current.localSaving).toBe(false))
}
async function durableCandidate(id: string) {
  const local = await drafts.practiceDraftStore.load(workspace)
  return drafts.decodePracticeEnvelope(local[drafts.practiceKey(id)].text, workspace).candidate_responses
}
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(yes => { resolve = yes })
  return { promise, resolve }
}

// Shell renders PracticeView with key={active.id}; its tab identity includes the
// session. These first two cases defend hook reuse, which is a broader interface
// boundary than the normal production switch (unmount/remount, tested below).
test('same hook identity change does not rebind or auto-save unsent A responses to B', async () => {
  const hook = await mount()
  await edit(hook, 'A_ONLY_UNSENT')
  hook.rerender({ id: 'practice_session_B' })
  await waitFor(() => expect(hook.result.current.snapshot?.id).toBe('practice_session_B'))
  await act(async () => { await delay(650) }) // Past the 450 ms automatic-save timer.
  expect(remotes.practice_session_B.responses).toEqual([])
  expect(puts.filter(item => item.id === 'practice_session_B')).toHaveLength(0)
  expect((await durableCandidate('practice_session_A'))[0].answer).toBe('A_ONLY_UNSENT')
})

test('same hook identity change during a PUT reads B and ignores the late A acknowledgement', async () => {
  const hook = await mount()
  await edit(hook, 'A_PENDING')
  const gate = deferred<PracticeResponsesSaved>()
  customPut = () => gate.promise
  let completion: Promise<void> | undefined
  act(() => { completion = hook.result.current.save() })
  await waitFor(() => expect(puts).toHaveLength(1))
  hook.rerender({ id: 'practice_session_B' })
  await act(async () => {
    gate.resolve({ id: 'practice_session_A', revision: 2, saved_at: '2026-09-14T00:00:00Z' })
    await completion
  })
  await waitFor(() => expect(gets).toContain('practice_session_B'))
  expect(hook.result.current.snapshot?.id).toBe('practice_session_B')
})

test('412 preserves separate local and remote candidates and the durable local response', async () => {
  const hook = await mount()
  await edit(hook, 'MY_LOCAL')
  remotes.practice_session_A = { ...remotes.practice_session_A, revision: 2, responses: [answer('OTHER_PAGE')] }
  await act(async () => { await hook.result.current.save() })
  expect(hook.result.current.state).toBe('conflict')
  expect(hook.result.current.conflict?.local[0].answer).toBe('MY_LOCAL')
  expect(hook.result.current.conflict?.remote.responses[0].answer).toBe('OTHER_PAGE')
  expect((await durableCandidate('practice_session_A'))[0].answer).toBe('MY_LOCAL')
})

test('explicit keep-local after remote submission retains the draft without a response PUT', async () => {
  const hook = await mount()
  await edit(hook, 'LOCAL_AFTER_SUBMITTED')
  remotes.practice_session_A = submittedSession()
  await act(async () => { await hook.result.current.retry() })
  expect(hook.result.current.conflict).not.toBeNull()
  act(() => hook.result.current.resolveServer(true))
  expect(hook.result.current.responses[0].answer).toBe('LOCAL_AFTER_SUBMITTED')
  expect(hook.result.current.state).toBe('offline')
  await waitFor(() => expect(hook.result.current.localSaving).toBe(false))
  await act(async () => { await delay(500) })
  expect(puts).toHaveLength(0)
  expect((await durableCandidate('practice_session_A'))[0].answer).toBe('LOCAL_AFTER_SUBMITTED')
})

test('keyed unmount with PUT in flight keeps both sessions separate and recovers A on return', async () => {
  const a = await mount()
  await edit(a, 'A_DURABLE_BEFORE_LEAVING')
  const gate = deferred<void>()
  customPut = async (id, body) => {
    if (id === 'practice_session_A') await gate.promise
    return acceptResponses(id, body)
  }
  let completion: Promise<void> | undefined
  act(() => { completion = a.result.current.save() })
  await waitFor(() => expect(puts).toHaveLength(1))
  a.unmount()
  const b = await mount('practice_session_B')
  await edit(b, 'B_OWN_DURABLE')
  await act(async () => { await b.result.current.save() })
  await act(async () => { gate.resolve(); await completion })
  expect(b.result.current.responses[0].answer).toBe('B_OWN_DURABLE')
  expect(remotes.practice_session_A.responses[0].answer).toBe('A_DURABLE_BEFORE_LEAVING')
  expect(remotes.practice_session_B.responses[0].answer).toBe('B_OWN_DURABLE')
  b.unmount()
  const restored = renderHook(() => hooks.usePracticeSession(workspace, target('practice_session_A')))
  await waitFor(() => expect(restored.result.current.snapshot?.id).toBe('practice_session_A'))
  await waitFor(() => expect(restored.result.current.needsRecovery).toBe(true))
  const candidate = restored.result.current.storedEnvelope
  expect(candidate?.candidate_responses[0].answer).toBe('A_DURABLE_BEFORE_LEAVING')
  if (!candidate) throw new Error('Expected the durable A recovery candidate')
  await act(async () => { await restored.result.current.restore(candidate) })
  if (restored.result.current.conflict) act(() => restored.result.current.resolveServer(false))
  expect(restored.result.current.responses[0].answer).toBe('A_DURABLE_BEFORE_LEAVING')
  expect(puts.map(item => [item.id, item.body.responses[0].answer])).toEqual([
    ['practice_session_A', 'A_DURABLE_BEFORE_LEAVING'], ['practice_session_B', 'B_OWN_DURABLE'],
  ])
})

test('keyed unmount during reveal neither displays the late A solution in B nor preloads it on return', async () => {
  const a = await mount()
  const gate = deferred<void>()
  customMutation = async (route, id) => {
    expect(route).toBe('POST /api/v1/practice/sessions/{id}/solutions')
    await gate.promise
    const current = remotes[id]
    remotes[id] = {
      ...current, revision: 2, assisted: true, exposure_event_ids: ['event_synthetic_reveal'],
      assistance: current.assistance.map((item, index) => index === 0 ? { ...item, solution_revealed: true } : item),
    }
    return { solution_markdown: 'PRIVATE_A_REVEAL_ONLY', exposure_event_id: 'event_synthetic_reveal', revision: 2, review_status: 'needs_review' }
  }
  let completion: Promise<void> | undefined
  act(() => { completion = a.result.current.reveal(questions[0].id) })
  await waitFor(() => expect(a.result.current.busy).toBe(true))
  a.unmount()
  const b = await mount('practice_session_B')
  await act(async () => { gate.resolve(); await completion })
  expect(b.result.current.solutions).toEqual({})
  expect(b.result.current.snapshot?.id).toBe('practice_session_B')
  b.unmount()
  const restored = await mount()
  expect(restored.result.current.snapshot?.assistance[0].solution_revealed).toBe(true)
  expect(restored.result.current.solutions).toEqual({})
})
