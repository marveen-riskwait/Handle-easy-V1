import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The React SPA lives in src/front. Build output goes to ./dist, which the
// Flask app serves as static files in production (see src/app.py).
export default defineConfig({
  plugins: [react()],
  root: ".",
  server: {
    port: 3000,
    host: true,
    // Same-origin dev: the browser only ever talks to the Vite server, which
    // proxies /api to the Flask backend. This avoids CORS *and* cross-site
    // cookie problems — critical in GitHub Codespaces, where :3000 and :3001
    // are separate https hosts. Keep VITE_BACKEND_URL empty so the SPA calls
    // same-origin "/api" (services/api.js). Only port 3000 needs forwarding.
    proxy: {
      "/api": {
        target: "http://localhost:3001",
        changeOrigin: true,
      },
    },
    // Codespaces / tunnels serve the app under a *.app.github.dev host; Vite
    // rejects unknown hosts by default.
    allowedHosts: [".app.github.dev", "localhost", "127.0.0.1"],
  },
  build: {
    outDir: "dist",
  },
});
