import { expect, type Page } from "@playwright/test";
import {
  ensureSetup,
  identity,
  login,
  screenshot,
  test,
} from "./fixtures/phase34";

async function csrf(page: Page) {
  const cookies = await page.context().cookies();
  return {
    "x-csrftoken": cookies.find((cookie) => cookie.name === "romm_csrftoken")!
      .value,
  };
}

for (const theme of ["dark", "light"]) {
  test("actual branded shell and auth " + theme, async ({ page }) => {
    await page.addInitScript((theme) => {
      localStorage.setItem("settings.theme", theme);
      localStorage.setItem("settings.locale", "en_US");
    }, theme);
    await ensureSetup(page);
    await page.goto("/");
    const home = page.locator(".r-v2-nav__logo");
    await expect(home).toHaveAttribute("aria-label", "Home");
    for (const width of [320, 599, 600, 959, 960, 1280, 1920, 3840]) {
      await page.setViewportSize({ width, height: 1000 });
      await expect(home.locator(".project-brand__short")).toHaveText("ZA");
      if (width < 600)
        await expect(home.locator(".project-brand__word")).toBeHidden();
      else await expect(home.locator(".project-brand__word")).toBeVisible();
      const bounds = await home.boundingBox();
      expect(bounds!.width).toBeGreaterThanOrEqual(44);
      expect(bounds!.height).toBeGreaterThanOrEqual(44);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    await page.setViewportSize({ width: 1280, height: 1000 });
    await home.focus();
    await expect(home).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/$/);
    await home.tap();
    await page.locator("[data-user-menu-trigger]").click();
    await page.getByText("About", { exact: true }).click();
    const about = page.locator(".r-v2-about");
    await expect(about).toContainText("ZockArchive");
    await expect(about.locator(".project-brand--about")).toHaveText("ZA");
    await expect(
      about.locator('a[href*="D1skanime/zockarchive/releases"]'),
    ).toBeVisible();
    await screenshot(page, "actual-about-" + theme);
    await page.keyboard.press("Escape");
    await expect(about).toBeHidden();
    const logout = await page.request.post("/api/logout", {
      headers: await csrf(page),
    });
    expect(logout.ok()).toBe(true);
    await page.goto("/login");
    await expect(page.locator(".auth-card .project-brand")).toHaveText(
      "ZockArchive",
    );
    await expect(page).toHaveTitle("Login");
    await login(page);
    await expect(page.locator(".r-v2-user__name")).toHaveText(
      identity().username,
    );
  });
}

test("real invitation registration and rejected credentials", async ({
  page,
}) => {
  await ensureSetup(page);
  const invite = await page.request.post("/api/users/invite-link?role=user", {
    headers: await csrf(page),
  });
  expect(invite.ok()).toBe(true);
  const token = (await invite.json()).token;
  await page.request.post("/api/logout", { headers: await csrf(page) });
  await page.goto("/register?token=" + encodeURIComponent(token));
  await expect(page.locator(".auth-card .project-brand")).toHaveText(
    "ZockArchive",
  );
  await page.getByLabel("Username", { exact: true }).fill("phase38-registered");
  await page.getByLabel("Email", { exact: true }).fill("phase38@example.test");
  await page.getByLabel("Password", { exact: true }).fill(identity().password);
  await page.locator("form.r-v2-register__form button[type=submit]").click();
  await expect(page).toHaveURL(/\/login/);
  const form = page.locator("form.r-v2-login-form");
  await form.locator('input[name="username"]').fill("phase38-registered");
  await form.locator('input[name="password"]').fill("incorrect-password");
  await form.locator('button[type="submit"]').click();
  await expect(page.locator(".r-v2-user__name")).toHaveCount(0);
  await expect(page).toHaveURL(/\/login/);
  await form.locator('input[name="password"]').fill(identity().password);
  await form.locator('button[type="submit"]').click();
  await expect(page.locator(".r-v2-user__name")).toHaveText(
    "phase38-registered",
  );
});

test("actual mapped library content requires authentication", async ({
  page,
  browser,
}) => {
  await ensureSetup(page);
  const response = await page.request.get("/api/roms?limit=100");
  expect(response.ok()).toBe(true);
  const roms = (await response.json()).items;
  expect(roms.length).toBeGreaterThan(0);
  const pc = roms.find(
    (rom: { platform_slug: string }) => rom.platform_slug === "win",
  );
  expect(pc).toBeTruthy();
  const detail = await (await page.request.get("/api/roms/" + pc.id)).json();
  const file = detail.files.find(
    (file: { file_name: string }) => file.file_name === "Phase34-Synthetic.bin",
  );
  expect(file).toBeTruthy();
  const path =
    "/api/roms/" +
    file.id +
    "/files/content/" +
    encodeURIComponent(file.file_name);
  const download = await page.request.get(path);
  expect(download.status()).toBe(200);
  expect((await download.body()).toString()).toBe(
    "phase34 synthetic fixture\n",
  );
  const anonymous = await browser.newContext();
  const denied = await anonymous.request.get("http://127.0.0.1:3345" + path);
  expect([401, 403]).toContain(denied.status());
  await anonymous.close();
  await page.goto("/rom/" + pc.id);
  await expect(page).toHaveTitle(new RegExp(pc.name || pc.fs_name));
  await screenshot(page, "actual-library-detail");
});

test("actual German auth and about identity", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("settings.locale", "de_DE");
    localStorage.setItem("settings.theme", "light");
  });
  await ensureSetup(page);
  await page.request.post("/api/logout", { headers: await csrf(page) });
  await page.goto("/login");
  await expect(page.locator(".auth-card .project-brand")).toHaveText(
    "ZockArchive",
  );
  await expect(
    page.locator("form.r-v2-login-form button[type=submit]"),
  ).toHaveText("Einloggen");
  await login(page);
  await page.setViewportSize({ width: 600, height: 1000 });
  await page.locator("[data-user-menu-trigger]").click();
  await page.getByText("\u00dcber", { exact: true }).click();
  await expect(page.locator(".r-v2-about")).toContainText(
    "ZockArchive-Version",
  );
  await screenshot(page, "actual-german-about");
});
