import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The AI assistant runs as a small Python service (assistant_server.py);
// in development, /api calls are forwarded to it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  build: { chunkSizeWarningLimit: 700 },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8787" } },
});
