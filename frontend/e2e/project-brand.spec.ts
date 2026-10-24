import { expect, test } from "@playwright/test";
import { mountGallery } from "./fixtures/screenshot-management";

for (const theme of ["dark", "light"] as const) {
  test(
    "shared shell identity geometry and interactions " + theme,
    async ({ page }) => {
      await page.route(
        "https://api.github.com/repos/D1skanime/zockarchive/releases/latest",
        (route) =>
          route.fulfill({
            json: { tag_name: "fixture", published_at: "2020-01-01T00:00:00Z" },
          }),
      );
      await page.addInitScript(() => {
        const buttons = Array.from({ length: 17 }, () => ({
          pressed: false,
          touched: false,
          value: 0,
        }));
        const pad = {
          id: "Synthetic standard pad",
          index: 0,
          connected: true,
          mapping: "standard",
          buttons,
          axes: [0, 0, 0, 0],
          timestamp: 0,
        };
        Object.defineProperty(navigator, "getGamepads", { value: () => [pad] });
        Object.assign(window, { brandPad: pad });
      });
      const state = await mountGallery(page, { theme });
      const home = page.locator(".r-v2-nav__logo");
      await expect(home).toHaveAttribute("aria-label", "Home");
      await expect(home).toHaveAttribute("href", "/");
      await expect(home.locator(".project-brand")).toHaveAttribute(
        "aria-hidden",
        "true",
      );
      for (const width of [320, 599, 600, 959, 960, 1280, 1920, 3840]) {
        await page.setViewportSize({ width, height: 1000 });
        await expect(page.locator("html")).toHaveAttribute(
          "data-bp",
          width < 600 ? /\bxs\b/ : /./,
        );
        await expect(home.locator(".project-brand__short")).toBeVisible();
        if (width < 600)
          await expect(home.locator(".project-brand__word")).toBeHidden();
        else await expect(home.locator(".project-brand__word")).toBeVisible();
        const box = await home.boundingBox();
        expect(box!.height).toBeGreaterThanOrEqual(44);
        expect(box!.width).toBeGreaterThanOrEqual(44);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
        const center = page.locator(".r-v2-nav__center");
        if (width < 960) await expect(center).toBeHidden();
        else {
          const rect = await center.boundingBox();
          expect(Math.abs(rect!.x + rect!.width / 2 - width / 2)).toBeLessThan(
            1,
          );
          expect(box!.x + box!.width).toBeLessThanOrEqual(rect!.x);
        }
      }
      await page.setViewportSize({ width: 1280, height: 1000 });
      await page.screenshot({ path: test.info().outputPath("navigation.png") });
      // Observe activation without leaving the fixture while testing each input path.
      await home.evaluate((element) => {
        element.setAttribute("data-activations", "0");
        element.addEventListener(
          "click",
          (event) => {
            event.preventDefault();
            element.setAttribute(
              "data-activations",
              String(Number(element.getAttribute("data-activations")) + 1),
            );
          },
          { capture: true },
        );
      });
      await home.click();
      await expect(home).toHaveAttribute("data-activations", "1");
      await home.focus();
      await expect(home).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(home).toHaveAttribute("data-activations", "2");
      await home.tap();
      await expect(home).toHaveAttribute("data-activations", "3");
      await page.evaluate(() =>
        window.dispatchEvent(new Event("gamepadconnected")),
      );
      await expect(page.locator("html")).toHaveAttribute("data-input", "pad");
      await home.focus();
      await expect(home).toBeFocused();
      await page.evaluate(() => {
        const pad = Reflect.get(window, "brandPad");
        pad.buttons[0] = { pressed: true, touched: true, value: 1 };
      });
      await expect(home).toHaveAttribute("data-activations", "4");
      await page.evaluate(() => {
        Reflect.get(window, "brandPad").buttons[0] = {
          pressed: false,
          touched: false,
          value: 0,
        };
      });
      await page.locator("[data-user-menu-trigger]").click();
      await page.getByText("About", { exact: true }).click();
      const about = page.locator(".r-v2-about");
      await expect(about).toBeVisible();
      await expect(about.locator(".project-brand--about")).toHaveText("ZA");
      await expect(about.locator("a").first()).toHaveAttribute(
        "href",
        "https://github.com/D1skanime/zockarchive/releases/tag/fixture",
      );
      await expect(about).toContainText("RomM (upstream)");
      for (const width of [320, 600, 960, 1280, 3840]) {
        await page.setViewportSize({ width, height: 1000 });
        await expect(about).toBeVisible();
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
      }
      await page.setViewportSize({ width: 1280, height: 1000 });
      await page.screenshot({ path: test.info().outputPath("about.png") });
      await page.keyboard.press("Escape");
      await expect(about).toBeHidden();
      expect(state.mutations).toEqual([]);
      expect(state.errors).toEqual([]);
      expect(state.unexpected).toEqual([]);
    },
  );

  test("auth text preserves frame across widths " + theme, async ({ page }) => {
    await page.addInitScript((theme) => {
      localStorage.setItem("settings.theme", theme);
      localStorage.setItem("settings.locale", "en_US");
    }, theme);
    const mutations: string[] = [];
    await page.route("**/*", async (route) => {
      const request = route.request(),
        url = new URL(request.url());
      if (url.origin !== "http://127.0.0.1:4177") return route.abort();
      if (!url.pathname.startsWith("/api/")) return route.continue();
      if (request.method() !== "GET") {
        mutations.push(request.method() + " " + url.pathname);
        return route.abort();
      }
      const json =
        url.pathname === "/api/users/me"
          ? null
          : url.pathname === "/api/heartbeat"
            ? { SYSTEM: { VERSION: "fixture", SHOW_SETUP_WIZARD: false } }
            : {};
      return route.fulfill({ json });
    });
    for (const path of [
      "/login",
      "/register?token=fixture",
      "/reset-password",
    ]) {
      await page.goto(path);
      await expect(page.locator(".auth-card .project-brand--auth")).toHaveText(
        "ZockArchive",
      );
      for (const width of [320, 600, 960, 1280, 3840]) {
        await page.setViewportSize({ width, height: 1000 });
        await expect(page.locator(".auth-card")).toBeVisible();
        const frame = await page.locator(".auth-card").boundingBox();
        expect(frame!.width).toBeLessThanOrEqual(440);
        if (path === "/login" && width === 320)
          await page.screenshot({
            path: test.info().outputPath("auth-320.png"),
          });
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        ).toBe(true);
      }
    }
    expect(mutations).toEqual([]);
  });
}
