import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Pitchsmith runs on 5174 (LabelOS holds 5173) and proxies /api to the backend
// on 8790. The UI only ever calls /api/... — the invariant inherited from
// LabelOS that keeps packaging a shell swap.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { "/api": "http://127.0.0.1:8790" },
  },
});
