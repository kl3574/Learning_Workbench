import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
const apiHost = process.env.LEARNING_HOST ?? '127.0.0.1'
const apiPort = process.env.LEARNING_PORT ?? '8765'
const target = `http://${apiHost === '::1' ? '[::1]' : apiHost}:${apiPort}`
export default defineConfig({plugins:[react()],server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'/api':{target,changeOrigin:false},'/health':{target,changeOrigin:false}}},test:{environment:'jsdom',include:['src/**/*.test.{ts,tsx}']}})
