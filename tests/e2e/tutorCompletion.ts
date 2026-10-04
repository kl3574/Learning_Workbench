import { expect, type Locator } from '../../apps/web/node_modules/@playwright/test/index.mjs'

/** Keep this one completion observation within the original five-second budget. */
export async function expectTutorCompletion(completed: Locator): Promise<void> {
  await expect(completed).toBeVisible({ timeout: 5000 })
}
