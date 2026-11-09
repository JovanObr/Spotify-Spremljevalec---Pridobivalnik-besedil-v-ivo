import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The Python API runs on 8888 (python -m api). In development, Vite forwards
// API and login requests to it, so the frontend can use relative URLs.
const API = "http://127.0.0.1:8888";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": API,
      "/login": API,
    },
  },
});
