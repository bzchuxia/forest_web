import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  plugins: [
    vue(),
    // 移除所有自定义配置，使用插件默认值，兼容性最好
    cesium()
  ],
  // 移除 CESIUM_BASE_URL 配置，这是解决静态资源路径问题的关键
  define: {},
  optimizeDeps: {
    include: ['cesium']
  },
  resolve: {
    extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.geojson', '.vue']
  },
  server: {
    cors: true,
    strictPort: false
  }
})