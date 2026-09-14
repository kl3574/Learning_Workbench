import {defineConfig} from '/tmp/m33-import-recovery-review-3cf2c34/apps/web/node_modules/@playwright/test/index.mjs';
export default defineConfig({testDir:'.',testMatch:'controlled-red.spec.ts',grep:/a reselected failed original/,workers:1,timeout:30000,reporter:'list',outputDir:'./controlled-red-results',use:{trace:'off',screenshot:'off'}});
