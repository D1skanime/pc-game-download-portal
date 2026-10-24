import { defineConfig } from "@playwright/test";
import { staticPreview } from "./e2e/fixtures/static-preview";

if (process.env.E2E_BASE_URL)
  throw new Error("Screenshot tests require the isolated local preview");
// The owned build directory avoids shared outputs; this static server has no backend proxy.
// Prepare it with npm run build -- --outDir /tmp/za-37-04-dist.
const buildRoot = process.env.ZA_SCREENSHOT_BUILD_ROOT ?? "/tmp/za-37-04-dist";
export default defineConfig({
  testDir: "./e2e",
  testMatch: "screenshot-management.spec.ts",
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: "list",
  outputDir:
    process.env.ZA_SCREENSHOT_OUTPUT_DIR ??
    "../.planning/phases/37-zockarchive-screenshot-management-ui-redesign/evidence/browser-results",
  use: {
    baseURL: "http://127.0.0.1:4177",
    serviceWorkers: "block",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    hasTouch: true,
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        launchOptions: {
          executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
        },
      },
    },
  ],
  webServer: staticPreview(buildRoot),
});
