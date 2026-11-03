import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// O proxy mantém a MESMA origem que o cookie SameSite=Strict exige (ADR-0009, ADR-0011).
const apiTarget = process.env.API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: { "/api": { target: apiTarget, changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
