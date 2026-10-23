import { expect, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

/** Theme/viewport controls never substitute for worker or durable-storage evidence. */
export async function presentation(page: Page) {
  const checks: Record<string, boolean> = {};
  const captures: { case: string; file: string; sha256: string }[] = [];
  const trigger = page.getByTestId("overview-description-edit");
  const editor = page.getByTestId("localized-description-editor");
  const settledEditor = async () => {
    await expect(editor).toBeVisible();
    await expect
      .poll(() =>
        editor.evaluate(async (node) => {
          const panel = node.closest(".r-dialog__panel");
          const root = panel?.closest(".r-dialog");
          if (!panel || !root) return false;
          if (
            root
              .getAnimations({ subtree: true })
              .some((animation) => animation.playState !== "finished")
          )
            return false;
          const transform = new DOMMatrixReadOnly(
            getComputedStyle(panel).transform,
          );
          if (!transform.isIdentity || getComputedStyle(root).opacity !== "1")
            return false;
          const before = panel.getBoundingClientRect();
          await new Promise<void>((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
          );
          const after = panel.getBoundingClientRect();
          return ["x", "y", "width", "height"].every(
            (key) =>
              before[key as keyof DOMRect] === after[key as keyof DOMRect],
          );
        }),
      )
      .toBe(true);
  };
  const capture = async (name: string) => {
    const file = "description-" + name + ".png";
    await page.screenshot({
      path: "/phase34/evidence/" + file,
      fullPage: true,
      animations: "disabled",
    });
    writeFileSync(
      "/phase34/evidence/description-" + name + ".html",
      await page.content(),
    );
    captures.push({
      case: name,
      file,
      sha256: createHash("sha256")
        .update(readFileSync("/phase34/evidence/" + file))
        .digest("hex"),
    });
  };
  await page.addScriptTag({ path: "node_modules/axe-core/axe.min.js" });
  const overflow = async () =>
    expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      )
      .toBe(true);
  const contrast = async () => {
    const result = await page.evaluate(async () => {
      const engine = Reflect.get(window, "axe");
      return engine.run(
        document.querySelector("[data-testid=localized-description-editor]"),
        {
          runOnly: {
            type: "rule",
            values: ["color-contrast", "button-name", "aria-valid-attr-value"],
          },
        },
      );
    });
    expect(result.violations).toEqual([]);
  };
  for (const theme of ["dark", "light"]) {
    await page.evaluate(async (value) => {
      const path = "/src/composables/useUISettings.ts";
      const module = await import(path);
      module.useUISettings().theme.value = value;
    }, theme);
    await expect(page.locator("#application")).toHaveClass(
      new RegExp("v-theme--" + theme),
    );
    for (const width of [320, 600, 960, 1280, 1920, 3840]) {
      await page.setViewportSize({ width, height: 1000 });
      await expect(page.locator(".overview-tab__summary")).toBeVisible();
      await overflow();
      await capture(width + "-" + theme);
      await trigger.click();
      await settledEditor();
      await overflow();
      const targets = await editor.locator("button").evaluateAll((nodes) =>
        nodes.map((node) => {
          const rect = node.getBoundingClientRect();
          return { width: rect.width, height: rect.height };
        }),
      );
      expect(targets.length).toBeGreaterThan(0);
      expect(
        targets.every((rect) => rect.width >= 44 && rect.height >= 44),
      ).toBe(true);
      await capture("editor-" + width + "-" + theme);
      await page.keyboard.press("Escape");
      await expect(editor).toHaveCount(0);
      await expect(trigger).toBeFocused();
    }
    await trigger.click();
    await settledEditor();
    await contrast();
    await page.keyboard.press("Escape");
  }
  checks.targets =
    checks.contrast =
    checks.overflow =
    checks.mouse =
    checks.trigger_focus =
      true;
  for (const value of ["de_DE", "zh_CN"]) {
    await page.evaluate(async (value) => {
      const path = "/src/locales/index.ts";
      const module = await import(path);
      module.default.global.locale.value = value;
    }, value);
    await overflow();
    await capture(value);
  }
  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  await overflow();
  await capture("zoom200");
  await page.evaluate(() => {
    document.documentElement.style.zoom = "";
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await capture("reduced-motion");
  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(editor).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  checks.keyboard = true;
  await trigger.tap();
  await expect(editor).toBeVisible();
  await page.keyboard.press("Escape");
  checks.touch = true;
  const physical = await page.evaluate(
    () => Array.from(navigator.getGamepads()).filter(Boolean).length,
  );
  await page.evaluate(() => {
    let pressed = false;
    Object.defineProperty(navigator, "getGamepads", {
      configurable: true,
      value: () => [
        {
          id: "synthetic-phase36-bridge",
          index: 0,
          connected: true,
          mapping: "standard",
          axes: [0, 0],
          timestamp: performance.now(),
          buttons: Array.from({ length: 17 }, (_, index) => ({
            pressed: pressed && index === 9,
            touched: false,
            value: pressed && index === 9 ? 1 : 0,
          })),
        },
      ],
    });
    requestAnimationFrame(() => {
      pressed = true;
    });
  });
  await expect(page.locator("html")).toHaveAttribute("data-input", "pad");
  await expect(page.locator("[data-user-menu-trigger]")).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  await page.keyboard.press("Escape");
  await page.evaluate(() => {
    Reflect.deleteProperty(navigator, "getGamepads");
  });
  checks.gamepad_bridge = true;
  return {
    captures,
    checks,
    physicalDetected: physical,
    physicalController: "unverified",
  };
}
