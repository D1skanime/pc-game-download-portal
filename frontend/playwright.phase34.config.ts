import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["scan-lifecycle.spec.ts", "setup-recovery.spec.ts"],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90000,
  expect: { timeout: 20000 },
  outputDir: "/phase34/evidence/browser-results",
  reporter: [
    ["list"],
    ["json", { outputFile: "/phase34/evidence/browser-report.json" }],
  ],
  use: {
    baseURL: process.env.PHASE34_BASE_URL || "http://127.0.0.1:3344",
    browserName: "chromium",
    trace: "off",
    video: "off",
    screenshot: "off",
  },
});
