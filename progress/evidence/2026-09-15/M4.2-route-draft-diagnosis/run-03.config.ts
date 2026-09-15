import { defineConfig } from '<ACCEPTANCE_CACHE>/m42-4cf13f7/apps/web/node_modules/@playwright/test/index.mjs'
export default defineConfig({testDir:'<DIAGNOSIS_CACHE>',testMatch:'routes-observed.spec.ts',fullyParallel:false,workers:1,timeout:30000,reporter:[['list']],outputDir:'<DIAGNOSIS_CACHE>/run-03-artifacts',use:{headless:true,trace:'off',screenshot:'off',viewport:{width:1440,height:900}}})
