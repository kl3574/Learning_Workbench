import { expect, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
const root = resolve(import.meta.dirname, '../..')
export async function bootstrap(page: Page) {
  // Capture only in process memory; never log or attach launcher secrets.
  const code = execFileSync(`${root}/.venv/bin/python`, ['-c', 'from services.api.app.config import Settings; from services.api.app.database import Database; from services.api.app.security import issue_bootstrap_code; d=Database(Settings.from_env()); d.initialize(); print(issue_bootstrap_code(d))'], { cwd: root, env: { ...process.env, LEARNING_DATA_DIR: process.env.LEARNING_E2E_DATA_DIR, LEARNING_UI_ORIGIN: 'http://127.0.0.1:5173' }, encoding: 'utf8' }).trim()
  await page.goto(`/#bootstrap=${code}`)
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  await expect(page).toHaveURL('http://127.0.0.1:5173/')
  // Unload the old Shell before resetting its server session and browser cache.
  const health = await page.goto('/health')
  expect(health?.status()).toBe(200)
  expect(health?.headers()['content-type']).toContain('application/json')
  await page.evaluate(async () => {
    const auth = await (await fetch('/api/v1/session')).json()
    const current = await (await fetch('/api/v1/workbench/session')).json()
    const session = { revision: current.revision, course_ref: null, navigation: 'route', tabs: [], active_tab_id: null, expanded_keys: [], directory_scroll: 0, nav_width: 300, agent_width: 368, nav_collapsed: false, agent_collapsed: false }
    const response = await fetch('/api/v1/workbench/session', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf_token }, body: JSON.stringify({ expected_revision: current.revision, session }) })
    if (!response.ok) throw new Error(`Reset failed ${response.status}`)
    localStorage.clear()
  })
  await page.goto('/')
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
}
export async function openSyntheticLesson(page: Page) {
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  await page.getByRole('button', { name: '浏览合成示例课程' }).click()
  await page.getByRole('navigation', { name: '学习主导航' }).getByRole('button', { name: '教材' }).click()
  await page.getByRole('button', { name: '打开示例小节' }).click()
  await expect(page.locator('.reader-content h1')).toContainText('1.2')
  await expect(page.locator('.reader-content svg').first()).toBeVisible()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
}
