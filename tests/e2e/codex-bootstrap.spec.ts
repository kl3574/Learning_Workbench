import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Locator, type Page, type Response } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { CodexBootstrapDecisionAck, CodexBootstrapPreparationView, CodexSessionView } from '../../packages/contracts/generated/codex-bootstrap-types'
import { RestartRuntime } from './restartRuntime'
import { role, screenshot } from './authoringTestData'

type Original = { path: string; key: string; body: unknown; status: number; bytes: Buffer }
type Registrations = { sessions: number; permits: number; finished: number }
const noFeatures = { approvals: false, interrupt: false, artifacts: false }
const sha256 = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')

// Only aggregate facts from this test's newly created synthetic workspace.
// This does not count OS process execution or prove the runtime's isolation.
function registrations(runtime: RestartRuntime): Registrations {
  const root = resolve(import.meta.dirname, '../..')
  const program = `import json,sys
from pathlib import Path
from services.api.app.config import Settings
from services.api.app.database import Database
db=Database(Settings(data_dir=Path(sys.argv[1])))
with db.transaction(immediate=False) as connection:
 connection.execute('PRAGMA query_only=ON')
 print(json.dumps({'sessions':connection.execute('SELECT count(*) FROM codex_sessions').fetchone()[0], 'permits':connection.execute('SELECT count(*) FROM codex_bootstrap_events WHERE sequence=3').fetchone()[0], 'finished':connection.execute('SELECT count(*) FROM codex_bootstrap_events WHERE sequence=4').fetchone()[0]}))`
  return JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', program, runtime.data], { cwd: root, encoding: 'utf8' }))
}

async function original(response: Response): Promise<Original> {
  const key = await response.request().headerValue('idempotency-key')
  expect(key).toMatch(/^codexcmd_[A-Za-z0-9_-]+$/)
  return { path: new URL(response.url()).pathname, key: key!, body: response.request().postDataJSON(), status: response.status(), bytes: await response.body() }
}

async function openPanel(page: Page) {
  await page.getByRole('button', { name: '创作', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  const panel = dialog.getByRole('region', { name: '本地控制会话', exact: true })
  await expect(panel.getByText('尚未读取当前会话与本机原命令。', { exact: true })).toBeVisible()
  await panel.getByRole('button', { name: '读取本地会话记录', exact: true }).click()
  await expect(panel.getByText('尚未读取当前会话与本机原命令。', { exact: true })).toHaveCount(0)
  return { dialog, panel }
}

async function postByClick(page: Page, button: Locator, path: string) {
  const pending = page.waitForResponse(value => value.request().method() === 'POST' && new URL(value.url()).pathname === path)
  await button.click()
  return pending
}

async function prepare(page: Page, panel: Locator) {
  const response = await postByClick(page, panel.getByRole('button', { name: '准备本地控制会话', exact: true }), '/api/v1/codex/session-preparations')
  expect(response.status()).toBe(201)
  const ack: CodexBootstrapPreparationView = await response.json()
  expect(ack).toMatchObject({ revision: 1, status: 'pending', consent_id: null, session_id: null })
  expect(ack.scope.allowed_actions).toEqual([])
  await expect(panel.getByText('准备原 ACK 已保存；须另读当前资格。', { exact: true })).toBeVisible()
  await expect(panel.getByRole('region', { name: '当前冻结准备', exact: true })).toHaveCount(0)
  return { ack, command: await original(response) }
}

async function readPreparation(page: Page, panel: Locator, id: string) {
  const pending = page.waitForResponse(value => value.request().method() === 'GET' && new URL(value.url()).pathname === `/api/v1/codex/session-preparations/${id}`)
  await panel.getByRole('button', { name: `读取准备当前状态 ${id}`, exact: true }).click()
  const response = await pending
  expect(response.status()).toBe(200)
  expect(response.headers()['cache-control']).toBe('no-store')
  const value: CodexBootstrapPreparationView = await response.json()
  await expect(panel.getByRole('region', { name: '当前冻结准备', exact: true })).toContainText(`准备 ${id} · r${value.revision} · ${value.status} · 当前资格 ${value.validity}`)
  if (value.session_id) await expect(panel.getByRole('region', { name: `当前本地会话 ${value.session_id}`, exact: true })).toBeVisible()
  return value
}

async function replay(page: Page, origin: string, command: Original) {
  // Explicit test action with the original full body/key; never an automatic UI retry.
  // The fresh transport secret stays only in memory and is not saved to evidence.
  const session = await page.request.get('/api/v1/session').then(value => value.json())
  const response = await page.request.post(command.path, { data: command.body, headers: {
    Origin: origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': command.key,
  } })
  expect(response.status()).toBe(command.status)
  const bytes = await response.body()
  if (response.status() < 400) expect(bytes).toEqual(command.bytes)
  else expect((await response.json()).error.code).toBe(JSON.parse(command.bytes.toString()).error.code)
  return { path: command.path, original_status: command.status, replay_status: response.status(),
    original_ack_sha256: sha256(command.bytes), replay_ack_sha256: sha256(bytes),
    equal_ack_bytes: response.status() < 400 ? bytes.equals(command.bytes) : null }
}

test('actual local bootstrap keeps explicit approval, original commands and current metadata across restart', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start(), calls: string[] = [], errors: string[] = []
  const observe = (page: Page) => {
    page.on('pageerror', () => errors.push('PAGE_ERROR'))
    page.on('request', request => {
      const path = new URL(request.url()).pathname
      if (path.startsWith('/api/v1/codex/')) calls.push(`${request.method()} ${path}`)
    })
  }
  try {
    let browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]; observe(page)
    await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author')
    const actor = await page.request.get('/api/v1/session').then(value => value.json()).then(value => value.actor_session_id as string)
    let { panel } = await openPanel(page)
    expect(calls).toEqual([]) // No Codex request on mount or local DraftStore read.
    const before = registrations(runtime)
    expect(before).toEqual({ sessions: 0, permits: 0, finished: 0 })

    const declined = await prepare(page, panel)
    expect(declined.ack.actor_session_id).toBe(actor)
    const decliningBasis = await readPreparation(page, panel, declined.ack.id)
    expect(decliningBasis.status).toBe('pending')
    expect(['current', 'changed', 'unavailable']).toContain(decliningBasis.validity)
    const declineResponse = await postByClick(page, panel.getByRole('button', { name: '拒绝这次本地建会话', exact: true }), `/api/v1/codex/session-preparations/${declined.ack.id}/decision`)
    expect(declineResponse.status()).toBe(200)
    const declineAck: CodexBootstrapDecisionAck = await declineResponse.json()
    expect(declineAck).toMatchObject({ revision: 2, actor_session_id: actor, decision: 'decline', consent_id: null })
    const declineCommand = await original(declineResponse)
    await expect(panel.getByText('决定原 ACK 已保存；须另读当前资格。', { exact: true })).toBeVisible()
    await expect(panel.getByRole('region', { name: '当前冻结准备', exact: true })).toHaveCount(0)
    const declinedCurrent = await readPreparation(page, panel, declined.ack.id)
    expect(declinedCurrent).toMatchObject({ revision: 2, status: 'declined', validity: 'closed', consent_id: null, session_id: null })
    expect(calls.filter(value => value === 'POST /api/v1/codex/sessions')).toEqual([])
    expect(registrations(runtime)).toEqual(before)

    const candidate = await prepare(page, panel)
    const current = await readPreparation(page, panel, candidate.ack.id)
    const frozen = panel.getByRole('region', { name: '当前冻结准备', exact: true })
    await expect(frozen).toContainText('允许 actions：[]；零模型、零工具、零学科读取、零网络。')
    await expect(frozen).toContainText(current.scope.sandbox_root_id)
    await expect(frozen).toContainText(current.scope.adapter_version)
    await expect(frozen).toContainText(current.scope.bootstrap_profile_sha256)
    await expect(frozen).toContainText(current.operation_sha256)
    const dialog = page.getByRole('dialog', { name: '创作', exact: true })
    const wide = await screenshot(page, dialog, 1440, frozen, 'codex-bootstrap-1440.png', info)
    const narrow = await screenshot(page, dialog, 390, frozen, 'codex-bootstrap-390.png', info)
    const originals = [declined.command, declineCommand, candidate.command]
    let realThread: 'PASS' | 'BLOCKED' = 'BLOCKED', blockedCode: string | null = null
    let createCommand: Original | null = null, currentSession: CodexSessionView | null = null
    let finalPreparation = current
    if (current.validity === 'current') {
      const approving = await postByClick(page, panel.getByRole('button', { name: '仅批准这一次本地建会话', exact: true }), `/api/v1/codex/session-preparations/${current.id}/decision`)
      expect(approving.status()).toBe(200)
      const decision: CodexBootstrapDecisionAck = await approving.json()
      expect(decision).toMatchObject({ revision: 2, actor_session_id: actor, decision: 'approve_once' })
      expect(decision.consent_id).not.toBeNull()
      originals.push(await original(approving))
      await expect(panel.getByText('决定原 ACK 已保存；须另读当前资格。', { exact: true })).toBeVisible()
      await expect(panel.getByRole('button', { name: '明确创建这次本地会话', exact: true })).toHaveCount(0)
      const approved = await readPreparation(page, panel, current.id)
      expect(approved).toMatchObject({ revision: 2, status: 'approved', validity: 'current', consent_id: decision.consent_id, session_id: null })
      expect(registrations(runtime)).toEqual(before)
      const creating = await postByClick(page, panel.getByRole('button', { name: '明确创建这次本地会话', exact: true }), '/api/v1/codex/sessions')
      expect([201, 503]).toContain(creating.status())
      createCommand = await original(creating); originals.push(createCommand)
      if (creating.status() === 201) {
        expect(await creating.json()).toMatchObject({ revision: 2, status: 'ready', capabilities: noFeatures, adapter_version: current.scope.adapter_version })
        await expect(panel.getByText('原 201 ACK 已保存；ready 仅表示已核验映射。', { exact: true })).toBeVisible()
        realThread = 'PASS'
      } else {
        blockedCode = (await creating.json()).error.code
        expect(['CODEX_BOOTSTRAP_UNAVAILABLE', 'CODEX_SESSION_OUTCOME_UNKNOWN']).toContain(blockedCode)
        await expect(panel.getByText('create · 已收到安全错误；当前实例须另读', { exact: true })).toBeVisible()
      }
      finalPreparation = await readPreparation(page, panel, current.id)
      expect(finalPreparation).toMatchObject({ revision: 3, status: 'consumed', validity: 'closed', consent_id: decision.consent_id })
      expect(finalPreparation.session_id).not.toBeNull()
      const response = await page.request.get(`/api/v1/codex/sessions/${finalPreparation.session_id}`)
      expect(response.status()).toBe(200)
      currentSession = await response.json()
      expect(currentSession).toMatchObject({ id: finalPreparation.session_id, revision: 2, active_turn_id: null, capabilities: noFeatures })
      expect(currentSession!.status).toBe(realThread === 'PASS' ? 'ready' : blockedCode === 'CODEX_BOOTSTRAP_UNAVAILABLE' ? 'failed' : 'unknown')
      expect(registrations(runtime)).toEqual({ sessions: 1, permits: 1, finished: 1 })
      expect(calls.filter(value => value === 'POST /api/v1/codex/sessions')).toHaveLength(1)
    } else {
      expect(['unavailable', 'changed']).toContain(current.validity)
      blockedCode = `PREPARATION_${current.validity.toUpperCase()}`
      await expect(panel.getByRole('button', { name: '仅批准这一次本地建会话', exact: true })).toBeDisabled()
      await expect(panel.getByRole('button', { name: '明确创建这次本地会话', exact: true })).toHaveCount(0)
      expect(registrations(runtime)).toEqual(before)
      expect(calls.filter(value => value === 'POST /api/v1/codex/sessions')).toHaveLength(0)
    }

    const stored = registrations(runtime), database = runtime.databaseIdentity(), requestsBeforeRestart = calls.length
    await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed()
    browser = await runtime.openBrowser(playwright.chromium); page = browser.pages()[0]; observe(page)
    await page.goto(runtime.origin); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
    expect(await page.request.get('/api/v1/session').then(value => value.json()).then(value => value.actor_session_id)).toBe(actor)
    ;({ panel } = await openPanel(page))
    expect(calls).toHaveLength(requestsBeforeRestart) // Real DraftStore reload never resends a command.
    for (const command of originals) {
      const summary = panel.getByText(`核对原控制命令 ${command.key}`, { exact: true })
      await summary.click()
      const article = panel.getByRole('article').filter({ hasText: command.key })
      expect(JSON.parse((await article.locator('pre').first().textContent())!)).toEqual(command.body)
      await expect(article).toContainText(`原 actor：${actor}`)
    }
    expect(await readPreparation(page, panel, declined.ack.id)).toEqual(declinedCurrent)
    const restartedPreparation = await readPreparation(page, panel, candidate.ack.id)
    expect(restartedPreparation).toEqual(finalPreparation)
    if (currentSession) {
      const response = await page.request.get(`/api/v1/codex/sessions/${currentSession.id}`)
      expect(response.status()).toBe(200); expect(await response.json()).toEqual(currentSession)
    }
    expect(runtime.databaseIdentity()).toEqual(database)
    expect(registrations(runtime)).toEqual(stored)
    const replays = []
    for (const command of originals) replays.push(await replay(page, runtime.origin, command))
    expect(registrations(runtime)).toEqual(stored)

    await role(page, runtime.origin, 'learner')
    ;({ panel } = await openPanel(page))
    await expect(panel.getByRole('button', { name: '准备本地控制会话', exact: true })).toBeDisabled()
    expect(await readPreparation(page, panel, candidate.ack.id)).toEqual(finalPreparation)
    for (const button of await panel.getByRole('button', { name: /^显式回放原 key / }).all()) await expect(button).toBeDisabled()
    expect(registrations(runtime)).toEqual(stored); expect(errors).toEqual([])
    writeFileSync(info.outputPath('codex-bootstrap-actual.json'), JSON.stringify({
      scope: 'Real production application/HTTP and persistent browser DraftStore, synthetic workspace, explicit control-only actions; no mocked response/runtime and no turn/login/tool/model request. This browser case does not independently prove OS isolation or count CLI starts.',
      real_thread: realThread, blocked_code: blockedCode,
      acceptance: realThread === 'PASS' ? 'Verified production ready mapping and persisted readback; backend execution evidence still required for unique upstream start and isolation.' : 'UI safety/degradation assertions passed; real thread acceptance remains BLOCKED, not a skipped green success.',
      actor_preserved: true, preparation_original: candidate.ack, preparation_current: finalPreparation, session_current: currentSession,
      declined_current: declinedCurrent, decline_session_posts: 0, decline_registered_instances: before,
      create_posts_before_explicit_replay: createCommand ? 1 : 0, registrations_before_restart: stored, registrations_after_restart_and_replay: registrations(runtime),
      original_replays: replays, database_identity_unchanged: true, api_processes: runtime.generations.length,
      browser_requests: calls, viewport_bounds: { wide, narrow }, page_errors: errors,
    }, null, 2))
  } finally { await runtime.close() }
})
