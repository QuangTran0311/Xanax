import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: false },
      "/ws": { target: "ws://localhost:8000", ws: true },
      "/static": "http://localhost:8000",
      "/hub": "http://localhost:8000",
      "/workspace": "http://localhost:8000",
      "/taskrunner": "http://localhost:8000",
    },
  },
});
