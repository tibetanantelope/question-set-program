import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/login': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/agent': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/profile': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/sessions': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/learning': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
