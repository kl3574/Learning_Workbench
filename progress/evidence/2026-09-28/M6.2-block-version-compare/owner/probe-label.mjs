import { chromium } from '../m62-block-version-compare-active/apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome' })
try {
 const page = await browser.newPage()
 await page.setContent('<section aria-label="块修订比较"><label>左侧修订<select><option value="">请选择准确修订</option><option value="old">修订 1 · old</option><option value="new">修订 2 · new</option></select></label></section>')
 const counts = { exactLabel: await page.getByLabel('左侧修订', { exact: true }).count(), exactRole: await page.getByRole('combobox', { name: '左侧修订', exact: true }).count() }
 await page.getByRole('combobox', { name: '左侧修订', exact: true }).selectOption('old')
 const receipt = { counts, roleSelectedValue: await page.getByRole('combobox', { name: '左侧修订', exact: true }).inputValue(), aria: await page.locator('section').ariaSnapshot(), html: await page.locator('section').evaluate(node => node.outerHTML), scope: 'Synthetic same-DOM locator probe; no application/API or product acceptance' }
 writeFileSync(new URL('./probe-label-receipt.json', import.meta.url), JSON.stringify(receipt, null, 2)+'\n')
 console.log(JSON.stringify(receipt))
} finally { await browser.close() }
