import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { parkingApiDevPlugin } from './vite-plugins/parkingApiDev'

// https://vite.dev/config/
/** Явный IPv4: на Windows `localhost` иногда резолвится в ::1, прокси отдаёт 502 */
const apiTarget = 'http://127.0.0.1:3001'
const backendTarget = 'http://127.0.0.1:8000'

const apiProxy = {
  target: apiTarget,
  changeOrigin: true,
}

export default defineConfig({
  plugins: [vue(), parkingApiDevPlugin()],
  server: {
    proxy: {
      '/api': apiProxy,
      '/uploads': { target: backendTarget, changeOrigin: true },
    },
  },
  preview: {
    proxy: {
      '/api': apiProxy,
      '/uploads': { target: backendTarget, changeOrigin: true },
    },
  },
})
