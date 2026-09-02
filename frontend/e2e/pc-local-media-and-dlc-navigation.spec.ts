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

test.describe("PC local media and DLC navigation", () => {
  test.use({ storageState: STORAGE_STATE.admin });

  test("selects owned artwork and opens a local DLC manifest without an IGDB popup", async ({
    page,
  }) => {
    test.skip(!process.env.PC_E2E_ROM_ID, "isolated PC fixture is required");
    const romId = process.env.PC_E2E_ROM_ID;
    const before = await fixtureDigest();
    let dlcComponentId: number | null = null;
    let dlcApplied = false;
    const popups: string[] = [];
    page.on("popup", (popup) => popups.push(popup.url()));

    await page.route(
      `**/api/roms/${romId}/pc-components/*/metadata-candidates`,
      async (route) => {
        dlcComponentId = Number(route.request().url().split("/").at(-2));
        await route.fulfill({
          json: {
            expected_version: "2026-09-02T00:00:00Z",
            providers: {
              igdb: {
                provider: "igdb",
                available: true,
                candidates: [
                  {
                    id: "phase11-phantom-liberty",
                    provider: "igdb",
                    title: "Phantom Liberty",
                    provider_ids: { igdb_id: 12345 },
                    description_available: true,
                    media: [],
                  },
                ],
              },
            },
          },
        });
      },
    );
    await page.route(
      `**/api/roms/${romId}/pc-components/*/metadata-selection`,
      async (route) => {
        expect(route.request().postDataJSON()).toEqual({
          candidate_id: "phase11-phantom-liberty",
          expected_version: "2026-09-02T00:00:00Z",
        });
        dlcApplied = true;
        await route.fulfill({
          json: {
            candidate_id: "phase11-phantom-liberty",
            component_id: dlcComponentId,
            expected_version: "2026-09-02T00:00:01Z",
          },
        });
      },
    );
    await page.route(`**/api/roms/${romId}`, async (route) => {
      const response = await route.fetch();
      if (!dlcApplied || !dlcComponentId) return route.fulfill({ response });
      const payload = await response.json();
      await route.fulfill({
        response,
        json: {
          ...payload,
          igdb_metadata: {
            ...(payload.igdb_metadata ?? {}),
            dlcs: [
              {
                id: 12345,
                name: "Phantom Liberty",
                slug: "phantom-liberty",
                type: "dlc",
                cover_url: "",
              },
            ],
          },
          components: payload.components.map((component: { id: number }) =>
            component.id === dlcComponentId
              ? {
                  ...component,
                  component_metadata: {
                    igdb_id: 12345,
                    moby_id: null,
                    sgdb_id: null,
                    launchbox_id: null,
                    name: "Phantom Liberty",
                    summary: null,
                    metadata_source: "igdb",
                    provider_metadata: null,
                  },
                }
              : component,
          ),
        },
      });
    });

    await seedUiState(page, "dark");
    await gotoHydrated(page, `/rom/${romId}?tab=pc-components`);
    const localArtwork = page.getByTestId("select-local-artwork");
    for (const role of ["cover", "background", "gallery"] as const) {
      await localArtwork.click();
      const candidate = page
        .locator('[data-testid^="local-art-candidate-"]')
        .filter({ hasText: "pc-local-media-fixture.png" });
      await candidate.click();
      await page.getByTestId(`local-art-role-${role}`).click();
      await page.getByTestId("apply-local-artwork").click();
      await expect(candidate).toBeHidden();
    }

    await page.evaluate(() => localStorage.setItem("settings.theme", "light"));
    await page.reload();
    const activeBackground = page.locator(".r-v2-bg__layer--active");
    await expect
      .poll(() =>
        activeBackground.evaluate((element) => element.getAttribute("style")),
      )
      .toContain("pc-media");
    const lightOverlayOpacity = await page
      .locator(".r-v2-bg__overlay")
      .evaluate((element) => {
        const matches = [
          ...getComputedStyle(element).backgroundImage.matchAll(
            /\/ ([\d.]+)\)/g,
          ),
        ];
        return Math.max(...matches.map((match) => Number(match[1])));
      });
    expect(lightOverlayOpacity).toBeLessThanOrEqual(0.86);

    const dlc = page.getByTestId("pc-component-dlc");
    await dlc.getByRole("button", { name: "dlc" }).click();
    await dlc.getByTestId("find-pc-metadata").click();
    await page.getByTestId("pc-candidate-phase11-phantom-liberty").click();
    await page.getByTestId("apply-pc-metadata").click();
    await page.getByRole("tab", { name: "Overview" }).click();
    await page
      .getByRole("heading", { name: "DLC", exact: true })
      .locator("..")
      .getByRole("button", { name: "Phantom Liberty", exact: true })
      .click();

    await expect(page).toHaveURL(
      new RegExp(`/rom/${romId}\\?tab=files&component=${dlcComponentId}`),
    );
    await expect(
      page.getByText(
        "dlc/setup_cyberpunk_2077_phantom_liberty_2.31a_(64bit)_(85116).exe",
        { exact: true },
      ),
    ).toBeVisible();
    expect(popups).toEqual([]);
    expect(await fixtureDigest()).toBe(before);
  });
});
