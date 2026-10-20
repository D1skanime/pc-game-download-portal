import { expect, test as base, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

export const test = base;
export { expect };
export function identity() {
  const password = process.env.PHASE34_TEST_PASSWORD;
  const username = process.env.PHASE34_TEST_USERNAME || "phase34_admin";
  const target = new URL(
    process.env.PHASE34_BASE_URL || "http://127.0.0.1:3344",
  );
  const token = process.env.PHASE34_RUN_TOKEN;
  let ownedProduction = false;
  if (token && /^[a-f0-9]{32}$/.test(token) && process.env.PHASE34_MANIFEST) {
    const manifest = JSON.parse(
      readFileSync(process.env.PHASE34_MANIFEST, "utf8"),
    );
    ownedProduction =
      target.hostname === "phase34-production-app" &&
      manifest.token === token &&
      manifest.project === "pgdp34-" + token &&
      password === token &&
      manifest.network?.internal === true;
  }
  if (
    !password ||
    (!["127.0.0.1", "localhost"].includes(target.hostname) && !ownedProduction)
  )
    throw new Error(
      "PHASE34_BROWSER_TARGET: verified disposable target and generated password required",
    );
  return { username, password };
}
export async function login(page: Page) {
  const account = identity();
  await page.goto("/login");
  const form = page.locator("form.r-v2-login-form");
  await form.locator('input[name="username"]').fill(account.username);
  await form.locator('input[name="password"]').fill(account.password);
  await form.locator('button[type="submit"]').click();
  await expect(page).not.toHaveURL(/\/login/);
}
export async function ensureSetup(page: Page) {
  const account = identity();
  const heartbeat = await page.request.get("/api/heartbeat");
  expect(heartbeat.ok(), "isolated API heartbeat").toBe(true);
  const body = await heartbeat.json();
  if (!body.SYSTEM.SHOW_SETUP_WIZARD) {
    await login(page);
    return;
  }
  await page.goto("/setup");
  await expect(page.locator(".r-setup-platforms")).toBeVisible();
  const folders = await page.request.get("/api/setup/folders");
  expect(folders.ok()).toBe(true);
  const discovery = await folders.json();
  expect(
    discovery.folders.length,
    "synthetic Games folders required",
  ).toBeGreaterThan(0);
  for (const folder of discovery.folders) {
    if (folder.suggested_platform) continue;
    const row = page
      .locator(".r-setup-platforms tbody tr")
      .filter({ has: page.locator("th", { hasText: folder.name }) });
    await row.locator(".r-select__field").click();
    const fixtureSlugs: Record<string, string> = {
      PC: "win",
      "GB GameBoy": "gb",
      "GBA GameBoy Advance": "gba",
      "SNES Super Nintendo": "snes",
    };
    const platform = discovery.platform_options.find(
      (option: { slug: string }) => option.slug === fixtureSlugs[folder.name],
    );
    expect(
      platform,
      "supported synthetic platform " + folder.name,
    ).toBeTruthy();
    await page
      .getByRole("option", { name: platform.display_name, exact: true })
      .click();
  }
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByLabel("Username", { exact: true }).fill(account.username);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page
    .getByLabel("Repeat password", { exact: true })
    .fill(account.password);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Start first scan", exact: true }),
  ).toBeVisible();
}
export async function scanSnapshot(page: Page) {
  const response = await page.request.get("/api/scan-operations/active");
  expect(response.ok(), "authenticated operation lookup").toBe(true);
  return response.json();
}
export async function screenshot(page: Page, name: string) {
  // Password controls are absent from all retained successful screenshots.
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await page.screenshot({
    path:
      (process.env.PHASE34_EVIDENCE_DIR || "/phase34/evidence") +
      "/" +
      name +
      ".png",
    fullPage: true,
  });
}

export async function clearMetadataProviders(page: Page) {
  const groups = page.locator(".r-v2-scan-card__providers-group");
  await expect(groups).toHaveCount(2);
  await expect(groups.first()).toBeVisible();
  for (let index = 0; index < (await groups.count()); index++) {
    const group = groups.nth(index);
    const clear = group.getByRole("button", { name: "Clear", exact: true });
    if (await clear.isVisible()) await clear.click();
    else {
      await group.locator(".r-select__field").click();
      const all = page.locator(".r-select__item--all[aria-selected='true']");
      if (await all.count()) await all.click();
      await page.keyboard.press("Escape");
    }
    await expect(group.getByText("All", { exact: true })).toHaveCount(0);
  }
  const matchers = page.locator(
    ".r-v2-scan-card__matchers input[type='checkbox']",
  );
  for (let index = 0; index < (await matchers.count()); index++)
    if (
      (await matchers.nth(index).isChecked()) &&
      (await matchers.nth(index).isEnabled())
    )
      await matchers.nth(index).uncheck();
}
