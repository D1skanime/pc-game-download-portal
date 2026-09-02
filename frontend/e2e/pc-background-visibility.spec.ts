import { expect, test } from "@playwright/test";
import { gotoHydrated, seedUiState, STORAGE_STATE } from "./fixtures/auth";

test.describe("PC local background visibility", () => {
  test.use({ storageState: STORAGE_STATE.admin });

  test("keeps selected local background artwork visibly present in light theme", async ({
    page,
  }) => {
    test.skip(!process.env.PC_E2E_ROM_ID, "isolated PC fixture is required");
    await seedUiState(page, "light");
    await gotoHydrated(page, `/rom/${process.env.PC_E2E_ROM_ID}`);

    await expect(page.locator(".r-v2-bg__layer--active")).toHaveAttribute(
      "style",
      /pc-media/,
    );
    await expect
      .poll(() =>
        page
          .locator(".r-v2-bg__layer--active")
          .evaluate((element) => getComputedStyle(element).filter),
      )
      .not.toContain("blur");
    const strongestLightWash = await page
      .locator(".r-v2-bg__overlay")
      .evaluate((element) => {
        const alphas = [
          ...getComputedStyle(element).backgroundImage.matchAll(
            /\/ ([\d.]+)\)/g,
          ),
        ].map((match) => Number(match[1]));
        return Math.max(...alphas);
      });

    expect(strongestLightWash).toBeLessThanOrEqual(0.58);
  });

  test("offers a usable platform neighbour when a game opens directly", async ({
    page,
  }) => {
    test.skip(!process.env.PC_E2E_ROM_ID, "isolated PC fixture is required");
    await seedUiState(page, "light");
    await gotoHydrated(page, `/rom/${process.env.PC_E2E_ROM_ID}`);

    const navigation = page.locator(".prev-next-nav");
    await expect(navigation).toBeVisible();
    await expect(navigation.locator("button")).toHaveCount(2);

    const before = page.url();
    await navigation.locator("button:not([disabled])").first().click();
    await expect.poll(() => page.url()).not.toBe(before);
  });
});
