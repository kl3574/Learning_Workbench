import { spawn, execFileSync } from 'node:child_process'
import { createServer } from 'node:net'
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'
import { setTimeout as pause } from 'node:timers/promises'
import assert from 'node:assert/strict'
import { chromium, expect } from '$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02/apps/web/node_modules/@playwright/test/index.mjs'

const root = '$HOME/.cache/learning-workbench-acceptance/m62-public-safe-oct02'
const out = import.meta.dirname, head = 'ff656a2fc360551f872bb0ff4ebe14d8240d82d3'
const digest = b => createHash('sha256').update(b).digest('hex')
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim()
assert.equal(git('rev-parse', 'HEAD'), head); assert.equal(git('status', '--porcelain'), '')
const data = mkdtempSync(`${tmpdir()}/learning-current-native-data-`)
const profile = mkdtempSync(`${tmpdir()}/learning-current-native-profile-`)
async function port() {
 const s = createServer(); await new Promise((ok, no) => { s.once('error', no); s.listen(0, '127.0.0.1', ok) })
 const p = s.address().port; await new Promise((ok, no) => s.close(e => e ? no(e) : ok())); return p
}
const apiPort = await port(); let uiPort = await port(); while (apiPort === uiPort) uiPort = await port()
const origin = `http://127.0.0.1:${uiPort}`
const env = { ...process.env, LEARNING_DATA_DIR: data, LEARNING_UI_ORIGIN: origin, LEARNING_HOST: '127.0.0.1',
 LEARNING_PORT: String(apiPort), PYTHONPATH: `${out}:${root}` }
let api, ui, browser; const generations = [], allCalls = [], errors = []
function start(cmd, args) {
 const child = spawn(cmd, args, { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] })
 // Private, bounded diagnostics only; never dump environment, bootstrap code or requests.
 let output = ''; for (const stream of [child.stdout, child.stderr]) stream.on('data', b => { output = (output + b).slice(-4096) })
 return { child, output: () => output, exit: new Promise(ok => child.once('close', ok)) }
}
async function stop(p) { if (p && p.child.exitCode === null && p.child.signalCode === null) { p.child.kill('SIGTERM'); await p.exit } }
async function ready(url, p) {
 for (let n = 0; n < 400; n++) {
  if (p.child.exitCode !== null) throw new Error('Owned server exited before readiness')
  try { if ((await fetch(url, { signal: AbortSignal.timeout(500) })).ok) return } catch {}
  await pause(50)
 }
 throw new Error('Owned server readiness timeout')
}
async function startApi() {
 api = start(`${root}/.venv/bin/python`, ['-B', '-m', 'uvicorn', 'controlled_api:create_app', '--factory', '--host', '127.0.0.1', '--port', String(apiPort), '--no-access-log'])
 await ready(`http://127.0.0.1:${apiPort}/health`, api); generations.push(api.child.pid)
}
async function open() {
 browser = await chromium.launchPersistentContext(profile, { executablePath: '/usr/bin/google-chrome', headless: true,
  baseURL: origin, viewport: { width: 1440, height: 900 } })
 const page = browser.pages()[0]; page.setDefaultTimeout(15000)
 page.on('pageerror', () => errors.push('PAGE_ERROR'))
 page.on('request', r => { const p = new URL(r.url()).pathname; if (p.startsWith('/api/v1/codex/')) allCalls.push(`${r.method()} ${p}`) })
 return page
}
async function currentHeaders(page, key) {
 const s = await page.request.get('/api/v1/session').then(r => r.json())
 return { Origin: origin, 'X-CSRF-Token': s.csrf_token, 'Idempotency-Key': key }
}
async function clickPost(page, button, path, status) {
 const waiting = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === path)
 await button.click(); const r = await waiting; assert.equal(r.status(), status)
 return { value: await r.json(), bytes: await r.body(), path, body: r.request().postDataJSON(), key: await r.request().headerValue('idempotency-key') }
}
async function panel(page) {
 await page.getByRole('button', { name: '创作', exact: true }).click()
 const p = page.getByRole('region', { name: '本地控制会话', exact: true })
 await p.getByRole('button', { name: '读取本地会话记录', exact: true }).click(); return p
}
async function readPreparation(page, p, id) {
 await p.getByRole('button', { name: `读取准备当前状态 ${id}`, exact: true }).click()
 await expect(p.getByRole('region', { name: '当前冻结准备', exact: true })).toBeVisible()
}
async function stored(page) {
 return await page.evaluate(() => new Promise((ok, no) => {
  const req = indexedDB.open('learning-workbench.codex-bootstrap-commands.v1', 1)
  req.onerror = () => no(Error('IDB open failed'))
  req.onsuccess = () => { const db = req.result, tx = db.transaction('drafts', 'readonly'), get = tx.objectStore('drafts').getAll();
   get.onerror = () => no(Error('IDB read failed')); get.onsuccess = () => { ok(JSON.stringify(get.result.sort((a,b) => a.objectId.localeCompare(b.objectId)))); db.close() } }
 }))
}
const facts = { source: head, controlled_bootstrap: true, actual_Codex_CLI: 'NOT_RUN', actual_external_model: 'NOT_RUN', assertions: [] }
try {
 await startApi(); ui = start('bash', ['scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'dev', '--', '--port', String(uiPort)])
 await ready(origin, ui); let page = await open()
 // Authentication capability stays only in memory; never written to evidence or logs.
 const code = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'from services.api.app.config import Settings; from services.api.app.database import Database; from services.api.app.security import issue_bootstrap_code; d=Database(Settings.from_env()); d.initialize(); print(issue_bootstrap_code(d))'], { cwd: root, env, encoding: 'utf8' }).trim()
 await page.goto(`${origin}/#bootstrap=${code}`); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
 assert.equal(page.url(), `${origin}/`)
 assert.equal((await page.request.post('/api/v1/session/role', { data: { role: 'author' }, headers: await currentHeaders(page, 'native-author') })).status(), 200)
 await page.reload(); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
 assert.equal((await page.request.put('/api/v1/providers/codex_local/config', { data: { expected_revision: 0, adapter: 'compatible_chat', base_url: 'https://example.invalid', model: 'synthetic-model', embedding_model: null, endpoint_policy: 'public_https', pricing: null }, headers: await currentHeaders(page, 'native-config') })).status(), 200)
 let p = await panel(page); assert.deepEqual(allCalls, [])
 const prepared = await clickPost(page, p.getByRole('button', { name: '准备本地控制会话', exact: true }), '/api/v1/codex/session-preparations', 201)
 await readPreparation(page, p, prepared.value.id)
 const decided = await clickPost(page, p.getByRole('button', { name: '仅批准这一次本地建会话', exact: true }), `/api/v1/codex/session-preparations/${prepared.value.id}/decision`, 200)
 await readPreparation(page, p, prepared.value.id)
 const created = await clickPost(page, p.getByRole('button', { name: '明确创建这次本地会话', exact: true }), '/api/v1/codex/sessions', 201)
 const sid = created.value.id; assert.equal(created.value.revision, 2); assert.equal(created.value.status, 'ready')
 await readPreparation(page, p, prepared.value.id)
 await expect(p.getByText('真实本地记录：ready · r2', { exact: true })).toBeVisible()
 const originalCommands = await stored(page)
 const body = { message: 'Original synthetic native α. No execution.', context_refs: [], expected_session_revision: 2, provider_id: 'codex_local', tools: { max_tool_calls: 0, wall_seconds: 30 } }
 const path = `/api/v1/codex/sessions/${sid}/turn-preparations`, response = await page.request.post(path, { data: body, headers: await currentHeaders(page, 'native-turn-original') })
 assert.equal(response.status(), 202); const turn = await response.json(), ack = await response.body()
 assert.equal(turn.validity, 'unavailable'); assert.equal(turn.job.status, 'awaiting_approval')
 await readPreparation(page, p, prepared.value.id)
 await expect(p.getByText('真实本地记录：ready · r3', { exact: true })).toBeVisible()
 await expect(p.getByText(`active_turn_id：${turn.turn_id}；审批、interrupt、artifacts：false、false、false。`, { exact: true })).toBeVisible()
 assert.equal(await stored(page), originalCommands)
 facts.assertions.push('actual HTTP202 creates Job/Run + active slot, original UI command bytes unchanged, r3/current turn displayed')
 for (const width of [1440, 390]) {
  await page.setViewportSize({ width, height: 900 }); await p.getByText('真实本地记录：ready · r3', { exact: true }).scrollIntoViewIfNeeded()
  const geometry = await page.getByRole('dialog', { name: '创作', exact: true }).evaluate(e => ({ client: e.clientWidth, scroll: e.scrollWidth, viewport: innerWidth, document: document.documentElement.scrollWidth }))
  assert.ok(geometry.scroll <= geometry.client + 1 && geometry.document <= geometry.viewport)
  writeFileSync(resolve(out, `r3-${width}-geometry.json`), JSON.stringify(geometry, null, 2)); await page.screenshot({ path: resolve(out, `r3-${width}.png`) })
 }
 const cancelled = await page.request.post(`/api/v1/jobs/${turn.job.id}/cancel`, { data: { expected_revision: 1 }, headers: await currentHeaders(page, 'native-cancel-original') })
 assert.equal(cancelled.status(), 200); assert.equal((await cancelled.json()).status, 'cancelled')
 await readPreparation(page, p, prepared.value.id); await expect(p.getByText('真实本地记录：ready · r5', { exact: true })).toBeVisible()
 await expect(p.getByText('active_turn_id：null；审批、interrupt、artifacts：false、false、false。', { exact: true })).toBeVisible()
 assert.equal(await stored(page), originalCommands)
 const turnReplay = await page.request.post(path, { data: body, headers: await currentHeaders(page, 'native-turn-original') }); assert.equal(turnReplay.status(), 202); assert.deepEqual(await turnReplay.body(), ack)
 const bootstrapReplay = await page.request.post(created.path, { data: created.body, headers: await currentHeaders(page, created.key) }); assert.equal(bootstrapReplay.status(), 201); assert.deepEqual(await bootstrapReplay.body(), created.bytes)
 facts.assertions.push('actual cancel200 releases r5/null slot; original202 and201 ACKs replay byte-exact without another bootstrap')
 const afterExplicit = allCalls.filter(x => x.startsWith('POST ')).length
 await browser.close(); browser = undefined; await stop(api); api = undefined; await startApi(); page = await open()
 await page.goto(origin); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible(); p = await panel(page)
 await readPreparation(page, p, prepared.value.id); await expect(p.getByText('真实本地记录：ready · r5', { exact: true })).toBeVisible()
 assert.equal(await stored(page), originalCommands); assert.equal(allCalls.filter(x => x.startsWith('POST ')).length, afterExplicit)
 assert.equal(new Set(generations).size, 2); assert.equal(readFileSync(resolve(data, 'synthetic-bootstrap-count.txt'), 'utf8'), 'synthetic-bootstrap\n')
 assert.deepEqual(errors, []); assert.equal(git('rev-parse', 'HEAD'), head); assert.equal(git('status', '--porcelain'), '')
 facts.assertions.push('actual browser close/API process restart/reopen preserves actor+IDB and r5; no automatic Codex POST; exactly one synthetic bootstrap')
 facts.status = 'NATIVE_CURRENT_METADATA_CONTROLLED_PORT_PASS'; facts.recorded_at = new Date().toISOString()
 facts.bootstrap_ack_sha256 = digest(created.bytes); facts.turn_ack_sha256 = digest(ack); facts.original_ui_records_sha256 = digest(originalCommands)
 facts.browser = await browser.browser()?.version(); facts.api_process_generations = generations.length; facts.codex_calls = allCalls
 facts.boundary = 'Native Chrome + real app HTTP/SQLite/IndexedDB against explicitly synthetic bootstrap only. Actual CLI/model/turn dispatch/wholeM6.3/quality NOT_RUN; production proof unavailable unchanged.'
 writeFileSync(resolve(out, 'receipt.json'), JSON.stringify(facts, null, 2) + '\n'); console.log(facts.status)
} catch (e) {
 writeFileSync(resolve(out, 'failure.json'), JSON.stringify({ status: 'NATIVE_CHECK_FAIL', source: head, name: e.name, message: String(e.message).replace(/#bootstrap=[^\s]*/g, '#bootstrap=REDACTED') }, null, 2) + '\n')
 throw e
} finally { await browser?.close(); await stop(ui); await stop(api) }
