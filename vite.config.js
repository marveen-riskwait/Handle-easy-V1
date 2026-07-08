import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The React SPA lives in src/front. Build output goes to ./dist, which the
// Flask app serves as static files in production (see src/app.py).
export default defineConfig({
  plugins: [react()],
  root: ".",
  server: {
    port: 3000,
  },
  build: {
    outDir: "dist",
  },
});
