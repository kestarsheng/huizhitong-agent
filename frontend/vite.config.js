import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api/agent': { target: 'http://localhost:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api\/agent/, '/internal') },
      '/api': { target: 'http://localhost:8083', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '') }
    }
  }
})
