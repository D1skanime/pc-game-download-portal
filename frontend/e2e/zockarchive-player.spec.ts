import { expect } from "@playwright/test";
import { login, screenshot, test } from "./fixtures/phase34";

test("actual local EmulatorJS initializes the owned synthetic cartridge", async ({
  page,
}) => {
  await login(page);
  const rows = await (await page.request.get("/api/roms?limit=100")).json();
  const rom = rows.items.find(
    (row: { name: string }) => row.name === "Owned synthetic cartridge",
  );
  expect(rom).toBeTruthy();
  const loader = await page.request.get("/assets/emulatorjs/data/loader.js");
  expect(loader.status()).toBe(200);
  expect(loader.headers()["content-type"]).toMatch(/javascript/);
  const external: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).hostname !== "phase34-production-app")
      external.push(request.url());
  });
  await page.goto("/rom/" + rom.id + "/ejs");
  await expect(page.locator(".r-v2-ejs__title")).toHaveText(
    "Owned synthetic cartridge",
  );
  await page.locator(".r-v2-ejs__play").click();
  await expect
    .poll(() => page.evaluate(() => !!window.EJS_emulator), { timeout: 60000 })
    .toBe(true);
  await expect(page.locator(".ejs_canvas")).toBeVisible({ timeout: 90000 });
  expect(await page.evaluate(() => window.EJS_pathtodata)).toBe(
    "/assets/emulatorjs/data",
  );
  expect(
    external.filter((url) => /emulatorjs|libretro|\.wasm/.test(url)),
  ).toEqual([]);
  await screenshot(page, "actual-local-emulatorjs");
});
