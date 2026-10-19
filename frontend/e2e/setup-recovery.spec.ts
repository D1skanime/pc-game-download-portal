import {
  ensureSetup,
  expect,
  identity,
  login,
  screenshot,
  test,
} from "./fixtures/phase34";

test("saved setup completes without submitting a scan and survives another login", async ({
  page,
}) => {
  identity();
  let submissions = 0;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      /\/api\/scan-operations$/.test(request.url())
    )
      submissions++;
  });
  await ensureSetup(page);
  await page.goto("/setup");
  await expect(
    page.getByRole("link", { name: "Start first scan", exact: true }),
  ).toBeVisible();
  const before = await page.request.get("/api/setup/status");
  expect(before.ok()).toBe(true);
  const saved = await before.json();
  expect(saved.setup_complete).toBe(true);
  expect(saved.saved_assignments.length).toBeGreaterThan(0);
  expect(submissions).toBe(0);
  await screenshot(page, "setup-complete");
  await page.context().clearCookies();
  await page.goto("/setup");
  await expect(page).toHaveURL(/\/login/);
  await login(page);
  await page.goto("/setup");
  await expect(
    page.getByRole("link", { name: "Start first scan", exact: true }),
  ).toBeVisible();
  const restored = await (await page.request.get("/api/setup/status")).json();
  expect(restored.saved_assignments).toEqual(saved.saved_assignments);
  expect(submissions).toBe(0);
});
