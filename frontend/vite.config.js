import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { quasar, transformAssetUrls } from "@quasar/vite-plugin";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  define: {
    "process.env": {},
  },

  plugins: [
    vue({
      template: { transformAssetUrls },
    }),

    quasar(),
  ],

  resolve: {
    alias: {
      src: path.resolve(__dirname, "./src"),
      components: path.resolve(__dirname, "./src/components"),
      layouts: path.resolve(__dirname, "./src/layouts"),
      pages: path.resolve(__dirname, "./src/pages"),
      assets: path.resolve(__dirname, "./src/assets"),
      boot: path.resolve(__dirname, "./src/boot"),
      stores: path.resolve(__dirname, "./src/stores"),
    },
  },

  server: {
    port: 8080,
    proxy: {
      "/api": {
        target: process.env.API_URL || "http://localhost:5000",
        changeOrigin: true,
      },
      "/upload": {
        target: process.env.API_URL || "http://localhost:5000",
        changeOrigin: true,
      },
      "/webhook": {
        target: process.env.API_URL || "http://localhost:5000",
        changeOrigin: true,
      },
      "/login": {
        target: process.env.API_URL || "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
