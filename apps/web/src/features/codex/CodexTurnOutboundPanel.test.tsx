import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { request } from '../../api/client'
import { actor, deferred, session, workspace } from './bootstrapTestFixtures'
import { CodexTurnOutboundPanel } from './CodexTurnOutboundPanel'
import { CodexTurnPanel } from './CodexTurnPanel'
import { turnOutboundClient, type TurnOutboundPort } from './turnOutboundClient'
import { outboundConsent, outboundControl, outboundCurrent, outboundGrant, outboundPreparation, outboundProposal, outboundProvider } from './turnOutboundFixtures'
import { readOutboundCommand, type OutboundCommand } from './turnOutboundCommands'
import { heldOutboundCommands, heldOutboundForms, releaseOutboundCommand, releaseOutboundForm } from './turnOutboundMemory'
import { emptyOutboundFields, persistOutboundForm, snapshotOutboundForm } from './turnOutboundForms'
const stores: DraftStore[] = []
const local = () => { const value = new DraftStore({ name: `outbound-panel-${crypto.randomUUID()}`, factory: new IDBFactory() }); stores.push(value); return value }
beforeEach(() => { vi.useFakeTimers({ toFake: ['Date'] }); vi.setSystemTime(new Date('2026-10-04T00:00:01Z')) })
afterEach(async () => { cleanup(); for (const w of [workspace, 'workspace_other']) { heldOutboundCommands(w).forEach(releaseOutboundCommand); heldOutboundForms(w).forEach(releaseOutboundForm) }; await Promise.all(stores.splice(0).map(v => v.close())); vi.unstubAllGlobals(); vi.useRealTimers() })
const port = (): TurnOutboundPort => ({ ...turnOutboundClient, session: vi.fn(async () => session()), current: vi.fn(async () => outboundCurrent()), preparation: vi.fn(async () => outboundPreparation()),
 control: vi.fn(async () => outboundControl()), config: vi.fn(async () => outboundProvider()), proposal: vi.fn(async () => outboundProposal()), consent: vi.fn(async () => outboundConsent()) })
const buttons = { preview: '明确创建完整外发预览', grant: '明确批准当前完整外发提案', revoke: '明确撤销本回合外发许可', start: '明确开始本回合' }
const response = (kind: OutboundCommand['kind']) => kind === 'preview' ? outboundProposal() : kind === 'grant' ? outboundGrant() : kind === 'revoke' ? { id: 'codexconsent_original', revision: 2, applied: true } : { turn_id: 'turn_test', session_revision: 4, job: { id: 'job_turn_test', status: 'queued' } }
const refresh = async () => { fireEvent.click(screen.getByText('读取外发记录与权限')); await screen.findByText(/外发本机记录已读取/) }
async function prepare(kind: OutboundCommand['kind']) {
 await refresh()
 fireEvent.change(screen.getByLabelText('外发回合 ID'), { target: { value: 'turn_test' } })
 if (kind === 'revoke') { fireEvent.click(screen.getByText('读取外发安全控制')); await screen.findByLabelText('外发安全控制原基准') }
 else {
  for (const [label, value] of [['原准备 ID', 'turn_preparation_test'], ['外发 session ID', 'codex_session_test'], ['外发 proposal ID', 'proposal_turn'], ['外发 consent ID', 'codexconsent_original'], ['完整输入 token 硬上限', '1000'], ['输出 token 硬上限', '100'], ['明确到期 UTC（未来十分钟内）', '2026-10-04T00:10:00Z']]) fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByText('读取准备、Job 与 Provider 基准')); await screen.findByLabelText('外发准备只读基准')
  if (kind === 'grant') { fireEvent.click(screen.getByText('独立读取当前外发提案')); await screen.findByLabelText('当前外发提案') }
  if (kind === 'start') { fireEvent.click(screen.getByText('独立读取当前外发许可')); await screen.findByLabelText('当前外发许可'); fireEvent.click(screen.getByText('独立读取开始 session 基准')); await screen.findByLabelText('开始 session 原基准') }
 }
 await waitFor(() => expect((screen.getByText(buttons[kind]) as HTMLButtonElement).disabled).toBe(false))
}

test.each(['preview', 'grant', 'revoke', 'start'] as const)('%s full HTTP wire survives lost ACK, remount with zero POST, explicit original replay and durable ACK reload', async kind => {
 const p = port(), store = local(), formStore = local(), posts: Array<{ path: string; key: string; body: string }> = []
 const fetch = vi.fn(async (path: string, init: RequestInit) => {
  const key = new Headers(init.headers).get('Idempotency-Key')!, original = readOutboundCommand((await store.load(workspace))[key], workspace)
  expect(original.actor_session_id).toBe(actor); expect(original.kind).toBe(kind); expect(original.ack).toBeNull(); expect(original.body).toEqual(JSON.parse(init.body as string))
  posts.push({ path, key, body: init.body as string })
  if (posts.length === 1) throw new Error('Synthetic lost original ACK')
  return new Response(JSON.stringify(response(kind)), { status: kind === 'start' ? 202 : kind === 'revoke' ? 200 : 201 })
 })
 vi.stubGlobal('fetch', fetch)
 let view = render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await prepare(kind); fireEvent.click(screen.getByText(buttons[kind])); await screen.findByText(/外发结果或本机保存未知/)
 const original = readOutboundCommand((await store.load(workspace))[posts[0].key], workspace)
 view.unmount(); view = render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await refresh(); expect(posts).toHaveLength(1)
 fireEvent.click(screen.getByText(`显式回放外发原 key ${original.command_id}`)); await screen.findByText(new RegExp(`外发 ${kind} 原 ACK 已保存`))
 expect(posts).toEqual([posts[0], posts[0]])
 expect(readOutboundCommand((await store.load(workspace))[original.command_id], workspace)).toEqual({ ...original, ack: response(kind) })
 view.unmount(); render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await refresh(); expect(posts).toHaveLength(2); expect(screen.getByText(`${kind} · 原 ACK 已保存，不是当前 GET`)).toBeTruthy()
 expect(screen.queryByLabelText('当前外发提案')).toBeNull(); expect(screen.queryByLabelText('当前外发许可')).toBeNull()
})

test.each(['preview', 'grant', 'revoke', 'start'] as const)('%s storage refusal keeps original command isolated and sends zero POST', async kind => {
 const p = port(), store = local(), formStore = local(), changed = vi.fn(), fetch = vi.fn()
 vi.stubGlobal('fetch', fetch); vi.spyOn(store, 'save').mockRejectedValue(new Error('Synthetic storage unavailable'))
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} onState={changed} />)
 await prepare(kind); fireEvent.click(screen.getByText(buttons[kind])); await screen.findByText(/外发结果或本机保存未知/)
 expect(fetch).not.toHaveBeenCalled(); expect(heldOutboundCommands(workspace)).toHaveLength(1)
 expect(heldOutboundCommands(workspace)[0].kind).toBe(kind); expect(changed).toHaveBeenLastCalledWith({ dirty: true, safe: false, isolated: true })
})

test.each(['workspace', 'port', 'store', 'admission', 'unmount'] as const)('late original grant ACK after %s change is retained under original actor and hidden', async change => {
 const p = port(), store = local(), formStore = local(), pending = deferred<Response>(), fetch = vi.fn(() => pending.promise)
 vi.stubGlobal('fetch', fetch)
 const view = render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await prepare('grant'); fireEvent.click(screen.getByText(buttons.grant)); await waitFor(() => expect(fetch).toHaveBeenCalledOnce())
 if (change === 'unmount') view.unmount()
 else view.rerender(<CodexTurnOutboundPanel workspace={change === 'workspace' ? 'workspace_other' : workspace} writeAdmitted={change !== 'admission'} port={change === 'port' ? port() : p} store={change === 'store' ? local() : store} formStore={formStore} />)
 await act(async () => pending.resolve(new Response(JSON.stringify(outboundGrant()), { status: 201 })))
 await waitFor(() => expect(heldOutboundCommands(workspace)[0]?.ack).toEqual(outboundGrant()))
 expect(heldOutboundCommands(workspace)[0].actor_session_id).toBe(actor); expect(screen.queryByText(/外发 grant 原 ACK 已保存/)).toBeNull(); expect(fetch).toHaveBeenCalledOnce()
})

test.each(['learner', 'independent', 'open_book'] as const)('fresh %s Policy after durable grant blocks POST and hides subject data while preserving original command', async mode => {
 const p = port(), store = local(), formStore = local(), save = store.save.bind(store), fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
 vi.spyOn(store, 'save').mockImplementation(async (...args) => { const value = await save(...args); vi.mocked(p.session).mockResolvedValue({ ...session(), role: mode === 'learner' ? 'learner' : 'author', active_independent_attempt_id: mode === 'independent' ? 'attempt_test' : null, active_open_book_attempt_id: mode === 'open_book' ? 'attempt_test' : null }); return value })
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await prepare('grant'); fireEvent.click(screen.getByText(buttons.grant)); await screen.findByText(/外发操作的当前权限或原 actor 已变化/)
 expect(fetch).not.toHaveBeenCalled(); expect(Object.keys(await store.load(workspace))).toHaveLength(1); expect(screen.queryByLabelText('当前外发提案')).toBeNull()
})

test('new learner with active assessment can revoke using actual safe control without reading subject details', async () => {
 const p = port(), store = local(), formStore = local()
 vi.mocked(p.session).mockResolvedValue({ ...session(), actor_session_id: 'learner_new', role: 'learner', active_independent_attempt_id: 'attempt_test' })
 const fetch = vi.fn(async () => new Response(JSON.stringify(response('revoke')), { status: 200 })); vi.stubGlobal('fetch', fetch)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted={false} port={p} store={store} formStore={formStore} />)
 await prepare('revoke'); fireEvent.click(screen.getByText(buttons.revoke)); await screen.findByText(/外发 revoke 原 ACK 已保存/)
 const original = Object.values(await store.load(workspace)).map(v => readOutboundCommand(v, workspace))[0]
 expect(original.actor_session_id).toBe('learner_new'); expect(original.ack).toEqual(response('revoke'))
 expect(p.preparation).not.toHaveBeenCalled(); expect(p.proposal).not.toHaveBeenCalled(); expect(p.consent).not.toHaveBeenCalled(); expect(fetch).toHaveBeenCalledOnce()
})

test('editing while a real preview is pending preserves the newer budget and original frozen request separately', async () => {
 const p = port(), store = local(), formStore = local(), pending = deferred<Response>(), fetch = vi.fn(() => pending.promise); vi.stubGlobal('fetch', fetch)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await prepare('preview'); fireEvent.click(screen.getByText(buttons.preview)); await waitFor(() => expect(fetch).toHaveBeenCalledOnce())
 fireEvent.change(screen.getByLabelText('完整输入 token 硬上限'), { target: { value: '2000' } })
 await act(async () => pending.resolve(new Response(JSON.stringify(outboundProposal()), { status: 201 }))); await screen.findByText(/外发 preview 原 ACK 已保存/)
 expect((screen.getByLabelText('完整输入 token 硬上限') as HTMLInputElement).value).toBe('2000')
 const command = Object.values(await store.load(workspace)).map(v => readOutboundCommand(v, workspace))[0]
 if (command.kind !== 'preview') throw new Error('Expected preview')
 expect(command.body.budget.max_input_tokens).toBe(1000)
})

test.each([412, 409, 503])('real HTTP %s preserves original body/key/basis and only explicit replay can send again', async status => {
 const p = port(), store = local(), formStore = local(), posts: Array<{ key: string; body: string }> = []
 const code = status === 503 ? 'CODEX_INPUT_PROOF_UNAVAILABLE' : 'CODEX_SOURCE_CHANGED'
 vi.stubGlobal('fetch', vi.fn(async (_path: string, init: RequestInit) => { posts.push({ key: new Headers(init.headers).get('Idempotency-Key')!, body: init.body as string }); return new Response(JSON.stringify({ error: { code, message: 'private synthetic diagnostic must stay hidden' } }), { status }) }))
 let view = render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await prepare('preview'); fireEvent.click(screen.getByText(buttons.preview)); await screen.findByText(status === 412 ? /外发版本已变化/ : status === 409 ? /外发绑定冲突/ : /BLOCKED：CODEX_INPUT_PROOF_UNAVAILABLE/)
 const original = readOutboundCommand((await store.load(workspace))[posts[0].key], workspace)
 expect(original.error).toEqual({ status, code }); expect(screen.queryByText(/private synthetic diagnostic/)).toBeNull()
 fireEvent.change(screen.getByLabelText('完整输入 token 硬上限'), { target: { value: '2000' } })
 view.unmount(); view = render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await refresh(); expect(posts).toHaveLength(1)
 fireEvent.click(screen.getByText(`显式回放外发原 key ${original.command_id}`)); await waitFor(() => expect(posts).toHaveLength(2)); await screen.findByText(status === 412 ? /外发版本已变化/ : status === 409 ? /外发绑定冲突/ : /BLOCKED：CODEX_INPUT_PROOF_UNAVAILABLE/)
 expect(posts[1]).toEqual(posts[0]); expect(readOutboundCommand((await store.load(workspace))[original.command_id], workspace)).toEqual(original)
})

test.each(['actor', 'workspace', 'learner', 'independent', 'open_book'] as const)('restore fresh %s change without a page notification never shows an old form or saves a new branch', async change => {
 const p = port(), store = local(), formStore = local(), original = snapshotOutboundForm(workspace, actor, { ...emptyOutboundFields(), preparation_id: 'original_private_preparation', max_input_tokens: '1234' }, null), fetch = vi.fn()
 await persistOutboundForm(original, formStore); vi.stubGlobal('fetch', fetch)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />)
 await refresh()
 vi.mocked(p.session).mockResolvedValue({ ...session(), actor_session_id: change === 'actor' ? 'other_actor' : actor, workspace_id: change === 'workspace' ? 'workspace_other' : workspace,
  role: change === 'learner' ? 'learner' : 'author', active_independent_attempt_id: change === 'independent' ? 'attempt_test' : null, active_open_book_attempt_id: change === 'open_book' ? 'attempt_test' : null })
 fireEvent.click(screen.getByText(`恢复外发表单 ${original.draft_id} · 1`)); await screen.findByText(/外发操作的当前权限或原 actor 已变化/)
 expect(screen.queryByDisplayValue('original_private_preparation')).toBeNull(); expect(screen.queryByDisplayValue('1234')).toBeNull()
 expect(Object.values(await formStore.load(workspace)).map(v => JSON.parse(v.text))).toEqual([original]); expect(fetch).not.toHaveBeenCalled()
})

test('restore rechecks identity after local read; an unnotified actor change leaves the original form intact', async () => {
 const p = port(), store = local(), formStore = local(), original = snapshotOutboundForm(workspace, actor, { ...emptyOutboundFields(), preparation_id: 'private_original' }, null)
 await persistOutboundForm(original, formStore)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await refresh()
 const load = formStore.load.bind(formStore)
 vi.spyOn(formStore, 'load').mockImplementation(async (...args) => { const values = await load(...args); vi.mocked(p.session).mockResolvedValue({ ...session(), actor_session_id: 'other_actor' }); return values })
 fireEvent.click(screen.getByText(`恢复外发表单 ${original.draft_id} · 1`)); await screen.findByText(/外发操作的当前权限或原 actor 已变化/)
 expect(screen.queryByDisplayValue('private_original')).toBeNull(); expect(Object.keys(await load(workspace))).toEqual([original.snapshot_id])
})

test('restore successful fresh reads preserve its original snapshot and never replace a newer edit made while reading', async () => {
 const p = port(), store = local(), formStore = local(), original = snapshotOutboundForm(workspace, actor, { ...emptyOutboundFields(), preparation_id: 'private_original', max_input_tokens: '1234' }, null)
 await persistOutboundForm(original, formStore)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await refresh()
 const pending = deferred<ReturnType<typeof session>>()
 vi.mocked(p.session).mockReturnValueOnce(pending.promise)
 fireEvent.click(screen.getByText(`恢复外发表单 ${original.draft_id} · 1`))
 fireEvent.change(screen.getByLabelText('完整输入 token 硬上限'), { target: { value: '2222' } })
 await act(async () => pending.resolve(session())); await screen.findByText(/原外发表单已核验并保存独立分支/)
 expect((screen.getByLabelText('完整输入 token 硬上限') as HTMLInputElement).value).toBe('2222')
 expect(JSON.parse((await formStore.load(workspace))[original.snapshot_id].text)).toEqual(original)
})

test('fresh actor change after durable start admission blocks transport without adopting the original consent', async () => {
 const p = port(), store = local(), formStore = local(), save = store.save.bind(store), fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await prepare('start')
 vi.spyOn(store, 'save').mockImplementation(async (...args) => { const value = await save(...args); vi.mocked(p.session).mockResolvedValue({ ...session(), actor_session_id: 'other_actor' }); return value })
 fireEvent.click(screen.getByText(buttons.start)); await screen.findByText(/外发操作的当前权限或原 actor 已变化/)
 expect(fetch).not.toHaveBeenCalled(); expect(Object.values(await store.load(workspace)).map(v => readOutboundCommand(v, workspace))[0].actor_session_id).toBe(actor)
 expect(screen.queryByLabelText('当前外发许可')).toBeNull()
})

test('late grant ACK after an unnotified actor change remains isolated under its original author', async () => {
 const p = port(), store = local(), formStore = local(), pending = deferred<Response>(), fetch = vi.fn(() => pending.promise); vi.stubGlobal('fetch', fetch)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await prepare('grant')
 fireEvent.click(screen.getByText(buttons.grant)); await waitFor(() => expect(fetch).toHaveBeenCalledOnce())
 vi.mocked(p.session).mockResolvedValue({ ...session(), actor_session_id: 'other_actor' })
 await act(async () => pending.resolve(new Response(JSON.stringify(outboundGrant()), { status: 201 })))
 await screen.findByText(/外发操作的当前权限或原 actor 已变化/)
 expect(heldOutboundCommands(workspace)[0].ack).toEqual(outboundGrant()); expect(heldOutboundCommands(workspace)[0].actor_session_id).toBe(actor)
 expect(screen.queryByText(/外发 grant 原 ACK 已保存/)).toBeNull(); expect(screen.queryByLabelText('当前外发提案')).toBeNull()
 await refresh(); expect(screen.queryByText(/核对外发原命令/)).toBeNull(); expect(fetch).toHaveBeenCalledOnce()
})

test('access generation invalidates a pending subject GET and never automatically retries it', async () => {
 const p = port(), store = local(), formStore = local(), pending = deferred<ReturnType<typeof outboundProposal>>()
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await prepare('grant')
 vi.mocked(p.proposal).mockReturnValueOnce(pending.promise); fireEvent.click(screen.getByText('独立读取当前外发提案'))
 await waitFor(() => expect(p.proposal).toHaveBeenCalledTimes(2)); vi.stubGlobal('fetch', vi.fn(async () => new Response('{}')))
 await act(async () => { await request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic_outbound_access_change' }) })
 await act(async () => pending.resolve(outboundProposal()))
 expect(screen.queryByLabelText('当前外发提案')).toBeNull(); expect(p.proposal).toHaveBeenCalledTimes(2); expect(screen.queryByText(/外发 grant 原 ACK/)).toBeNull()
})

test('production-shaped unavailable preparation honestly blocks preview without creating a command or POST', async () => {
 const p = port(), store = local(), formStore = local(), fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
 vi.mocked(p.preparation).mockResolvedValue({ ...outboundPreparation(), validity: 'unavailable' })
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await refresh()
 fireEvent.change(screen.getByLabelText('原准备 ID'), { target: { value: 'turn_preparation_test' } }); fireEvent.click(screen.getByText('读取准备、Job 与 Provider 基准'))
 await screen.findByText(/BLOCKED：CODEX_INPUT_PROOF_UNAVAILABLE。当前没有完整输入证明/)
 expect((screen.getByText(buttons.preview) as HTMLButtonElement).disabled).toBe(true); expect(Object.keys(await store.load(workspace))).toHaveLength(0); expect(fetch).not.toHaveBeenCalled()
})

test('runtime unavailable start retains its exact original command and never displays a result as completed', async () => {
 const p = port(), store = local(), formStore = local(), fetch = vi.fn(async () => new Response(JSON.stringify({ error: { code: 'CODEX_RUNTIME_UNAVAILABLE', message: 'private synthetic runtime' } }), { status: 503 })); vi.stubGlobal('fetch', fetch)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await prepare('start')
 fireEvent.click(screen.getByText(buttons.start)); await screen.findByText(/BLOCKED：CODEX_RUNTIME_UNAVAILABLE/)
 expect(fetch).toHaveBeenCalledOnce(); expect(screen.queryByLabelText('当前未审回合结果')).toBeNull()
 const command = Object.values(await store.load(workspace)).map(v => readOutboundCommand(v, workspace))[0]
 expect(command.ack).toBeNull(); expect(command.error).toEqual({ status: 503, code: 'CODEX_RUNTIME_UNAVAILABLE' })
})

test.each(['none', 'partial', 'complete'] as const)('real result GET displays preserved %s output with all quality checks NOT_RUN', async output_state => {
 const p = port(), store = local(), formStore = local(), answer = output_state === 'none' ? '' : '  未审 α\n中文😀  ', outcome = output_state === 'complete' ? 'completed' as const : 'failed' as const
 const value = { control: { ...outboundControl(), job: { id: 'job_turn_test', status: outcome }, execution: 'terminal', outcome, started_at: '2026-10-04T00:00:02Z', finished_at: '2026-10-04T00:00:03Z', error_code: outcome === 'completed' ? null : 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED' },
  preparation_id: 'turn_preparation_test', answer_markdown: answer, output_sha256: answer ? bytesToHex(sha256(new TextEncoder().encode(answer))) : null, output_state,
  usage: { input_tokens: 50, output_tokens: answer ? 5 : 0 }, mathematical: 'NOT_RUN', sources: 'NOT_RUN', independent_pedagogy: 'NOT_RUN' }
 const fetch = vi.fn(async (_path: string, init: RequestInit) => { expect(init.method).toBe('GET'); return new Response(JSON.stringify(value)) }); vi.stubGlobal('fetch', fetch)
 render(<CodexTurnOutboundPanel workspace={workspace} writeAdmitted port={p} store={store} formStore={formStore} />); await prepare('preview')
 fireEvent.click(screen.getByText('独立读取本回合结果')); await screen.findByLabelText('当前未审回合结果')
 expect(screen.getByLabelText('原始未审回答').textContent).toBe(answer); expect(screen.getByText(`输出 ${output_state} · terminal · ${outcome}`)).toBeTruthy()
 expect(screen.getByText(/数学审查 NOT_RUN · 来源审查 NOT_RUN · 独立教学审查 NOT_RUN/)).toBeTruthy(); expect(fetch).toHaveBeenCalledOnce(); expect(Object.keys(await store.load(workspace))).toHaveLength(0)
})

test('outbound unsaved input and isolated memory reach the existing parent navigation guard', async () => {
 const p = port(), store = local(), formStore = local(), changed = vi.fn()
 vi.spyOn(formStore, 'save').mockRejectedValue(new Error('Synthetic storage unavailable'))
 render(<CodexTurnPanel workspace={workspace} writeAdmitted outboundPort={p} outboundStore={store} outboundFormStore={formStore} onState={changed} />)
 await refresh(); fireEvent.change(screen.getByLabelText('完整输入 token 硬上限'), { target: { value: '1234' } })
 await screen.findByText(/外发表单尚未落盘/)
 expect(changed).toHaveBeenLastCalledWith({ dirty: true, safe: false, isolated: true })
 expect(heldOutboundForms(workspace)[0].fields.max_input_tokens).toBe('1234')
})
