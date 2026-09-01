import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { gotoHydrated, seedUiState, STORAGE_STATE } from "./fixtures/auth";

const fixtureRoot = path.resolve(
  import.meta.dirname,
  "../../tests/fixtures/pc-integration-model/source-library/ExamplePCGame",
);

async function fixtureDigest(directory = fixtureRoot): Promise<string> {
  const entries = await readdir(directory, { withFileTypes: true });
  const lines = await Promise.all(
    entries
      .sort((a, b) => a.name.localeCompare(b.name))
      .map(async (entry) => {
        const entryPath = path.join(directory, entry.name);
        if (entry.isDirectory()) return fixtureDigest(entryPath);
        const bytes = await readFile(entryPath);
        return `${path.relative(fixtureRoot, entryPath)}:${bytes.length}:${createHash("sha256").update(bytes).digest("hex")}`;
      }),
  );
  return createHash("sha256").update(lines.join("\n")).digest("hex");
}

test.describe("PC integration model", () => {
  test.use({ storageState: STORAGE_STATE.admin });

  test("reviews PC metadata without mutating the isolated source fixture", async ({
    page,
  }) => {
    test.skip(
      !process.env.PC_E2E_ROM_ID,
      "PC_E2E_ROM_ID isolated fixture is required",
    );
    const before = await fixtureDigest();
    await seedUiState(page, "dark");
    await gotoHydrated(
      page,
      `/rom/${process.env.PC_E2E_ROM_ID}?tab=pc-components`,
    );
    await expect(page.getByText("Base game")).toBeVisible();
    await expect(page.getByText("Updates")).toBeVisible();
    await expect(page.getByText("DLC")).toBeVisible();
    await page.getByTestId("pc-component-ExamplePCGame").click();
    await expect(page.getByText("SHA-256")).toBeVisible();
    await page.getByTestId("find-pc-metadata").click();
    const apply = page.getByTestId("apply-pc-metadata");
    await expect(apply).toBeDisabled();
    await page.locator("[data-testid^='pc-candidate-']").first().click();
    await expect(apply).toBeEnabled();
    await apply.click();
    expect(await fixtureDigest()).toBe(before);
  });
});
