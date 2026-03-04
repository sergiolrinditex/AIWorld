import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Cargar .env desde la raíz del monorepo (donde está el .env principal)
  envDir: '..',
  server: {
    port: 5173,
    proxy: {
      // Proxy /api al backend FastAPI en desarrollo
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
