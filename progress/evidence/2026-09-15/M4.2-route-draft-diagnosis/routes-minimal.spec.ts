import { expect, test as base } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import { RestartRuntime } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/tests/e2e/restartRuntime.ts'
import { originalAssessmentPackage, importAssessmentPackage } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/tests/e2e/assessmentTestData.ts'
import type { PageRoute } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/packages/contracts/generated/api-types.ts'
const test = base.extend<{ runtime: RestartRuntime }>({
  runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright }, use) => { const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page); await use(page) },
})
test('the real new-route goal survives delivery of its own earlier initial draft after focus', async ({page}) => {
  await page.getByRole('button', { name: '创建路线', exact: true }).first().click()
  const editor = page.getByRole('dialog', { name: '创建路线', exact: true })
  await editor.getByRole('button', { name: '填写新路线', exact: true }).click()
  await editor.getByLabel('路线名称', { exact: true }).fill('原创路线与精确任务')
  await expect.poll(() => page.evaluate(() => ((window as Window & { __routeStoreGate?: { events: {kind:string}[] } }).__routeStoreGate?.events ?? []).some(value => value.kind === 'actual_initial_save_completed_result_held'))).toBe(true)
  const goal = editor.getByLabel('路线学习目标', { exact: true })
  await goal.fill('先读再练；提醒不锁定，人工标记不授予能力。')
  expect(await goal.inputValue()).toBe('先读再练；提醒不锁定，人工标记不授予能力。')
})
import { startObserver, finishObserver } from './observer-controlled-min'
test.beforeEach(async ({ page }, info) => { await startObserver(page, info) })
test.afterEach(async ({ page }, info) => { await finishObserver(page, info) })
