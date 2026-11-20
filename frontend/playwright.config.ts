import { defineConfig, devices } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";

const PORT = 8077;

const testDir = defineBddConfig({
  features: "e2e/features/*.feature",
  steps: "e2e/steps/*.ts",
});

export default defineConfig({
  testDir,
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: `http://localhost:${PORT}`, trace: "retain-on-failure" },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] }, grepInvert: /@celular/ },
    // Pixel 7 no Chromium (já instalado): viewport de celular, toque e DPR reais.
    { name: "celular", use: { ...devices["Pixel 7"] }, grep: /@celular/ },
  ],
  // API real em modo memória servindo o build do React na mesma origem.
  webServer: {
    command: `cd ../backend && poetry run uvicorn developer_myself.main:app --port ${PORT}`,
    url: `http://localhost:${PORT}/healthz`,
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      DM_STORAGE: "memory",
      DM_COOKIE_SECURE: "false",
      DM_STATIC_DIR: "../frontend/dist",
      DM_LOG_LEVEL: "WARNING",
    },
  },
});
