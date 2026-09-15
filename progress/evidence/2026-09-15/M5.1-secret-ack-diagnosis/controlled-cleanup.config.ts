import { defineConfig } from '<REPO>/apps/web/node_modules/@playwright/test/index.mjs'
export default defineConfig({testDir: '.', testMatch: 'controlled-cleanup.spec.ts', fullyParallel:false, workers:1, timeout:30000, reporter:[['list']], use:{trace:'off',screenshot:'off'}})
