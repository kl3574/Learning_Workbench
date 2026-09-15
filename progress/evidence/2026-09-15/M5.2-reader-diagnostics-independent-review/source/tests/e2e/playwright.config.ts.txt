import { defineConfig } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdtempSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
const root = resolve(import.meta.dirname, '../..')
const data = process.env.LEARNING_E2E_DATA_DIR ?? mkdtempSync(`${tmpdir()}/learning-workbench-e2e-`)
process.env.LEARNING_E2E_DATA_DIR = data
export default defineConfig({
  testDir: '.', testMatch: '*.spec.ts', fullyParallel: false, workers: 1, timeout: 30000,
  reporter: [['list']], outputDir: process.env.LEARNING_E2E_OUTPUT_DIR ?? resolve(root, '.local_data/e2e-results'),
  use: { baseURL: 'http://127.0.0.1:5173', headless: true, trace: 'off', screenshot: 'only-on-failure', viewport: { width: 1440, height: 900 }, launchOptions: existsSync('/usr/bin/google-chrome') ? { executablePath: '/usr/bin/google-chrome' } : {} },
  webServer: [
    { command: `${root}/.venv/bin/python -m uvicorn services.api.app.main:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log`, cwd: root, url: 'http://127.0.0.1:8765/health', reuseExistingServer: false, env: { LEARNING_DATA_DIR: data, LEARNING_UI_ORIGIN: 'http://127.0.0.1:5173', LEARNING_PORT: '8765' } },
    { command: 'bash scripts/node.sh npm --prefix apps/web run dev', cwd: root, url: 'http://127.0.0.1:5173', reuseExistingServer: false },
  ],
})
