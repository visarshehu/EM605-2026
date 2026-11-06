import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In `npm run dev`, forward /api to a backend on localhost:8000.
// In the container, nginx does this job instead (see nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
