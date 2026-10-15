import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // REST API
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // WebSocket — proxied transparently so WS connects to localhost:5173/ws/...
      '/ws': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
