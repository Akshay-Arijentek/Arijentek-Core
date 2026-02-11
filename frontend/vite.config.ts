import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const isProduction = mode === 'production';
  return {
    plugins: [
      vue(),
    ],
    base: isProduction ? '/assets/arijentek_core/frontend/' : '/',
    build: {
      outDir: '../arijentek_core/public/frontend',
      emptyOutDir: true,
      target: 'es2015',
      rollupOptions: {
        output: {
          entryFileNames: 'assets/main.js',
          chunkFileNames: 'assets/[name].js',
          assetFileNames: 'assets/[name].[ext]'
        }
      }
    },
    server: {
      host: true,
      port: 3000,
      proxy: {
        '^/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          headers: { Host: 'arijentek.localhost' },
        },
        '^/assets': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          headers: { Host: 'arijentek.localhost' },
        },
        '^/files': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          headers: { Host: 'arijentek.localhost' },
        }
      }
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
  }
})
