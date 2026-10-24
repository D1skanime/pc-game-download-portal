import { defineConfig } from "@playwright/test";
import preview from "./playwright.screenshot-management.config";

// Reuse the owned fail-closed static preview and the existing API fixtures.
if (!process.env.ZA_SCREENSHOT_BUILD_ROOT)
  throw new Error(
    "Set ZA_SCREENSHOT_BUILD_ROOT to the owned product brand build",
  );
export default defineConfig({
  ...preview,
  testMatch: "project-brand.spec.ts",
  outputDir: process.env.ZA_BRAND_OUTPUT_DIR ?? "/tmp/za-project-brand-results",
});
