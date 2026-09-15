# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: route-draft-input.spec.ts >> native route goal input survives its own initial draft load_first delivery after focus
- Location: tests/e2e/route-draft-input.spec.ts:9:60

# Error details

```
Error: Owned test server exited before readiness: Node 24.21.0 is required; run make setup.

```

# Test source

```ts
  1   | import { spawn, execFileSync, type ChildProcess } from 'node:child_process'
  2   | import { mkdtempSync, existsSync, statSync } from 'node:fs'
  3   | import { createServer } from 'node:net'
  4   | import { tmpdir } from 'node:os'
  5   | import { resolve } from 'node:path'
  6   | import { setTimeout as pause } from 'node:timers/promises'
  7   | import { expect, type BrowserContext, type BrowserType, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  8   | 
  9   | const root = resolve(import.meta.dirname, '../..')
  10  | type OwnedProcess = { child: ChildProcess; exit: Promise<void>; output: () => string }
  11  | const ownedGroups = new Set<number>()
  12  | // Playwright can dispose a timed-out worker before its async finally finishes.
  13  | // A synchronous exit hook still signals only this worker's retained child groups.
  14  | process.once('exit', () => {
  15  |   for (const pid of ownedGroups) {
  16  |     try { process.kill(-pid, 'SIGTERM') } catch { /* An already exited owned group needs no cleanup. */ }
  17  |   }
  18  | })
  19  | 
  20  | async function availablePort() {
  21  |   const socket = createServer()
  22  |   await new Promise<void>((accept, reject) => { socket.once('error', reject); socket.listen(0, '127.0.0.1', accept) })
  23  |   const address = socket.address()
  24  |   if (!address || typeof address === 'string') throw new Error('No loopback test port')
  25  |   await new Promise<void>((accept, reject) => socket.close(error => error ? reject(error) : accept()))
  26  |   return address.port
  27  | }
  28  | 
  29  | function owned(command: string, args: string[], env: NodeJS.ProcessEnv): OwnedProcess {
  30  |   const child = spawn(command, args, { cwd: root, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] })
  31  |   if (child.pid) ownedGroups.add(child.pid)
  32  |   let output = ''
  33  |   for (const stream of [child.stdout, child.stderr]) stream?.on('data', chunk => { output = (output + String(chunk)).slice(-8192) })
  34  |   const exit = new Promise<void>(accept => {
  35  |     const done = () => { if (child.pid) ownedGroups.delete(child.pid); accept() }
  36  |     child.once('close', done); child.once('error', done)
  37  |   })
  38  |   return { child, exit, output: () => output }
  39  | }
  40  | 
  41  | async function stopOwned(value: OwnedProcess | undefined) {
  42  |   if (!value || value.child.exitCode !== null || value.child.signalCode !== null) return
  43  |   const pid = value.child.pid
  44  |   if (!pid) { await value.exit; return }
  45  |   // Only signal the new process group created and retained by this harness.
  46  |   // Never find/kill an existing server by its port or stop a user process.
  47  |   try { process.kill(-pid, 'SIGTERM') } catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error }
  48  |   let timer: ReturnType<typeof setTimeout> | undefined
  49  |   const forced = new Promise<void>(accept => {
  50  |     timer = setTimeout(() => {
  51  |       try { process.kill(-pid, 'SIGKILL') } catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ESRCH') throw error }
  52  |       accept()
  53  |     }, 5000)
  54  |   })
  55  |   await Promise.race([value.exit, forced])
  56  |   clearTimeout(timer)
  57  |   await value.exit
  58  | }
  59  | 
  60  | async function ready(url: string, service: OwnedProcess) {
  61  |   const deadline = Date.now() + 20_000
  62  |   while (Date.now() < deadline) {
> 63  |     if (service.child.exitCode !== null || service.child.signalCode !== null) throw new Error(`Owned test server exited before readiness: ${service.output()}`)
      |                                                                                     ^ Error: Owned test server exited before readiness: Node 24.21.0 is required; run make setup.
  64  |     try {
  65  |       const response = await fetch(url, { signal: AbortSignal.timeout(1000) })
  66  |       if (response.ok) return
  67  |     } catch { /* Wait for this new process to bind its loopback port. */ }
  68  |     await pause(50)
  69  |   }
  70  |   throw new Error(`Owned test server did not become ready: ${service.output()}`)
  71  | }
  72  | 
  73  | /** A private synthetic workspace, a persistent Chrome profile and actual API restarts. */
  74  | export class RestartRuntime {
  75  |   readonly data = mkdtempSync(`${tmpdir()}/learning-workbench-reader-restart-data-`)
  76  |   readonly profile = mkdtempSync(`${tmpdir()}/learning-workbench-reader-restart-browser-`)
  77  |   readonly generations: number[] = []
  78  |   readonly origin: string
  79  |   private readonly env: NodeJS.ProcessEnv
  80  |   private api?: OwnedProcess
  81  |   private ui?: OwnedProcess
  82  |   private context?: BrowserContext
  83  | 
  84  |   private constructor(private readonly apiPort: number, uiPort: number) {
  85  |     this.origin = `http://127.0.0.1:${uiPort}`
  86  |     this.env = { ...process.env, LEARNING_DATA_DIR: this.data, LEARNING_UI_ORIGIN: this.origin, LEARNING_HOST: '127.0.0.1', LEARNING_PORT: String(apiPort) }
  87  |   }
  88  | 
  89  |   static async start() {
  90  |     const apiPort = await availablePort()
  91  |     let uiPort = await availablePort()
  92  |     while (uiPort === apiPort) uiPort = await availablePort()
  93  |     const runtime = new RestartRuntime(apiPort, uiPort)
  94  |     try {
  95  |       await runtime.startApi()
  96  |       runtime.ui = owned('bash', ['scripts/node.sh', 'npm', '--prefix', 'apps/web', 'run', 'dev', '--', '--port', String(uiPort)], runtime.env)
  97  |       await ready(runtime.origin, runtime.ui)
  98  |       return runtime
  99  |     } catch (error) { await runtime.close(); throw error }
  100 |   }
  101 | 
  102 |   private async startApi() {
  103 |     this.api = owned(`${root}/.venv/bin/python`, ['-B', '-m', 'uvicorn', 'services.api.app.main:create_app', '--factory', '--host', '127.0.0.1', '--port', String(this.apiPort), '--no-access-log'], this.env)
  104 |     await ready(`http://127.0.0.1:${this.apiPort}/health`, this.api)
  105 |     if (!this.api.child.pid) throw new Error('Owned API has no process identity')
  106 |     this.generations.push(this.api.child.pid)
  107 |   }
  108 | 
  109 |   async openBrowser(browserType: BrowserType) {
  110 |     if (this.context) throw new Error('Close the actual previous browser before reopening')
  111 |     this.context = await browserType.launchPersistentContext(this.profile, {
  112 |       headless: true, viewport: { width: 1440, height: 900 }, baseURL: this.origin,
  113 |       ...(existsSync('/usr/bin/google-chrome') ? { executablePath: '/usr/bin/google-chrome' } : {}),
  114 |     })
  115 |     this.context.setDefaultTimeout(10_000)
  116 |     this.context.setDefaultNavigationTimeout(20_000)
  117 |     return this.context
  118 |   }
  119 | 
  120 |   async closeBrowser() {
  121 |     await this.context?.close()
  122 |     this.context = undefined
  123 |   }
  124 | 
  125 |   async restartApiAfterBrowserClosed() {
  126 |     if (this.context) throw new Error('Restart acceptance requires the real browser to be closed first')
  127 |     await stopOwned(this.api)
  128 |     this.api = undefined
  129 |     await this.startApi()
  130 |     if (new Set(this.generations).size !== this.generations.length) throw new Error('API process identity did not change')
  131 |   }
  132 | 
  133 |   async authenticateOnly(page: Page) {
  134 |     // The launcher capability remains only in process memory. This performs
  135 |     // no workbench reset, storage clear, fixture replacement or state injection.
  136 |     const code = execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', 'from services.api.app.config import Settings; from services.api.app.database import Database; from services.api.app.security import issue_bootstrap_code; d=Database(Settings.from_env()); d.initialize(); print(issue_bootstrap_code(d))'], { cwd: root, env: this.env, encoding: 'utf8' }).trim()
  137 |     await page.goto(`${this.origin}/#bootstrap=${code}`)
  138 |     await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  139 |     await expect(page).toHaveURL(`${this.origin}/`)
  140 |   }
  141 | 
  142 |   databaseIdentity() {
  143 |     const file = resolve(this.data, 'workspace.sqlite3')
  144 |     const stat = statSync(file)
  145 |     return { device: stat.dev, inode: stat.ino }
  146 |   }
  147 | 
  148 |   async close() {
  149 |     const results = await Promise.allSettled([this.closeBrowser(), stopOwned(this.ui), stopOwned(this.api)])
  150 |     const failures = results.filter((value): value is PromiseRejectedResult => value.status === 'rejected')
  151 |     if (failures.length) throw new AggregateError(failures.map(value => value.reason), 'Owned test runtime cleanup failed')
  152 |   }
  153 | }
  154 | 
```