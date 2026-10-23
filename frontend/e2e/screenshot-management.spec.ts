import { expect, test, type Page, type Locator } from "@playwright/test";
import { writeFileSync } from "node:fs";
import {
  mountGallery,
  card,
  pick,
  shots,
  upload,
  evidence,
} from "./fixtures/screenshot-management";

test.afterEach(async ({ page }) => {
  const state = states.get(page);
  if (state)
    expect(
      state.unexpected,
      "Unknown traffic is rejected before host access",
    ).toEqual([]);
});
const states = new WeakMap<object, Awaited<ReturnType<typeof mountGallery>>>();
async function open(
  page: Parameters<typeof mountGallery>[0],
  options: Parameters<typeof mountGallery>[1] = {},
) {
  const state = await mountGallery(page, options);
  states.set(page, state);
  return state;
}
const posts = (state: Awaited<ReturnType<typeof mountGallery>>) =>
  state.mutations.filter((m) => m.path === "/api/screenshots");

test("top picker and actual drop upload N files once with canonical refresh", async ({
  page,
}) => {
  const state = await open(page);
  let choosers = 0;
  page.on("filechooser", () => choosers++);
  await expect(shots(page).locator('input[type="file"]')).toHaveCount(1);
  await pick(page, ["one.png", "two.png"]);
  await expect.poll(() => posts(state).length).toBe(2);
  await expect.poll(() => state.reads).toBe(2);
  await expect(card(page, "user:103")).toHaveCount(1);
  expect(choosers).toBe(1);
  await shots(page)
    .locator(".za-shots__dropzone")
    .dispatchEvent("drop", {
      dataTransfer: await page.evaluateHandle(() => {
        const data = new DataTransfer();
        data.items.add(new File(["a"], "drop-a.png", { type: "image/png" }));
        data.items.add(new File(["b"], "drop-b.png", { type: "image/png" }));
        return data;
      }),
    });
  await expect.poll(() => posts(state).length).toBe(4);
  await expect.poll(() => state.reads).toBe(3);
  expect(choosers).toBe(1);
  expect(
    await page
      .locator("html")
      .evaluate(() => performance.getEntriesByType("navigation").length),
  ).toBe(1);
});

test("provider placements preserve both surfaces, position zero, order and captured version", async ({
  page,
}) => {
  const state = await open(page);
  const first = card(page, "provider:7"),
    third = card(page, "provider:9");
  await expect(first.locator(".za-shot__badge")).toHaveCount(2);
  await expect(first.locator(".za-shot__badge").first()).toContainText("1");
  for (const [add, remove] of [
    ["Add to overview", "Remove from overview"],
    ["Add as background", "Remove as background"],
  ]) {
    await third.getByRole("button", { name: add, exact: true }).click();
    await expect(
      third.getByRole("button", { name: remove, exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(state.mutations.at(-1)?.body?.expected_version).toBe(
      "2026-10-23T10:00:00Z",
    );
    await third.getByRole("button", { name: remove, exact: true }).click();
    await expect(
      third.getByRole("button", { name: add, exact: true }),
    ).toBeEnabled();
    expect(
      state.rom.owned_media
        .slice(0, 2)
        .map((m) =>
          m.placements.map(({ surface, position }) => ({ surface, position })),
        ),
    ).toEqual([
      [
        { surface: "overview", position: 0 },
        { surface: "background", position: 0 },
      ],
      [
        { surface: "overview", position: 1 },
        { surface: "background", position: 1 },
      ],
    ]);
  }
  expect(
    state.mutations.every((m) => m.path.includes("/media/placements")),
  ).toBe(true);
  await expect(first.locator("script")).toHaveCount(0);
  await expect(first.locator(".za-shot__source")).toContainText(
    "<script>escaped</script>",
  );
});

test("own visibility and permanent deletion preserve colliding community/provider identity", async ({
  page,
}) => {
  const state = await open(page);
  const mine = card(page, "user:10");
  await mine.getByRole("button", { name: "Make private", exact: true }).click();
  await expect(
    mine.getByRole("button", { name: "Make public", exact: true }),
  ).toBeEnabled();
  await mine.getByRole("button", { name: "Make public", exact: true }).click();
  await expect(
    mine.getByRole("button", { name: "Make private", exact: true }),
  ).toBeEnabled();
  await mine.getByRole("button", { name: "Delete", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText(/permanent/i);
  await dialog.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(mine).toHaveCount(0);
  await expect(card(page, "provider:7")).toHaveCount(1);
  await expect(card(page, "user:7")).toHaveCount(1);
  await expect(card(page, "user:7").locator(".za-shot__actions")).toHaveCount(
    0,
  );
  expect(
    state.mutations.some(
      (m) => m.path === "/api/screenshots/10" && m.method === "DELETE",
    ),
  ).toBe(true);
});

test("provider managed-copy confirmation is truthful and source-specific", async ({
  page,
}) => {
  const state = await open(page);
  await card(page, "provider:7")
    .getByRole("button", { name: "Remove provider screenshot" })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("managed screenshot copy");
  await expect(dialog).toContainText("may restore");
  await page.screenshot({
    path: evidence + "/confirmation-dark.png",
    animations: "disabled",
  });
  await dialog
    .getByRole("button", { name: "Remove screenshot", exact: true })
    .click();
  await expect(card(page, "provider:7")).toHaveCount(0);
  await expect(card(page, "user:7")).toHaveCount(1);
  expect(state.mutations.at(-1)?.path).toBe("/api/roms/1/media/7");
});

test("viewer personal exception and protected community, manual/audio panels and stable owner", async ({
  page,
}) => {
  const state = await open(page, { viewer: true });
  await expect(
    card(page, "provider:7").locator(".za-shot__actions"),
  ).toHaveCount(0);
  await expect(card(page, "user:7").locator(".za-shot__actions")).toHaveCount(
    0,
  );
  await expect(
    card(page, "user:10").getByRole("button", { name: "Delete", exact: true }),
  ).toHaveCount(1);
  await pick(page, ["viewer.png"]);
  await expect.poll(() => posts(state).length).toBe(1);
  await expect(upload(page)).toBeEnabled();
  const owner = await shots(page).elementHandle();
  for (const name of ["Manual", "Artwork", "Soundtrack", "Screenshots"]) {
    await page
      .locator(".r-v2-media__subtab-btn")
      .filter({ hasText: name })
      .click();
    await expect(page).toHaveURL(/fixture=preserved/);
    if (name !== "Screenshots") await expect(shots(page)).toBeHidden();
    expect(await owner!.evaluate((el) => el.isConnected)).toBe(true);
  }
  await expect(shots(page)).toBeVisible();
  await page
    .locator(".r-tab-nav")
    .getByRole("tab", { name: "Overview", exact: true })
    .click();
  await expect(shots(page)).toHaveCount(0);
  await expect(page).toHaveURL(/tab=overview/);
  await page
    .locator(".r-tab-nav")
    .getByRole("tab", { name: "Media", exact: true })
    .click();
  await expect(shots(page)).toBeVisible();
  await expect(page).toHaveURL(/subtab=screenshots/);
});

test("409 refreshes canonical version before the next placement", async ({
  page,
}) => {
  const state = await open(page);
  state.conflict = true;
  const action = card(page, "provider:9").getByRole("button", {
    name: "Add to overview",
    exact: true,
  });
  await action.click();
  await expect.poll(() => state.reads).toBe(2);
  await expect(action).toBeEnabled();
  await action.click();
  await expect.poll(() => state.mutations.length).toBe(2);
  expect(state.mutations[1].body?.expected_version).toBe(
    "2026-10-23T11:00:00Z",
  );
});

test("partial failures retain upload progress and one settled canonical refresh", async ({
  page,
}) => {
  const state = await open(page);
  state.uploadFailure = true;
  let release!: () => void;
  state.uploadBarrier = new Promise((resolve) => (release = resolve));
  await pick(page, ["good.png", "fail.png"]);
  await expect(upload(page)).toBeDisabled();
  await expect.poll(() => posts(state).length).toBe(2);
  await shots(page)
    .locator(".za-shots__dropzone")
    .dispatchEvent("drop", {
      dataTransfer: await page.evaluateHandle(() => {
        const data = new DataTransfer();
        data.items.add(new File(["a"], "duplicate.png", { type: "image/png" }));
        return data;
      }),
    });
  expect(posts(state)).toHaveLength(2);
  release();
  await expect.poll(() => state.reads).toBe(2);
  await expect(upload(page)).toBeEnabled();
  await expect(page.getByText(/1 screenshot uploaded; 1 failed/)).toBeVisible();
  await expect(page.getByText("Fixture upload failed").first()).toBeVisible();
  await expect(
    page.getByText("fail.png", { exact: true }).first(),
  ).toBeVisible();
});

test("all failure avoids refresh and canonical failure never reports success", async ({
  page,
}) => {
  const state = await open(page);
  state.uploadFailure = true;
  await pick(page, ["fail.png"]);
  await expect(upload(page)).toBeEnabled();
  await expect(page.getByText("Fixture upload failed").first()).toBeVisible();
  expect(state.reads).toBe(1);
  state.refreshFailure = true;
  await pick(page, ["success.png"]);
  await expect(
    page
      .getByText(/uploaded.*could not|could not.*refresh|could not.*update/i)
      .first(),
  ).toBeVisible();
  expect(state.reads).toBe(2);
});

test("lightbox uses exact clicked source/index and restores focus, keyboard and touch", async ({
  page,
}) => {
  await open(page);
  const trigger = card(page, "provider:8").locator("[data-preview]");
  await trigger.focus();
  await page.keyboard.press("Enter");
  const overlay = page.locator(".r-carousel--fullscreen");
  await expect(overlay).toBeVisible();
  await expect(
    overlay.locator(".r-carousel__item img").filter({ visible: true }).first(),
  ).toHaveAttribute("src", "/api/roms/1/media/8/content");
  await page.keyboard.press("ArrowRight");
  await expect(
    overlay.locator(".r-carousel__item img").filter({ visible: true }).first(),
  ).toHaveAttribute("src", "/api/roms/1/media/9/content");
  await page.keyboard.press("ArrowLeft");
  await expect(
    overlay.locator(".r-carousel__item img").filter({ visible: true }).first(),
  ).toHaveAttribute("src", "/api/roms/1/media/8/content");
  await page.keyboard.press("Escape");
  await expect(overlay).toHaveCount(0);
  await expect(trigger).toBeFocused();
  const mine = card(page, "user:11").locator("[data-preview]");
  await mine.tap();
  await expect(overlay).toBeVisible();
  await expect(
    overlay.locator(".r-carousel__item img").filter({ visible: true }).first(),
  ).toHaveAttribute("src", "/fixture/mine11.svg");
  await page.keyboard.press("Escape");
  await expect(mine).toBeFocused();
});

for (const theme of ["dark", "light"] as const)
  for (const width of [320, 600, 960, 1280, 1920, 3840]) {
    test(`actual scroll geometry ${theme} ${width}`, async ({ page }) => {
      await page.setViewportSize({ width, height: 1000 });
      const state = await open(page, { count: 1001, theme, locale: "de_DE" });
      await expect(shots(page).locator("[data-shot-key]")).toHaveCount(1004);
      const rows: unknown[] = [];
      for (const fraction of [0, 0.5, 1]) {
        await shots(page).evaluate((el, fraction) => {
          const owner =
            getComputedStyle(el).overflowY === "visible"
              ? document.scrollingElement!
              : el;
          owner.scrollTop =
            fraction * (owner.scrollHeight - owner.clientHeight);
        }, fraction);
        await expect
          .poll(async () =>
            shots(page).evaluate((el) => {
              const rect = el
                .querySelector(".za-shots__toolbar")!
                .getBoundingClientRect();
              return rect.top >= -1 && rect.bottom <= innerHeight;
            }),
          )
          .toBe(true);
        const geometry = await shots(page).evaluate((el) => {
          const owner =
            getComputedStyle(el).overflowY === "visible"
              ? document.scrollingElement!
              : el;
          const bar = el
            .querySelector(".za-shots__toolbar")!
            .getBoundingClientRect();
          const btn = el
            .querySelector(".za-shots__toolbar button")!
            .getBoundingClientRect();
          const nav = document
            .querySelector(".r-v2-nav-bar")
            ?.getBoundingClientRect();
          return {
            owner: owner === el ? "inner" : "document",
            scrollTop: owner.scrollTop,
            max: owner.scrollHeight - owner.clientHeight,
            bar: { top: bar.top, bottom: bar.bottom },
            button: { width: btn.width, height: btn.height },
            navBottom: nav?.bottom ?? 0,
            overflow: document.documentElement.scrollWidth - innerWidth,
          };
        });
        expect(geometry.max).toBeGreaterThan(1000);
        if (fraction) expect(geometry.scrollTop).toBeGreaterThan(1000);
        expect(geometry.overflow).toBeLessThanOrEqual(1);
        expect(geometry.bar.top).toBeGreaterThanOrEqual(geometry.navBottom - 1);
        const chooser = page.waitForEvent("filechooser");
        await upload(page).click();
        await (await chooser).setFiles([]);
        rows.push({ fraction, ...geometry });
        if (fraction === 0)
          await page.screenshot({
            path: `${evidence}/gallery-${theme}-${width}.png`,
            animations: "disabled",
          });
        if (fraction === 0.5 && [320, 1280].includes(width))
          await page.screenshot({
            path: `${evidence}/gallery-mid-${theme}-${width}.png`,
            animations: "disabled",
          });
      }
      writeFileSync(
        `${evidence}/geometry-${theme}-${width}.json`,
        JSON.stringify(rows, null, 2),
      );
      expect(posts(state)).toHaveLength(0);
    });
  }

for (const width of [320, 1280])
  test(`upload prepend preserves real visible anchor at ${width}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const state = await open(page, { count: 80, ownCount: 40 });
    const anchor = card(page, "user:10");
    await anchor.evaluate((el) => {
      const root = el.closest(".za-shots")!;
      const owner =
        getComputedStyle(root).overflowY === "visible"
          ? document.scrollingElement!
          : root;
      owner.scrollTop +=
        el.getBoundingClientRect().top -
        root.querySelector(".za-shots__toolbar")!.getBoundingClientRect()
          .bottom -
        8;
    });
    await anchor.evaluate((el) => {
      const root = el.closest(".za-shots")!;
      const owner =
        getComputedStyle(root).overflowY === "visible"
          ? document.scrollingElement!
          : root;
      owner.scrollTop +=
        el.getBoundingClientRect().top -
        root.querySelector(".za-shots__toolbar")!.getBoundingClientRect()
          .bottom -
        8;
    });
    const before = (await anchor.boundingBox())!.y;
    const scrollBefore = await shots(page).evaluate(
      (el) =>
        (getComputedStyle(el).overflowY === "visible"
          ? document.scrollingElement!
          : el
        ).scrollTop,
    );
    await pick(page, ["prepend-a.png", "prepend-b.png", "prepend-c.png"]);
    await expect.poll(() => state.reads).toBe(2);
    await expect(upload(page)).toBeEnabled();
    await expect
      .poll(async () => Math.abs((await anchor.boundingBox())!.y - before))
      .toBeLessThanOrEqual(3);
    const after = (await anchor.boundingBox())!.y;
    expect(scrollBefore).toBeGreaterThan(1000);
    expect(posts(state)).toHaveLength(3);
    expect(
      await page.evaluate(
        () => performance.getEntriesByType("navigation").length,
      ),
    ).toBe(1);
    writeFileSync(
      `${evidence}/anchor-${width}.json`,
      JSON.stringify({ before, after, scrollBefore, tolerance: 3 }),
    );
  });

test("keyboard picker and real touch preserve existing input", async ({
  page,
}) => {
  await page.setViewportSize({ width: 600, height: 1000 });
  await open(page);
  await upload(page).focus();
  const chooser = page.waitForEvent("filechooser");
  await page.keyboard.press("Enter");
  await (await chooser).setFiles([]);
  const trigger = card(page, "provider:7").locator("[data-preview]");
  await trigger.tap();
  await expect(page.locator(".r-carousel--fullscreen")).toBeVisible();
  const touchTargets = await card(page, "provider:7")
    .locator(".za-shot__actions button")
    .evaluateAll((nodes) =>
      nodes.map((node) => {
        const rect = node.getBoundingClientRect();
        return { width: rect.width, height: rect.height };
      }),
    );
  expect(
    touchTargets.every((rect) => rect.width >= 44 && rect.height >= 44),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  writeFileSync(
    `${evidence}/touch-input.json`,
    JSON.stringify({ touchTargets, keyboardPicker: true, touchPreview: true }),
  );
});

async function padBridge(page: Page) {
  const physicalDetected = await page.evaluate(
    () => Array.from(navigator.getGamepads()).filter(Boolean).length,
  );
  await page.evaluate(() => {
    Reflect.set(window, "shotPadButton", -1);
    Object.defineProperty(navigator, "getGamepads", {
      configurable: true,
      value: () => [
        {
          id: "synthetic-shot-dpad",
          index: 0,
          connected: true,
          mapping: "standard",
          axes: [0, 0],
          timestamp: performance.now(),
          buttons: Array.from({ length: 17 }, (_, i) => ({
            pressed: Reflect.get(window, "shotPadButton") === i,
            value: Reflect.get(window, "shotPadButton") === i ? 1 : 0,
            touched: false,
          })),
        },
      ],
    });
  });
  const press = async (button: number) =>
    page.evaluate(async (button) => {
      Reflect.set(window, "shotPadButton", button);
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      );
      Reflect.set(window, "shotPadButton", -1);
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      );
    }, button);
  return { press, physicalDetected };
}

for (const width of [320, 1280])
  test(`controller D-pad reaches every screenshot control at ${width}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const state = await open(page, { count: 2 });
    const preview = (key: string) => card(page, key).locator("[data-preview]");
    const actions = (key: string) =>
      card(page, key).locator(".za-shot__actions button");
    const refresh = shots(page).locator(".za-shots__head button");
    const { press, physicalDetected } = await padBridge(page);
    const visited: { button: number; active: string }[] = [];
    // Follow actual visual positions because a sticky toolbar changes row order during scrolling.
    const moveTo = async (target: Locator) => {
      await expect(target).toBeEnabled();
      for (let i = 0; i < 30; i++) {
        if (await target.evaluate((el) => el === document.activeElement))
          return;
        await expect
          .poll(() =>
            shots(page).evaluate((el) => el.contains(document.activeElement)),
          )
          .toBe(true);
        const desired = (await target.boundingBox())!;
        const active = await page.evaluate(() => {
          const node = document.activeElement!;
          const r = node.getBoundingClientRect();
          return { top: r.top, left: r.left };
        });
        const button =
          Math.abs(desired.y - active.top) > 3
            ? desired.y > active.top
              ? 13
              : 12
            : desired.x > active.left
              ? 15
              : 14;
        await press(button);
        visited.push({
          button,
          active: await page.evaluate(() => {
            const node = document.activeElement!;
            return (
              (node.closest("[data-shot-key]")?.getAttribute("data-shot-key") ??
                "toolbar") +
              ":" +
              node.getAttribute("aria-label")
            );
          }),
        });
      }
      writeFileSync(
        `${evidence}/dpad-diagnostic-${width}.json`,
        JSON.stringify(visited, null, 2),
      );
      await expect(target).toBeFocused();
    };
    // The sole direct focus establishes entry; every subsequent gallery target uses D-pad events.
    await upload(page).focus();
    const required = [
      refresh,
      preview("provider:7"),
      ...[0, 1, 2].map((i) => actions("provider:7").nth(i)),
      preview("provider:8"),
      ...[0, 1, 2].map((i) => actions("provider:8").nth(i)),
      preview("user:10"),
      ...[0, 1].map((i) => actions("user:10").nth(i)),
      preview("user:11"),
      ...[0, 1].map((i) => actions("user:11").nth(i)),
      preview("user:7"),
    ];
    const reached: string[] = [];
    for (const target of required) {
      await moveTo(target);
      reached.push((await target.getAttribute("aria-label")) ?? "");
    }
    await expect(actions("user:7")).toHaveCount(0);
    await moveTo(upload(page));
    const chooser = page.waitForEvent("filechooser");
    await press(0);
    await (await chooser).setFiles([]);
    await moveTo(refresh);
    const beforeRefresh = state.reads;
    await press(0);
    await expect.poll(() => state.reads).toBe(beforeRefresh + 1);
    await expect(refresh).toBeEnabled();
    await moveTo(preview("provider:7"));
    await press(0);
    await expect(page.locator(".r-carousel--fullscreen")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(preview("provider:7")).toBeFocused();
    for (const [index, surface] of [
      [0, "overview"],
      [1, "background"],
    ] as const) {
      for (let iteration = 0; iteration < 2; iteration++) {
        await moveTo(actions("provider:7").nth(index));
        const before = state.mutations.length;
        await press(0);
        await expect.poll(() => state.mutations.length).toBe(before + 1);
        await expect(actions("provider:7").nth(index)).toBeEnabled();
        const mutation = state.mutations.at(-1)!;
        expect(mutation.path).toContain("/media/placements");
        expect(
          mutation.method === "POST"
            ? mutation.body?.surface
            : new URLSearchParams(mutation.query).get("surface"),
        ).toBe(surface);
      }
    }
    await moveTo(actions("user:10").nth(0));
    await press(0);
    await expect(
      card(page, "user:10").getByRole("button", {
        name: "Make public",
        exact: true,
      }),
    ).toBeEnabled();
    expect(state.mutations.at(-1)?.path).toBe("/api/screenshots/10");
    await moveTo(upload(page));
    await expect(page.locator("html")).toHaveAttribute("data-input", "pad");
    // The shared dialog focuses its header Close; activate that real focus with A.
    const dangerSource = width === 320 ? "provider:7" : "user:10";
    await moveTo(actions(dangerSource).nth(width === 320 ? 2 : 1));
    const beforeDanger = state.mutations.length;
    await press(0);
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(
      dialog.getByRole("button", { name: "Close", exact: true }),
    ).toBeFocused();
    const dialogFocus = await dialog.evaluate((el) => ({
      inside: el.contains(document.activeElement),
      label: document.activeElement?.getAttribute("aria-label"),
      text: document.activeElement?.textContent?.trim(),
    }));
    expect(dialogFocus.inside).toBe(true);
    await press(0);
    await expect(dialog).toHaveCount(0);
    expect(state.mutations).toHaveLength(beforeDanger);
    writeFileSync(
      `${evidence}/dpad-${width}.json`,
      JSON.stringify(
        {
          width,
          physicalDetected,
          directGalleryFocusCalls: 1,
          reached,
          visited,
          chooserByA: true,
          placementByA: true,
          visibilityByA: true,
          dangerSource,
          dangerOpenedByA: true,
          dialogFocus,
          headerCloseCancelledByA: true,
          communityReadonly: true,
          returnedToUploadBeforeDialog: true,
          physicalController: "unavailable",
        },
        null,
        2,
      ),
    );
  });

test("empty and broken-image states remain operable", async ({ page }) => {
  await open(page, { count: 0 });
  await expect(shots(page).getByText("No screenshots yet")).toBeVisible();
  await pick(page, ["empty.png"]);
  await expect(upload(page)).toBeEnabled();
  await expect(shots(page).locator(".za-shot--new")).toHaveCount(1);
  await page.route("**/fixture/mine10.svg?broken=1", (route) => route.abort());
  await card(page, "user:10")
    .locator("img")
    .evaluate((img) => {
      img.removeAttribute("src");
      img.setAttribute("src", "/fixture/mine10.svg?broken=1");
    });
  await expect(
    card(page, "user:10").getByText("Screenshot preview unavailable."),
  ).toBeVisible();
});

test("provider loading and post-navigation upload settlement stay bounded", async ({
  page,
}) => {
  const state = await open(page, { count: 0 });
  let release!: () => void;
  state.mediaBarrier = new Promise((resolve) => (release = resolve));
  const refresh = shots(page).locator(".za-shots__head button");
  await refresh.click();
  try {
    await expect(shots(page).locator(".r-skeleton")).toHaveCount(3);
    await expect(refresh).toBeDisabled();
  } finally {
    release();
  }
  await expect(refresh).toBeEnabled();
  await expect(shots(page).locator(".r-skeleton")).toHaveCount(0);
  state.uploadBarrier = new Promise((resolve) => (release = resolve));
  await pick(page, ["late.png"]);
  await expect.poll(() => posts(state).length).toBe(1);
  const reads = state.reads;
  await page
    .locator(".r-tab-nav")
    .getByRole("tab", { name: "Overview", exact: true })
    .click();
  await expect(shots(page)).toHaveCount(0);
  release();
  await expect.poll(() => state.rom.all_user_screenshots.length).toBe(4);
  expect(state.reads).toBe(reads);
  await expect(page).toHaveURL(/tab=overview/);
});

test("unknown API and external requests fail closed", async ({ page }) => {
  const state = await open(page);
  await page.evaluate(async () => {
    await Promise.allSettled([
      fetch("/api/never-allowed"),
      fetch("https://unexpected.invalid/gallery"),
    ]);
  });
  expect(state.unexpected).toEqual(
    expect.arrayContaining([
      "GET /api/never-allowed",
      "https://unexpected.invalid/gallery",
    ]),
  );
  expect(state.unexpected).toHaveLength(2);
  state.unexpected.length = 0;
  expect(state.blocked.some((url) => url.includes("socket.io"))).toBe(true);
});
