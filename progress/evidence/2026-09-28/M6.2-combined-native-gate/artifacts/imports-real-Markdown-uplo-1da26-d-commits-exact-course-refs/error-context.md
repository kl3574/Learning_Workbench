# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: imports.spec.ts >> real Markdown upload stays staged, previews and downloads exact bytes, restores and commits exact course refs
- Location: ../../tests/e2e/imports.spec.ts:111:1

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

# Test source

```ts
  1  | import { expect, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  2  | import { execFileSync } from 'node:child_process'
  3  | import { resolve } from 'node:path'
  4  | const root = resolve(import.meta.dirname, '../..')
  5  | export async function bootstrap(page: Page) {
  6  |   // Capture only in process memory; never log or attach launcher secrets.
  7  |   const code = execFileSync(`${root}/.venv/bin/python`, ['-c', 'from services.api.app.config import Settings; from services.api.app.database import Database; from services.api.app.security import issue_bootstrap_code; d=Database(Settings.from_env()); d.initialize(); print(issue_bootstrap_code(d))'], { cwd: root, env: { ...process.env, LEARNING_DATA_DIR: process.env.LEARNING_E2E_DATA_DIR, LEARNING_UI_ORIGIN: 'http://127.0.0.1:5173' }, encoding: 'utf8' }).trim()
  8  |   await page.goto(`/#bootstrap=${code}`)
> 9  |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
     |                                              ^ Error: expect(locator).toBeVisible() failed
  10 |   await expect(page).toHaveURL('http://127.0.0.1:5173/')
  11 |   // Unload the old Shell before resetting its server session and browser cache.
  12 |   const health = await page.goto('/health')
  13 |   expect(health?.status()).toBe(200)
  14 |   expect(health?.headers()['content-type']).toContain('application/json')
  15 |   await page.evaluate(async () => {
  16 |     const auth = await (await fetch('/api/v1/session')).json()
  17 |     const current = await (await fetch('/api/v1/workbench/session')).json()
  18 |     const session = { revision: current.revision, course_ref: null, navigation: 'route', tabs: [], active_tab_id: null, expanded_keys: [], directory_scroll: 0, nav_width: 300, agent_width: 368, nav_collapsed: false, agent_collapsed: false }
  19 |     const response = await fetch('/api/v1/workbench/session', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf_token }, body: JSON.stringify({ expected_revision: current.revision, session }) })
  20 |     if (!response.ok) throw new Error(`Reset failed ${response.status}`)
  21 |     localStorage.clear()
  22 |   })
  23 |   await page.goto('/')
  24 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  25 | }
  26 | export async function openSyntheticLesson(page: Page) {
  27 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  28 |   await page.getByRole('button', { name: '浏览合成示例课程' }).click()
  29 |   await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  30 |   await page.getByRole('button', { name: '打开示例小节' }).click()
  31 |   await expect(page.locator('.reader-content h1')).toContainText('1.2')
  32 |   await expect(page.locator('.reader-content svg').first()).toBeVisible()
  33 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  34 | }
  35 | 
```