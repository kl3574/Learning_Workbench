import { defineConfig } from '[REVIEW_UI_WORKTREE]/apps/web/node_modules/@playwright/test/index.mjs'
export default defineConfig({testDir: '[REVIEW_UI_WORKTREE]/tests/e2e',testMatch:'draft-review.spec.ts',workers:1,fullyParallel:false,retries:0,timeout:30000,reporter:[['list']],outputDir:'[REVIEW_UI_PRIVATE_EVIDENCE]/native-output-v5',use:{headless:true,trace:'off',screenshot:'only-on-failure'}})
