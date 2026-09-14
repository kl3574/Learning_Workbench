import { defineConfig } from 'vitest/config'
export default defineConfig({ root: '<HOOK_REVIEW>', test: { environment: 'jsdom', include: ['*.test.ts'], testTimeout: 5000 }, server: { fs: { allow: ['<HOOK_REVIEW>', '<WORKTREE>'] } } })
