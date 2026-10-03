# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: import-admission.spec.ts >> real independent Policy preserves an open import selection and restores only explicit admission
- Location: ../../tests/e2e/import-admission.spec.ts:65:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('✓ UI 会话已保存')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText('✓ UI 会话已保存') with timeout 5000ms
  - waiting for getByText('✓ UI 会话已保存')

```

```yaml
- main:
  - heading "工作台尚未恢复" [level=1]
  - status: 尚未建立本机会话。请从一次性启动链接打开；当前未确认 UI 保留。
  - button "重试连接"
```

# Test source

```ts
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
  63  |     if (service.child.exitCode !== null || service.child.signalCode !== null) throw new Error(`Owned test server exited before readiness: ${service.output()}`)
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
> 138 |     await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
      |                                                ^ Error: expect(locator).toBeVisible() failed
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