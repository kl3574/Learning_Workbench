import { spawn, execFileSync, type ChildProcess } from 'node:child_process'
import { mkdtempSync, existsSync, statSync, readFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { setTimeout as pause } from 'node:timers/promises'
import { expect, type BrowserContext, type BrowserType, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(import.meta.dirname, '../..')
type OwnedProcess = { child: ChildProcess; exit: Promise<void>; output: () => string }
const ownedGroups = new Set<number>()
// Playwright can dispose a timed-out worker before its async finally finishes.
// A synchronous exit hook still signals only this worker's retained child groups.
process.once('exit', () => {
  for (const pid of ownedGroups) {
    try { process.kill(-pid, 'SIGTERM') } catch { /* An already exited owned group needs no cleanup. */ }
  }
})

async function availablePort() {
  const socket = createServer()
  await new Promise<void>((accept, reject) => { socket.once('error', reject); socket.listen(0, '127.0.0.1', accept) })
  const address = socket.address()
  if (!address || typeof address === 'string') throw new Error('No loopback test port')
  await new Promise<void>((accept, reject) => socket.close(error => error ? reject(error) : accept()))
  return address.port
}

function owned(command: string, args: string[], env: NodeJS.ProcessEnv): OwnedProcess {
  const child = spawn(command, args, { cwd: root, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] })
  if (child.pid) ownedGroups.add(child.pid)
  let output = ''
  for (const stream of [child.stdout, child.stderr]) stream?.on('data', chunk => { output = (output + String(chunk)).slice(-8192) })
  const exit = new Promise<void>(accept => {
    const done = () => { if (child.pid) ownedGroups.delete(child.pid); accept() }
    child.once('close', done); child.once('error', done)
  })
  return { child, exit, output: () => output }
}

async function stopOwned(value: OwnedProcess | undefined) {
  if (!value || value.child.exitCode !== null || value.child.signalCode !== null) return
  const pid = value.child.pid
  if (!pid) { await value.exit; return }
  // Only signal the new process group created and retained by this harness.
  // Never find/kill an existing server by its port or stop a user process.
  try { process.kill(-pid, 'SIGTERM') } catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error }
  let timer: ReturnType<typeof setTimeout> | undefined
  const forced = new Promise<void>(accept => {
    timer = setTimeout(() => {
      try { process.kill(-pid, 'SIGKILL') } catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error }
      accept()
    }, 5000)
  })
  await Promise.race([value.exit, forced])
  clearTimeout(timer)
  await value.exit
}

async function ready(url: string, service: OwnedProcess) {
  const deadline = Date.now() + 20_000
  while (Date.now() < deadline) {
    if (service.child.exitCode !== null || service.child.signalCode !== null) throw new Error(`Owned test server exited before readiness: ${service.output()}`)
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1000) })
      if (response.ok) return
    } catch { /* Wait for this new process to bind its loopback port. */ }
    await pause(50)
  }
  throw new Error(`Owned test server did not become ready: ${service.output()}`)
}

/** Explicit test-only factory runtime. The production RestartRuntime remains unchanged.
 * Process ownership/cleanup follows that existing harness; the complete-byte
 * proof and loopback endpoint are available only through this selected factory. */
export class AuthoringRuntime {
  readonly data = mkdtempSync(`${tmpdir()}/learning-workbench-authoring-provider-data-`)
  readonly profile = mkdtempSync(`${tmpdir()}/learning-workbench-authoring-provider-browser-`)
  readonly generations: number[] = []
  readonly origin: string
  private readonly env: NodeJS.ProcessEnv
  private api?: OwnedProcess
  private ui?: OwnedProcess
  private context?: BrowserContext

  private constructor(private readonly apiPort: number, uiPort: number, scenario: 'complete' | 'no_proof') {
    this.origin = `http://127.0.0.1:${uiPort}`
    this.env = { ...process.env, LEARNING_DATA_DIR: this.data, LEARNING_UI_ORIGIN: this.origin, LEARNING_HOST: '127.0.0.1', LEARNING_PORT: String(apiPort), AUTHORING_NATIVE_SCENARIO: scenario }
  }

  static async start(scenario: 'complete' | 'no_proof' = 'no_proof') {
    const apiPort = await availablePort()
    let uiPort = await availablePort()
    while (uiPort === apiPort) uiPort = await availablePort()
    const runtime = new AuthoringRuntime(apiPort, uiPort, scenario)
    try {
      await runtime.startApi()
      runtime.ui = owned('bash', ['scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'dev', '--', '--port', String(uiPort)], runtime.env)
      await ready(runtime.origin, runtime.ui)
      return runtime
    } catch (error) { await runtime.close(); throw error }
  }

  private async startApi() {
    this.api = owned(`${root}/.venv/bin/python`, ['-B', '-m', 'uvicorn', 'tests.authoring_native_fixture:create_test_app', '--factory', '--host', '127.0.0.1', '--port', String(this.apiPort), '--no-access-log'], this.env)
    await ready(`http://127.0.0.1:${this.apiPort}/health`, this.api)
    if (!this.api.child.pid) throw new Error('Owned API has no process identity')
    this.generations.push(this.api.child.pid)
  }

  async openBrowser(browserType: BrowserType) {
    if (this.context) throw new Error('Close the actual previous browser before reopening')
    this.context = await browserType.launchPersistentContext(this.profile, {
      headless: true, viewport: { width: 1440, height: 900 }, baseURL: this.origin,
      ...(existsSync('/usr/bin/google-chrome') ? { executablePath: '/usr/bin/google-chrome' } : {}),
    })
    this.context.setDefaultTimeout(10_000)
    this.context.setDefaultNavigationTimeout(20_000)
    return this.context
  }

  async closeBrowser() {
    await this.context?.close()
    this.context = undefined
  }

  async restartApiAfterBrowserClosed() {
    if (this.context) throw new Error('Restart acceptance requires the real browser to be closed first')
    await stopOwned(this.api)
    this.api = undefined
    await this.startApi()
    if (new Set(this.generations).size !== this.generations.length) throw new Error('API process identity did not change')
  }

  async authenticateOnly(page: Page) {
    // The launcher capability remains only in process memory. This performs
    // no workbench reset, storage clear, fixture replacement or state injection.
    const code = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'from services.api.app.config import Settings; from services.api.app.database import Database; from services.api.app.security import issue_bootstrap_code; d=Database(Settings.from_env()); d.initialize(); print(issue_bootstrap_code(d))'], { cwd: root, env: this.env, encoding: 'utf8' }).trim()
    await page.goto(`${this.origin}/#bootstrap=${code}`)
    await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
    await expect(page).toHaveURL(`${this.origin}/`)
  }

  control(): { test_only: true; proof_registered: boolean; base_url: string; model: string; adapter: 'compatible_chat'; answer_markdown: string; received_request_count: number; validated_request_count: number; invalid_request_count: number; request_body_sha256: string[] } {
    return JSON.parse(readFileSync(resolve(this.data, 'authoring-native-control.json'), 'utf8'))
  }

  async diagnosticControl(): Promise<unknown> {
    const value = JSON.parse(await readFile(resolve(this.data, 'authoring-native-control.json'), 'utf8'))
    return { test_only: value.test_only, received_request_count: value.received_request_count,
      validated_request_count: value.validated_request_count, invalid_request_count: value.invalid_request_count }
  }

  databaseIdentity() {
    const file = resolve(this.data, 'workspace.sqlite3')
    const stat = statSync(file)
    return { device: stat.dev, inode: stat.ino }
  }

  async close() {
    const results = await Promise.allSettled([this.closeBrowser(), stopOwned(this.ui), stopOwned(this.api)])
    const failures = results.filter((value): value is PromiseRejectedResult => value.status === 'rejected')
    if (failures.length) throw new AggregateError(failures.map(value => value.reason), 'Owned test runtime cleanup failed')
  }
}
