# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: codex-bootstrap.spec.ts >> actual local bootstrap keeps explicit approval, original commands and current metadata across restart
- Location: tests/e2e/codex-bootstrap.spec.ts:91:1

# Error details

```
Error: expect(locator).toHaveCount(expected) failed

Locator:  getByRole('dialog', { name: '创作', exact: true }).getByRole('region', { name: '本地控制会话', exact: true }).getByText('尚未读取当前会话与本机原命令。', { exact: true })
Expected: 0
Received: 1
Timeout:  5000ms

Call log:
  - Expect "toHaveCount" getByRole('dialog', { name: '创作', exact: true }).getByRole('region', { name: '本地控制会话', exact: true }).getByText('尚未读取当前会话与本机原命令。', { exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '创作', exact: true }).getByRole('region', { name: '本地控制会话', exact: true }).getByText('尚未读取当前会话与本机原命令。', { exact: true })
    14 × locator resolved to 1 element
       - unexpected value "1"

```

# Test source

```ts
  1   | import { createHash } from 'node:crypto'
  2   | import { execFileSync } from 'node:child_process'
  3   | import { writeFileSync } from 'node:fs'
  4   | import { resolve } from 'node:path'
  5   | import { expect, test, type Locator, type Page, type Response } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  6   | import type { CodexBootstrapDecisionAck, CodexBootstrapPreparationView, CodexSessionView } from '../../packages/contracts/generated/codex-bootstrap-types'
  7   | import { RestartRuntime } from './restartRuntime'
  8   | import { role, screenshot } from './authoringTestData'
  9   | 
  10  | type Original = { path: string; key: string; body: unknown; status: number; bytes: Buffer }
  11  | type Registrations = { sessions: number; permits: number; finished: number }
  12  | const noFeatures = { approvals: false, interrupt: false, artifacts: false }
  13  | const sha256 = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')
  14  | 
  15  | // Only aggregate facts from this test's newly created synthetic workspace.
  16  | // This does not count OS process execution or prove the runtime's isolation.
  17  | function registrations(runtime: RestartRuntime): Registrations {
  18  |   const root = resolve(import.meta.dirname, '../..')
  19  |   const program = `import json,sys
  20  | from pathlib import Path
  21  | from services.api.app.config import Settings
  22  | from services.api.app.database import Database
  23  | db=Database(Settings(data_dir=Path(sys.argv[1])))
  24  | with db.transaction(immediate=False) as connection:
  25  |  connection.execute('PRAGMA query_only=ON')
  26  |  print(json.dumps({'sessions':connection.execute('SELECT count(*) FROM codex_sessions').fetchone()[0], 'permits':connection.execute('SELECT count(*) FROM codex_bootstrap_events WHERE sequence=3').fetchone()[0], 'finished':connection.execute('SELECT count(*) FROM codex_bootstrap_events WHERE sequence=4').fetchone()[0]}))`
  27  |   return JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', program, runtime.data], { cwd: root, encoding: 'utf8' }))
  28  | }
  29  | 
  30  | async function original(response: Response): Promise<Original> {
  31  |   const key = await response.request().headerValue('idempotency-key')
  32  |   expect(key).toMatch(/^codexcmd_[A-Za-z0-9_-]+$/)
  33  |   return { path: new URL(response.url()).pathname, key: key!, body: response.request().postDataJSON(), status: response.status(), bytes: await response.body() }
  34  | }
  35  | 
  36  | async function openPanel(page: Page) {
  37  |   await page.getByRole('button', { name: '创作', exact: true }).click()
  38  |   const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  39  |   const panel = dialog.getByRole('region', { name: '本地控制会话', exact: true })
  40  |   await expect(panel.getByText('尚未读取当前会话与本机原命令。', { exact: true })).toBeVisible()
  41  |   await panel.getByRole('button', { name: '读取本地会话记录', exact: true }).click()
> 42  |   await expect(panel.getByText('尚未读取当前会话与本机原命令。', { exact: true })).toHaveCount(0)
      |                                                                     ^ Error: expect(locator).toHaveCount(expected) failed
  43  |   return { dialog, panel }
  44  | }
  45  | 
  46  | async function postByClick(page: Page, button: Locator, path: string) {
  47  |   const pending = page.waitForResponse(value => value.request().method() === 'POST' && new URL(value.url()).pathname === path)
  48  |   await button.click()
  49  |   return pending
  50  | }
  51  | 
  52  | async function prepare(page: Page, panel: Locator) {
  53  |   const response = await postByClick(page, panel.getByRole('button', { name: '准备本地控制会话', exact: true }), '/api/v1/codex/session-preparations')
  54  |   expect(response.status()).toBe(201)
  55  |   const ack: CodexBootstrapPreparationView = await response.json()
  56  |   expect(ack).toMatchObject({ revision: 1, status: 'pending', consent_id: null, session_id: null })
  57  |   expect(ack.scope.allowed_actions).toEqual([])
  58  |   await expect(panel.getByText('准备原 ACK 已保存；须另读当前资格。', { exact: true })).toBeVisible()
  59  |   await expect(panel.getByRole('region', { name: '当前冻结准备', exact: true })).toHaveCount(0)
  60  |   return { ack, command: await original(response) }
  61  | }
  62  | 
  63  | async function readPreparation(page: Page, panel: Locator, id: string) {
  64  |   const pending = page.waitForResponse(value => value.request().method() === 'GET' && new URL(value.url()).pathname === `/api/v1/codex/session-preparations/${id}`)
  65  |   await panel.getByRole('button', { name: `读取准备当前状态 ${id}`, exact: true }).click()
  66  |   const response = await pending
  67  |   expect(response.status()).toBe(200)
  68  |   expect(response.headers()['cache-control']).toBe('no-store')
  69  |   const value: CodexBootstrapPreparationView = await response.json()
  70  |   await expect(panel.getByRole('region', { name: '当前冻结准备', exact: true })).toContainText(`准备 ${id} · r${value.revision} · ${value.status} · 当前资格 ${value.validity}`)
  71  |   if (value.session_id) await expect(panel.getByRole('region', { name: `当前本地会话 ${value.session_id}`, exact: true })).toBeVisible()
  72  |   return value
  73  | }
  74  | 
  75  | async function replay(page: Page, origin: string, command: Original) {
  76  |   // Explicit test action with the original full body/key; never an automatic UI retry.
  77  |   // The fresh transport secret stays only in memory and is not saved to evidence.
  78  |   const session = await page.request.get('/api/v1/session').then(value => value.json())
  79  |   const response = await page.request.post(command.path, { data: command.body, headers: {
  80  |     Origin: origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': command.key,
  81  |   } })
  82  |   expect(response.status()).toBe(command.status)
  83  |   const bytes = await response.body()
  84  |   if (response.status() < 400) expect(bytes).toEqual(command.bytes)
  85  |   else expect((await response.json()).error.code).toBe(JSON.parse(command.bytes.toString()).error.code)
  86  |   return { path: command.path, original_status: command.status, replay_status: response.status(),
  87  |     original_ack_sha256: sha256(command.bytes), replay_ack_sha256: sha256(bytes),
  88  |     equal_ack_bytes: response.status() < 400 ? bytes.equals(command.bytes) : null }
  89  | }
  90  | 
  91  | test('actual local bootstrap keeps explicit approval, original commands and current metadata across restart', async ({ playwright }, info) => {
  92  |   test.setTimeout(120_000)
  93  |   const runtime = await RestartRuntime.start(), calls: string[] = [], errors: string[] = []
  94  |   const observe = (page: Page) => {
  95  |     page.on('pageerror', () => errors.push('PAGE_ERROR'))
  96  |     page.on('request', request => {
  97  |       const path = new URL(request.url()).pathname
  98  |       if (path.startsWith('/api/v1/codex/')) calls.push(`${request.method()} ${path}`)
  99  |     })
  100 |   }
  101 |   try {
  102 |     let browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]; observe(page)
  103 |     await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author')
  104 |     const actor = await page.request.get('/api/v1/session').then(value => value.json()).then(value => value.actor_session_id as string)
  105 |     let { panel } = await openPanel(page)
  106 |     expect(calls).toEqual([]) // No Codex request on mount or local DraftStore read.
  107 |     const before = registrations(runtime)
  108 |     expect(before).toEqual({ sessions: 0, permits: 0, finished: 0 })
  109 | 
  110 |     const declined = await prepare(page, panel)
  111 |     expect(declined.ack.actor_session_id).toBe(actor)
  112 |     const decliningBasis = await readPreparation(page, panel, declined.ack.id)
  113 |     expect(decliningBasis.status).toBe('pending')
  114 |     expect(['current', 'changed', 'unavailable']).toContain(decliningBasis.validity)
  115 |     const declineResponse = await postByClick(page, panel.getByRole('button', { name: '拒绝这次本地建会话', exact: true }), `/api/v1/codex/session-preparations/${declined.ack.id}/decision`)
  116 |     expect(declineResponse.status()).toBe(200)
  117 |     const declineAck: CodexBootstrapDecisionAck = await declineResponse.json()
  118 |     expect(declineAck).toMatchObject({ revision: 2, actor_session_id: actor, decision: 'decline', consent_id: null })
  119 |     const declineCommand = await original(declineResponse)
  120 |     await expect(panel.getByText('决定原 ACK 已保存；须另读当前资格。', { exact: true })).toBeVisible()
  121 |     await expect(panel.getByRole('region', { name: '当前冻结准备', exact: true })).toHaveCount(0)
  122 |     const declinedCurrent = await readPreparation(page, panel, declined.ack.id)
  123 |     expect(declinedCurrent).toMatchObject({ revision: 2, status: 'declined', validity: 'closed', consent_id: null, session_id: null })
  124 |     expect(calls.filter(value => value === 'POST /api/v1/codex/sessions')).toEqual([])
  125 |     expect(registrations(runtime)).toEqual(before)
  126 | 
  127 |     const candidate = await prepare(page, panel)
  128 |     const current = await readPreparation(page, panel, candidate.ack.id)
  129 |     const frozen = panel.getByRole('region', { name: '当前冻结准备', exact: true })
  130 |     await expect(frozen).toContainText('允许 actions：[]；零模型、零工具、零学科读取、零网络。')
  131 |     await expect(frozen).toContainText(current.scope.sandbox_root_id)
  132 |     await expect(frozen).toContainText(current.scope.adapter_version)
  133 |     await expect(frozen).toContainText(current.scope.bootstrap_profile_sha256)
  134 |     await expect(frozen).toContainText(current.operation_sha256)
  135 |     const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  136 |     const wide = await screenshot(page, dialog, 1440, frozen, 'codex-bootstrap-1440.png', info)
  137 |     const narrow = await screenshot(page, dialog, 390, frozen, 'codex-bootstrap-390.png', info)
  138 |     const originals = [declined.command, declineCommand, candidate.command]
  139 |     let realThread: 'PASS' | 'BLOCKED' = 'BLOCKED', blockedCode: string | null = null
  140 |     let createCommand: Original | null = null, currentSession: CodexSessionView | null = null
  141 |     let finalPreparation = current
  142 |     if (current.validity === 'current') {
```