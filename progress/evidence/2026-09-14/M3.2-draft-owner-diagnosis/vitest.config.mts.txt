import { defineConfig } from 'vitest/config'
export default defineConfig({root:'__PROBE_DIRECTORY__',test:{environment:'jsdom',include:['*.test.tsx']}})
