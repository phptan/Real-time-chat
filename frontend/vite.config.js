import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Trong Docker container, dùng service names thay vì localhost
const AUTH_TARGET = process.env.VITE_AUTH_URL || 'http://auth_service:8001'
const USER_TARGET = process.env.VITE_USER_URL || 'http://user_service:8002'
const CHAT_TARGET = process.env.VITE_CHAT_URL || 'http://chat_service:3002'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api/auth': {
        target: AUTH_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/auth/, ''),
      },
      '/api/users': {
        target: USER_TARGET,
        changeOrigin: true,
      },
      '/api/chat': {
        target: CHAT_TARGET,
        changeOrigin: true,
      },
      '/socket.io': {
        target: CHAT_TARGET,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
