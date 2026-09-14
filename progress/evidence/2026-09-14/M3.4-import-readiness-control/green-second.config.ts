import {defineConfig} from '/tmp/m33-import-recovery-review-3cf2c34/apps/web/node_modules/@playwright/test/index.mjs';
export default defineConfig({testDir:'.',testMatch:'controlled-green-second.spec.ts',grep:/a reselected failed original/,workers:1,timeout:30000,reporter:'list',outputDir:'./controlled-green-second-results',use:{trace:'off',screenshot:'off'}});
