import { expect, type Page } from "@playwright/test";
import type { ScanOperationSnapshot } from "../../src/__generated__";

/** Shared presentation probe. Controlled projections are never worker evidence. */
export async function presentation(
  page: Page,
  warm: ScanOperationSnapshot,
  accept: (snapshot: ScanOperationSnapshot) => Promise<ScanOperationSnapshot>,
  capture: (name: string) => Promise<void>,
  checks: Record<string, boolean>,
  variants: string[],
) {
  const panel = page.getByTestId("operation-status");
  // Controlled browser-only projection uses the shipped monotonic status owner.
  // These states are UI fixtures, not claims of observed provider requests.
  const states = [
    ["unchanged", "no_request", "not_scheduled"],
    ["changed", "cached", "cooldown"],
    ["refresh_required", "requested", "due"],
    ["incomplete", "failed", "configuration_blocked"],
    ["unchanged", "no_match", "budget_deferred"],
    ["unchanged", "matched", "not_scheduled"],
  ] as const;
  const projected: ScanOperationSnapshot = {
    ...warm,
    version: warm.version + 10000,
    items: states.map(([inventory, provider, retry], index) => ({
      ...warm.items![0],
      id: 90000 + index,
      target_key: "projection-" + index,
      relative_path: "Controlled.<script>.未知." + index,
      provider: "steam",
      outcome: provider === "failed" ? "failed" : "completed",
      inventory: {
        rom_id: 90000 + index,
        inventory_state: inventory,
        existing_game: true,
        identified_windows: provider === "matched",
        retry_state: retry,
        is_identifying: provider === "requested",
        next_eligible_at: "2030-01-01T12:00:00Z",
      },
      provider_execution: {
        state: provider,
        invoked: provider !== "no_request",
        requests: ["requested", "failed", "no_match", "matched"].includes(
          provider,
        )
          ? 1
          : 0,
        cached: provider === "cached",
        is_identifying: provider === "requested",
      },
    })),
    items_offset: 0,
    items_total: Math.max(warm.items_total ?? 0, states.length) + 1,
  };
  await accept(projected);
  await expect(panel).toContainText("Cached metadata used");
  await expect(panel).toContainText("Requesting metadata");
  await expect(panel).toContainText("Retry deferred");
  await expect(panel).toContainText("inventory check could not finish");
  expect(await panel.locator("script").count()).toBe(0);
  checks.state_projection = true;
  const stale = { ...warm, version: 1, scan_stats: { total_roms: 99999 } };
  const retained = await accept(stale);
  expect(retained.version).toBe(projected.version);
  checks.stale_monotonic = true;
  const warnings = panel.locator("fieldset");
  await expect(warnings.locator("input[type=checkbox]")).toHaveCount(1);
  await warnings.locator("label.r-checkbox").click();
  await expect(warnings.locator("input[type=checkbox]")).toBeChecked();
  await expect(
    warnings.getByRole("button", { name: "Retry selected metadata" }),
  ).toBeEnabled();
  checks.fault_only = true;
  await expect(panel).toHaveAttribute("aria-live", "polite");
  await expect(panel).toHaveAttribute("aria-atomic", "false");
  checks.polite = true;
  const lastPage = panel.getByRole("button", {
    name: "Load more",
    exact: true,
  });
  await expect.soft(lastPage).toBeVisible();
  if (await lastPage.count()) {
    await lastPage.focus();
    await expect.soft(lastPage).toBeFocused();
    const consumed = retained.items?.length ?? states.length;
    await accept({
      ...projected,
      version: projected.version + 1,
      items: [],
      items_offset: consumed,
      items_total: consumed,
    });
    await expect.soft(lastPage).toHaveCount(0);
    await expect.soft(panel.getByRole("status")).toBeFocused();
  }
  checks.focus_restoration = true;
  const allRows = page.locator(".r-v2-scan-platform__rom");
  const heights = await allRows.evaluateAll((rows) =>
    rows.map((row) => row.getBoundingClientRect().height),
  );
  expect.soft(heights.length).toBeGreaterThan(0);
  expect.soft(heights.every((height) => Math.abs(height - 65) < 1)).toBe(true);
  checks.geometry = true;
  await page.addScriptTag({ path: "node_modules/axe-core/axe.min.js" });
  for (const theme of ["dark", "light"]) {
    await page.evaluate(async (theme) => {
      const path = "/src/composables/useUISettings.ts";
      const module = await import(path);
      module.useUISettings().theme.value = theme;
    }, theme);
    await expect
      .soft(page.locator("#application"))
      .toHaveClass(new RegExp("v-theme--" + theme));
    for (const width of [320, 600, 960, 1280, 1920, 3840]) {
      await page.setViewportSize({ width, height: 1000 });
      await expect.soft(panel).toBeVisible();
      await expect
        .configure({ soft: true })
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
      await capture(width + "-" + theme);
    }
    const contrast = await page.evaluate(async () => {
      const engine = Reflect.get(window, "axe");
      return engine.run(
        document.querySelector("[data-testid=operation-status]"),
        {
          runOnly: {
            type: "rule",
            values: ["color-contrast", "button-name", "aria-valid-attr-value"],
          },
        },
      );
    });
    expect.soft(contrast.violations, theme).toEqual([]);
  }
  checks.overflow = true;
  await page.setViewportSize({ width: 320, height: 1000 });
  const targets = await panel.locator("button").evaluateAll((buttons) =>
    buttons
      .filter((button) => {
        const r = button.getBoundingClientRect();
        return r.width && r.height;
      })
      .map((button) => {
        const r = button.getBoundingClientRect();
        return { width: r.width, height: r.height };
      }),
  );
  expect.soft(targets.length).toBeGreaterThan(0);
  expect.soft(targets.every((r) => r.width >= 44 && r.height >= 44)).toBe(true);
  checks.targets = true;
  for (const locale of ["de_DE", "zh_CN"]) {
    await page.evaluate(async (locale) => {
      const path = "/src/locales/index.ts";
      const module = await import(path);
      module.default.global.locale.value = locale;
    }, locale);
    await expect.soft(panel).not.toContainText("scan.");
    await expect
      .configure({ soft: true })
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      )
      .toBe(true);
    await capture(locale);
    variants.push(locale);
  }
  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  await expect
    .configure({ soft: true })
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await capture("zoom200");
  variants.push("zoom200");
  await page.evaluate(() => {
    document.documentElement.style.zoom = "";
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await capture("reduced-motion");
  variants.push("reduced-motion");
  // Exercise the actual RAF bridge using a synthetic connected pad.
  // The native hardware inventory is read first and recorded separately.
  const physical = await page.evaluate(
    () => Array.from(navigator.getGamepads()).filter(Boolean).length,
  );
  await page.evaluate(() => {
    let pressed = false;
    const buttons = Array.from({ length: 17 }, (_, index) => ({
      value: index === 9 ? 1 : 0,
      pressed: index === 9,
      touched: false,
    }));
    Object.defineProperty(navigator, "getGamepads", {
      configurable: true,
      value: () => [
        {
          id: "synthetic-phase35-bridge",
          index: 0,
          connected: true,
          mapping: "standard",
          axes: [0, 0],
          buttons: pressed
            ? buttons
            : buttons.map((button) => ({
                ...button,
                pressed: false,
                value: 0,
              })),
          timestamp: performance.now(),
        },
      ],
    });
    requestAnimationFrame(() => {
      pressed = true;
    });
  });
  await expect.soft(page.locator("html")).toHaveAttribute("data-input", "pad");
  await expect
    .soft(page.locator("[data-user-menu-trigger]"))
    .toHaveAttribute("aria-expanded", "true");
  checks.gamepad_bridge = true;
  await page.keyboard.press("Escape");
  await expect
    .soft(page.locator("[data-user-menu-trigger]"))
    .toHaveAttribute("aria-expanded", "false");
  await page.evaluate(() => {
    Reflect.deleteProperty(navigator, "getGamepads");
  });
  await page.addScriptTag({ path: "node_modules/axe-core/axe.min.js" });
  const axe = await page.evaluate(async () => {
    const engine = Reflect.get(window, "axe");
    return engine.run(
      document.querySelector("[data-testid=operation-status]"),
      {
        runOnly: {
          type: "rule",
          values: ["color-contrast", "button-name", "aria-valid-attr-value"],
        },
      },
    );
  });
  expect.soft(axe.violations).toEqual([]);
  checks.contrast = true;
  return { states, stale, retained, physical, targets, heights };
}
