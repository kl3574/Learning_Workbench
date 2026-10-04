import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { expectTutorCompletion } from './tutorCompletion'

for (const delay of [200, 4900]) {
  test(`Tutor completion observer sees synthetic visible state after ${delay} ms`, async ({ page }) => {
    await page.setContent('<section aria-label="真实问答线程与任务"><h3>真实任务状态：running</h3></section>')
    await page.evaluate(delay => {
      setTimeout(() => { document.querySelector('h3')!.textContent = '真实任务状态：completed' }, delay)
    }, delay)
    const completed = page.getByRole('region', { name: '真实问答线程与任务', exact: true })
      .getByRole('heading', { name: '真实任务状态：completed', exact: true })
    await expectTutorCompletion(completed)
    expect(await completed.isVisible()).toBe(true)
  })
}

test('Tutor completion observer rejects when the exact completed heading never appears', async ({ page }) => {
  await page.setContent('<section aria-label="真实问答线程与任务"><h3>真实任务状态：running</h3></section><h3>真实任务状态：completed</h3>')
  const completed = page.getByRole('region', { name: '真实问答线程与任务', exact: true })
    .getByRole('heading', { name: '真实任务状态：completed', exact: true })
  await expect(expectTutorCompletion(completed)).rejects.toThrow()
  expect(await completed.isVisible()).toBe(false)
  await expect(page.getByRole('heading', { name: '真实任务状态：running', exact: true })).toBeVisible()
})
