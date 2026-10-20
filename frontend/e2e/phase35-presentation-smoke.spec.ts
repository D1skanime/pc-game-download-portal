import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { clearMetadataProviders, login } from "./fixtures/phase34";
import { presentation } from "./fixtures/phase35-presentation";

test("debug-only small-fixture presentation matrix", async ({ page }) => {
  await login(page);
  await page.goto("/scan");
  await clearMetadataProviders(page);
  const submitted = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/scan-operations",
  );
  await page.locator(".r-v2-scan-card__start").click();
  const id = (await (await submitted).json()).id;
  await expect
    .poll(
      async () => {
        const response = await page.request.get("/api/scan-operations/" + id);
        return (await response.json()).state;
      },
      { timeout: 180000 },
    )
    .toBe("completed");
  const warm = await (
    await page.request.get("/api/scan-operations/" + id)
  ).json();
  const checks: Record<string, boolean> = {};
  const variants: string[] = [];
  const result = await presentation(
    page,
    warm,
    async (snapshot) =>
      page.evaluate(async (snapshot) => {
        const path = "/src/v2/composables/useScanOperationStatus/index.ts";
        const module = await import(path);
        const status = module.useScanOperationStatus();
        const accepted = status.accept(snapshot);
        status.dispose();
        return accepted;
      }, snapshot),
    async (name) => {
      await page.screenshot({
        path: "/phase34/evidence/smoke-" + name + ".png",
        fullPage: true,
      });
      writeFileSync(
        "/phase34/evidence/smoke-" + name + ".html",
        await page.content(),
      );
    },
    checks,
    variants,
  );
  writeFileSync(
    "/phase34/evidence/presentation-smoke.json",
    JSON.stringify(
      {
        kind: "presentation-smoke",
        debug_only: true,
        passed: test.info().errors.length === 0,
        checks,
        variants,
        result,
      },
      null,
      2,
    ),
  );
});
