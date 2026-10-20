import {
  clearMetadataProviders,
  ensureSetup,
  expect,
  screenshot,
  test,
} from "./fixtures/phase34";

test("lost acceptance restores the same durable operation on reload without duplicate submission", async ({
  page,
}) => {
  await ensureSetup(page);
  const setup = await (await page.request.get("/api/setup/status")).json();
  const expectedPlatforms = new Set<string>(
    setup.saved_assignments.map(
      (assignment: { platform_slug: string }) => assignment.platform_slug,
    ),
  );
  expect(expectedPlatforms.size).toBeGreaterThan(0);
  await page.goto("/scan");
  await clearMetadataProviders(page);
  const start = page.locator(".r-v2-scan-card__start");
  await expect(start).toBeEnabled();
  let submissions = 0;
  let accepted: { id: string; job_id: string; request_key: string } | undefined;
  await page.route("**/api/scan-operations", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    submissions++;
    const payload = route.request().postDataJSON() as {
      type: string;
      apis: string[];
    };
    await test.info().attach("scan-provider-selection", {
      body: JSON.stringify({ type: payload.type, apis: payload.apis }),
      contentType: "application/json",
    });
    expect(
      payload.apis,
      "discovery-only scan must not use external metadata",
    ).toEqual([]);
    const response = await route.fetch();
    expect(response.ok()).toBe(true);
    accepted = await response.json();
    await route.abort("failed");
  });
  await start.click();
  await expect.poll(() => accepted?.id).toBeTruthy();
  await expect(page.getByTestId("operation-status")).toBeVisible();
  await expect.poll(() => submissions).toBe(1);
  await page.reload();
  await expect(page.getByTestId("operation-status")).toBeVisible();
  const result = await page.request.get("/api/scan-operations/" + accepted!.id);
  expect(result.ok()).toBe(true);
  const restored = await result.json();
  expect(restored.id).toBe(accepted!.id);
  expect(restored.job_id).toBe(accepted!.job_id);
  expect(submissions).toBe(1);
  await expect
    .poll(
      async () => {
        const response = await page.request.get(
          "/api/scan-operations/" + accepted!.id,
        );
        expect(response.ok()).toBe(true);
        return (await response.json()).state;
      },
      {
        timeout: 60000,
        message: "real RQ scan must reach confirmed completion",
      },
    )
    .toBe("completed");
  const platformResponse = await page.request.get("/api/platforms");
  expect(platformResponse.ok()).toBe(true);
  const platforms: { id: number; slug: string; rom_count: number }[] =
    await platformResponse.json();
  expect(new Set(platforms.map((platform) => platform.slug))).toEqual(
    expectedPlatforms,
  );
  expect(new Set(platforms.map((platform) => platform.id)).size).toBe(
    expectedPlatforms.size,
  );
  for (const platform of platforms)
    expect(
      platform.rom_count,
      "each generated platform must contain indexed games",
    ).toBeGreaterThan(0);
  const romResponse = await page.request.get("/api/roms?limit=100");
  expect(romResponse.ok()).toBe(true);
  const roms: { items: { platform_id: number }[] } = await romResponse.json();
  expect(new Set(roms.items.map((rom) => rom.platform_id))).toEqual(
    new Set(platforms.map((platform) => platform.id)),
  );
  expect(submissions).toBe(1);
  await screenshot(page, "scan-restored");
});

test("leaving scan never sends cancellation", async ({ page }) => {
  await ensureSetup(page);
  let cancels = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && /\/cancel$/.test(request.url()))
      cancels++;
  });
  await page.goto("/scan");
  await page.goto("/");
  await page.goto("/scan");
  expect(cancels).toBe(0);
});
