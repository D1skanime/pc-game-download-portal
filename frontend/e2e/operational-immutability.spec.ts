import { expect, test } from "@playwright/test";
import { gotoHydrated, seedUiState, STORAGE_STATE } from "./fixtures/auth";
import {
  expectHeading,
  firstFilesystemPlatform,
  firstPlayableRom,
  firstRom,
  listStorageRoots,
  loginToV2,
  runWorkflow,
  WORKFLOW_SLUGS,
} from "./fixtures/operational-proof";

test.describe.configure({ mode: "serial" });

test("browse-test covers login, hydration, and storage administration shells", async ({
  page,
}) => {
  await runWorkflow(
    page,
    WORKFLOW_SLUGS.browseTest,
    "/login -> /library-management",
    async () => {
      await loginToV2(page, "/library-management?tab=mapping");
      await expect(page.locator(".r-v2-user__name")).toBeVisible();
      await expect(
        page.getByRole("tab", { name: /folder mappings/i }),
      ).toBeVisible();

      const platform = await firstFilesystemPlatform(page);
      await gotoHydrated(page, `/platforms/${platform.id}/storage`);
      await expect(page.getByText("Storage administration")).toBeVisible();
      await expectHeading(page, /storage/i);
      await expect(
        page
          .getByRole("button", { name: "Map storage" })
          .or(page.getByRole("button", { name: "Change mapping" })),
      ).toBeVisible();
    },
  );
});

test.describe("operational immutability workflows", () => {
  test.use({ storageState: STORAGE_STATE.admin });

  test("mapping create, update, preview, and remove stay on the storage route", async ({
    page,
  }) => {
    await seedUiState(page, "dark");
    const platform = await firstFilesystemPlatform(page);
    const roots = await listStorageRoots(page);
    test.skip(roots.length === 0, "storage root fixture is required");

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.mappingCreate,
      `/platforms/${platform.id}/storage`,
      async () => {
        await gotoHydrated(page, `/platforms/${platform.id}/storage`);
        await expect(page.getByText("Storage administration")).toBeVisible();
        await expect(
          page
            .getByRole("button", { name: "Map storage" })
            .or(page.getByRole("button", { name: "Change mapping" })),
        ).toBeVisible();
      },
    );

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.preview,
      `/platforms/${platform.id}/storage`,
      async () => {
        await expect(page.getByText("Preview")).toBeVisible();
        await expect(
          page
            .getByRole("button", { name: "Refresh preview" })
            .or(page.getByText(/no preview has been started/i)),
        ).toBeVisible();
      },
    );

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.mappingUpdate,
      `/platforms/${platform.id}/storage`,
      async () => {
        await expect(page.getByText("Active mapping")).toBeVisible();
        await expect(
          page
            .getByRole("button", { name: "Change mapping" })
            .or(page.getByRole("button", { name: "Map storage" })),
        ).toBeVisible();
      },
    );

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.mappingRemove,
      `/platforms/${platform.id}/storage`,
      async () => {
        const removeButton = page.getByRole("button", {
          name: "Remove mapping",
        });
        const unchangedCopy = page.getByText(
          /original files remain unchanged/i,
        );
        await expect(removeButton.or(unchangedCopy)).toBeVisible();
      },
    );
  });

  test("scan and metadata workflows stay on the real v2 scan surface", async ({
    page,
  }) => {
    await seedUiState(page, "dark");

    await runWorkflow(page, WORKFLOW_SLUGS.scanHash, "/scan", async () => {
      await gotoHydrated(page, "/scan");
      await expect(
        page.getByRole("button", { name: /scan|start scan/i }),
      ).toBeVisible();
      await expect(
        page.getByText(/live progress|scan complete|scanning/i),
      ).toBeVisible();
    });

    await runWorkflow(page, WORKFLOW_SLUGS.metadataMatch, "/scan", async () => {
      await expect(page.getByText(/metadata/i).first()).toBeVisible();
      await expect(page.getByText(/providers/i).first()).toBeVisible();
      await expect(page.getByText(/hash matchers/i).first()).toBeVisible();
    });
  });

  test("stream, play, and download workflows stay on existing v2 ROM surfaces", async ({
    page,
  }) => {
    await seedUiState(page, "dark");
    const rom = await firstPlayableRom(page);

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.streamPlay,
      `/rom/${rom.id}`,
      async () => {
        await gotoHydrated(page, `/rom/${rom.id}`);
        await expectHeading(page, /.+/);
        await expect(
          page
            .getByRole("link", { name: /play/i })
            .or(page.getByRole("button", { name: /play/i }))
            .or(page.getByRole("link", { name: /stream/i }))
            .or(page.getByRole("button", { name: /stream/i })),
        ).toBeVisible();
      },
    );

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.singleDownload,
      `/rom/${rom.id}`,
      async () => {
        await page.getByRole("tab", { name: "Files" }).click();
        await expect(
          page.getByRole("button", { name: "Download", exact: true }).first(),
        ).toBeVisible();
      },
    );

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.multiDownload,
      `/rom/${rom.id}`,
      async () => {
        await expect(
          page
            .getByRole("button", { name: /download/i })
            .filter({ hasNot: page.getByText(/copy link/i) })
            .first(),
        ).toBeVisible();
      },
    );
  });

  test("catalog removal copy stays source-safe on the real ROM dialog", async ({
    page,
  }) => {
    await seedUiState(page, "dark");
    const rom = await firstRom(page);

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.gameCatalogRemoval,
      `/rom/${rom.id}`,
      async () => {
        await gotoHydrated(page, `/rom/${rom.id}`);
        await page
          .getByRole("button", { name: "More actions" })
          .first()
          .click();
        await page.getByRole("menuitem", { name: /delete/i }).click();
        await expect(
          page.getByText(/original files and folders remain unchanged/i),
        ).toBeVisible();
        await expect(
          page.getByRole("button", { name: /remove from catalog/i }),
        ).toBeVisible();
      },
    );
  });

  test("legacy migration, rollback, and platform mapping removal are named in the proof contract", async ({
    page,
  }) => {
    await seedUiState(page, "dark");
    const platform = await firstFilesystemPlatform(page);
    await gotoHydrated(page, `/platforms/${platform.id}/storage`);

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.legacyMigration,
      `/platforms/${platform.id}/storage`,
      async () => {
        await expect(page.getByText("Storage administration")).toBeVisible();
      },
    );

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.supportedRollback,
      `/platforms/${platform.id}/storage`,
      async () => {
        await expect(page.getByText("Active mapping")).toBeVisible();
      },
    );

    await runWorkflow(
      page,
      WORKFLOW_SLUGS.platformMappingRemoval,
      `/platforms/${platform.id}/storage`,
      async () => {
        await expect(
          page
            .getByRole("button", { name: "Remove mapping" })
            .or(page.getByText(/original files remain unchanged/i)),
        ).toBeVisible();
      },
    );
  });
});
