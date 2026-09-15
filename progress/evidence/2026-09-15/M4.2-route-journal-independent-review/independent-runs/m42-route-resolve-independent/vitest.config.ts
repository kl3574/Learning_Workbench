import { defineConfig } from 'vitest/config'
export default defineConfig({test:{environment:'jsdom',include:['resolve-late-ack.test.tsx']}})
