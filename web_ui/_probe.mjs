import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// 临时探针：打印 manualChunks 收到的 id 格式
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('Layout') || id.includes('store')) {
            console.log('MATCH:', id);
            return 'layout-vendor';
          }
          return undefined;
        },
      },
    },
  },
});
