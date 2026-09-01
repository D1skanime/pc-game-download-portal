import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { gotoHydrated, seedUiState, STORAGE_STATE } from "./fixtures/auth";

const fixtureRoot = process.env.PC_E2E_FIXTURE_ROOT
  ? path.join(process.env.PC_E2E_FIXTURE_ROOT, "roms", "win", "Cyberpunk2077")
  : path.resolve(
      import.meta.dirname,
      "../../tests/fixtures/pc-integration-model/source-library/Cyberpunk2077",
    );
const SELECTED_TITLE = "Cyberpunk 2077";
const SELECTED_DESCRIPTION =
  "Phase 10 selected LaunchBox metadata for the isolated PC fixture.";

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
    const romId = process.env.PC_E2E_ROM_ID;
    let selectionApplied = false;
    let selectionRequests = 0;
    await page.route(`**/api/roms/${romId}/pc-metadata-candidates`, (route) =>
      route.fulfill({
        json: {
          expected_version: "2026-09-01T00:00:00Z",
          providers: {
            launchbox: {
              provider: "launchbox",
              available: true,
              candidates: [
                {
                  id: "phase10-launchbox-cyberpunk",
                  provider: "launchbox",
                  title: SELECTED_TITLE,
                  provider_ids: { launchbox_id: "2077" },
                  description_available: true,
                  media: [
                    {
                      kind: "cover",
                      url: "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==",
                    },
                  ],
                },
              ],
              reason: null,
            },
          },
        },
      }),
    );
    await page.route(`**/api/roms/${romId}/pc-metadata-selection`, (route) => {
      selectionRequests += 1;
      const selection = route.request().postDataJSON();
      expect(selection).toEqual({
        candidate_id: "phase10-launchbox-cyberpunk",
        expected_version: "2026-09-01T00:00:00Z",
      });
      selectionApplied = true;
      return route.fulfill({
        json: {
          candidate_id: "phase10-launchbox-cyberpunk",
          expected_version: "2026-09-01T00:00:01Z",
        },
      });
    });
    await page.route(`**/api/roms/${romId}`, async (route) => {
      if (!selectionApplied) return route.continue();
      const response = await route.fetch();
      const payload = await response.json();
      await route.fulfill({
        response,
        json: {
          ...payload,
          name: SELECTED_TITLE,
          summary: SELECTED_DESCRIPTION,
        },
      });
    });
    const before = await fixtureDigest();
    await seedUiState(page, "dark");
    const romResponse = page.waitForResponse((response) =>
      response.url().endsWith(`/api/roms/${romId}`),
    );
    await gotoHydrated(page, `/rom/${romId}?tab=pc-components`);
    const loadedRomResponse = await romResponse;
    expect(
      loadedRomResponse.ok(),
      `could not load the scanned PC ROM: ${loadedRomResponse.status()} ${await loadedRomResponse.text()}`,
    ).toBe(true);
    await expect(
      page.getByRole("heading", { name: "Base game", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "DLC", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Extras", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Needs classification", exact: true }),
    ).toBeVisible();
    const baseComponent = page.getByTestId("pc-component-base");
    const baseToggle = baseComponent.getByRole("button", { name: "base" });
    await baseToggle.click();
    await expect(
      baseComponent.getByText("SHA-256", { exact: true }).first(),
    ).toBeVisible();
    await page.getByTestId("find-pc-metadata").click();
    const apply = page.getByTestId("apply-pc-metadata");
    await expect(apply).toBeDisabled();
    expect(selectionRequests).toBe(0);
    await expect(page.getByText(SELECTED_TITLE, { exact: true })).toBeVisible();
    await page.getByTestId("pc-candidate-phase10-launchbox-cyberpunk").click();
    await expect(apply).toBeEnabled();
    await apply.click();
    await expect(page.getByText("LaunchBox", { exact: true })).toBeVisible();
    expect(selectionRequests).toBe(1);
    await page.getByRole("button", { name: "Close" }).click();
    await page.getByRole("tab", { name: "Overview" }).click();
    await expect(
      page.getByText(SELECTED_DESCRIPTION, { exact: true }),
    ).toBeVisible();
    expect(await fixtureDigest()).toBe(before);
  });
});
