import { defineConfig } from '<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-learning-route-diagnosis-active/apps/web/node_modules/@playwright/test/index.mjs'
export default defineConfig({
  testDir: '<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-learning-route-diagnosis-active/tests/e2e',
  testMatch: 'learning-state.spec.ts', fullyParallel: false, workers: 1, timeout: 30000,
  reporter: [['list']], outputDir: process.env.LEARNING_E2E_OUTPUT_DIR,
  use: { headless: true, trace: 'off', screenshot: 'only-on-failure', viewport: { width: 1440, height: 900 } },
})
