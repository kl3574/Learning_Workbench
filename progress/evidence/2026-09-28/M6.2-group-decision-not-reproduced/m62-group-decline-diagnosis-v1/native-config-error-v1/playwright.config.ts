import { defineConfig } from '../m62-group-decline-diagnosis-active/apps/web/node_modules/@playwright/test/index.mjs'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
const root = resolve(import.meta.dirname, '../m62-group-decline-diagnosis-active')
// The original selected case owns its dynamic API/UI runtime. Deliberately do
// not start the unrelated ordinary global 8765/5173 servers during diagnosis.
export default defineConfig({
  testDir: resolve(root, 'tests/e2e'), testMatch: 'authoring-groups.spec.ts', fullyParallel: false,
  workers: 1, retries: 0, timeout: 30000, reporter: [['list']], outputDir: resolve(import.meta.dirname, 'native-once/artifacts'),
  use: { baseURL: 'http://127.0.0.1:5173', headless: true, trace: 'off', screenshot: 'only-on-failure', viewport: { width: 1440, height: 900 }, launchOptions: existsSync('/usr/bin/google-chrome') ? { executablePath: '/usr/bin/google-chrome' } : {} },
})
