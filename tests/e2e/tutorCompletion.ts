import { expect, type Locator } from '../../apps/web/node_modules/@playwright/test/index.mjs'

/** Sample only this locator more densely; keep the original five-second budget. */
export async function expectTutorCompletion(completed: Locator): Promise<void> {
  await expect.poll(() => completed.isVisible(), { timeout: 5000, intervals: [25] }).toBe(true)
}
