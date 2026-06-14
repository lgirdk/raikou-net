import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // During `npm run dev`, proxy /api/* directly to the orchestrator.
    // In production the FastAPI backend handles the proxy instead.
    proxy: {
      '/api': {
        target: 'http://192.168.150.10:8080',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
