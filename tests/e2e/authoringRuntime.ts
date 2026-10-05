import { execFileSync } from 'node:child_process'
import { mkdtempSync, existsSync, statSync, readFileSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { expect, type BrowserContext, type BrowserType, type Page } from '../../apps/web/node_modules/@playwright/test/index.js'
import { availablePort, owned, ready, readyOwnedUi, stopOwned, withOwnedStartup, type OwnedProcess } from './ownedStartup'

const root = resolve(import.meta.dirname, '../..')
type AuthoringScenario = 'complete' | 'no_proof' | 'lesson' | 'practice_set' | 'assessment'
type AuthoringFactory = 'single' | 'groups'
const factories = {
  single: 'tests.authoring_native_fixture:create_test_app',
  groups: 'tests.authoring_group_native_fixture:create_test_app',
} as const
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

  private constructor(private readonly apiPort: number, uiPort: number, scenario: AuthoringScenario, private readonly factory: AuthoringFactory) {
    this.origin = `http://127.0.0.1:${uiPort}`
    this.env = { ...process.env, LEARNING_DATA_DIR: this.data, LEARNING_UI_ORIGIN: this.origin, LEARNING_HOST: '127.0.0.1', LEARNING_PORT: String(apiPort), AUTHORING_NATIVE_SCENARIO: scenario }
  }

  static async start(scenario: 'complete' | 'no_proof', factory?: 'single'): Promise<AuthoringRuntime>
  static async start(scenario: 'lesson' | 'practice_set' | 'assessment', factory: 'groups'): Promise<AuthoringRuntime>
  static async start(): Promise<AuthoringRuntime>
  static async start(scenario: AuthoringScenario = 'no_proof', factory: AuthoringFactory = 'single') {
    if (factory === 'single' ? !['complete', 'no_proof'].includes(scenario) : factory !== 'groups' || !['lesson', 'practice_set', 'assessment'].includes(scenario)) throw new Error('Unknown closed Authoring test factory/scenario')
    return withOwnedStartup(async deadline => {
      const apiPort = await availablePort()
      let uiPort = await availablePort()
      while (uiPort === apiPort) {
        if (Date.now() >= deadline) throw new Error('No distinct loopback test ports before readiness deadline')
        uiPort = await availablePort()
      }
      const runtime = new AuthoringRuntime(apiPort, uiPort, scenario, factory)
      try {
        // API failures never enter the UI-only bind-collision retry path.
        await runtime.startApi(deadline)
        runtime.ui = owned('bash', ['scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'dev', '--', '--port', String(uiPort)], runtime.env)
        await readyOwnedUi(uiPort, runtime.ui, deadline)
        return runtime
      } catch (error) { await runtime.close(); throw error }
    })
  }

  private async startApi(deadline?: number) {
    this.api = owned(`${root}/.venv/bin/python`, ['-B', '-m', 'uvicorn', factories[this.factory], '--factory', '--host', '127.0.0.1', '--port', String(this.apiPort), '--no-access-log'], this.env)
    await ready(`http://127.0.0.1:${this.apiPort}/health`, this.api, { deadline })
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

  control(): { api_pid?: number; target_initialization?: 'published_once' | 'reused_exact'; target_refs?: unknown[]; test_only: true; proof_registered: boolean; base_url: string; model: string; adapter: 'compatible_chat'; answer_markdown: string; received_request_count: number; validated_request_count: number; invalid_request_count: number; request_body_sha256: string[] } {
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
