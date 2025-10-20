import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://api:8000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://api:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: '../api/static',
    emptyOutDir: true,
  },
})
