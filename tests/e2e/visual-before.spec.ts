import { test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { bootstrap, openSyntheticLesson } from './helpers'
test('capture initial running interface for independent visual review', async ({ page }) => {
  await bootstrap(page)
  await page.screenshot({ path: '../../docs/ui/m1-before-empty-1440.png' })
  await openSyntheticLesson(page)
  await page.screenshot({ path: '../../docs/ui/m1-before-1440.png' })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: '../../docs/ui/m1-before-390.png' })
})
