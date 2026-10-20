import { expect, test } from "@playwright/test";
import { existsSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { clearMetadataProviders } from "./e2e/fixtures/phase34";

test("fresh direct Games mapping, persistent readiness, inputs, and mapped scan", async ({ page }) => {
  const fixture = (action: string, ...args: (number | string)[]) => {
    const output = execFileSync("/app/.venv/bin/python", ["tools/phase33_collection_fixture.py", action, ...args.map(String)], { cwd: "/app/backend", env: process.env, encoding: "utf8" });
    const line = output.trim().split("\n").at(-1)!;
    return JSON.parse(line.replace(/^PGDP33_FIXTURE_JSON:/, ""));
  };
  const addFixture = async (stage: string) => {
    writeFileSync("/phase34/evidence/add-" + stage + "-child.request", "request host synthetic fixture addition");
    await expect.poll(() => existsSync("/phase34/evidence/add-" + stage + "-child.ready"), { timeout: 30000 }).toBe(true);
  };
  const checks: Record<string, boolean> = {};
  const screenshots: string[] = [];
  const receipts: { method: string; path: string; status: number; body: unknown }[] = [];
  const pending: Promise<void>[] = [];
  page.on("response", response => {
    const path = new URL(response.url()).pathname;
    if (!path.startsWith("/api/setup/")) return;
    pending.push((async () => {
      const body = await response.json().catch(() => null);
      receipts.push({ method: response.request().method(), path, status: response.status(), body });
    })());
  });
  const screenshot = async (name: string) => {
    await page.screenshot({ path: "/phase34/evidence/" + name, fullPage: true });
    screenshots.push(name);
  };
  await page.goto("/setup");
  const discovery = await page.request.get("/api/setup/folders");
  expect(discovery.ok()).toBe(true);
  const folders = await discovery.json();
  expect(folders.folders.map((folder: { name: string }) => folder.name).sort()).toEqual(["My Games", "pc"]);
  expect(folders.folders.find((folder: { name: string }) => folder.name === "pc").association).toBe("known");
  expect(folders.folders.find((folder: { name: string }) => folder.name === "My Games").association).toBe("unknown");
  const table = page.locator(".r-setup-platforms");
  await expect(table).toBeVisible();
  await expect(table.getByText("My Games", { exact: true })).toBeVisible();
  await expect(table.getByText("pc", { exact: true })).toBeVisible();
  checks.discovery = true;
  await expect(page.locator("body")).not.toContainText(/Storage Administration|\/app\/|\/home\/|RomM|roms\//i);

  for (const mode of ["dark", "light"]) {
    await page.evaluate(mode => localStorage.setItem("settings.theme", mode), mode);
    await page.reload();
    await expect(table).toBeVisible();
    await expect.soft(page.locator(".r-v2-" + mode).first()).toBeVisible();
    await screenshot("setup-" + mode + ".png");
    checks["theme_" + mode] = await page.locator(".r-v2-" + mode).first().isVisible();
  }
  for (const width of [320, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(table).toBeVisible();
    const noOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    expect.soft(noOverflow).toBe(true);
    await screenshot("setup-" + width + ".png");
    checks[width === 320 ? "layout_320" : "layout_desktop"] = noOverflow;
  }
  const row = table.locator("tbody tr").filter({ has: page.locator("th", { hasText: "My Games" }) });
  const field = row.locator(".r-select__field");
  await field.click();
  const platform = folders.platform_options.find((option: { slug: string }) => option.slug === "snes");
  expect(platform).toBeTruthy();
  await page.getByRole("option", { name: platform.display_name, exact: true }).click();
  checks.inline_assignment = true;
  checks.mouse = true;
  await page.keyboard.press("Tab");
  const keyboardReachable = await page.evaluate(() => document.activeElement?.tagName !== "BODY");
  expect.soft(keyboardReachable).toBe(true);
  await screenshot("setup-keyboard.png");
  checks.keyboard = keyboardReachable;
  const next = page.getByRole("button", { name: "Next", exact: true });
  const bounds = await next.boundingBox();
  expect(bounds).toBeTruthy();
  const navigationBounds = await page.locator(".r-v2-setup__footer button").evaluateAll(buttons => buttons.map(button => {
    const rect = button.getBoundingClientRect();
    return { label: button.textContent?.trim(), width: rect.width, height: rect.height };
  }));
  expect.soft(navigationBounds.length).toBeGreaterThanOrEqual(1);
  for (const target of navigationBounds) {
    expect.soft(target.height, target.label).toBeGreaterThanOrEqual(44);
    expect.soft(target.width, target.label).toBeGreaterThanOrEqual(44);
  }
  checks.touch_target = navigationBounds.length >= 1 && navigationBounds.every(target => target.height >= 44 && target.width >= 44);
  await page.touchscreen.tap(bounds!.x + bounds!.width / 2, bounds!.y + bounds!.height / 2);
  checks.touch = true;
  const previousStepBounds = await page.locator(".r-v2-setup__footer button").evaluateAll(buttons => buttons.map(button => {
    const rect = button.getBoundingClientRect();
    return { label: button.textContent?.trim(), width: rect.width, height: rect.height };
  }));
  expect.soft(previousStepBounds.length).toBeGreaterThanOrEqual(2);
  for (const target of previousStepBounds) {
    expect.soft(target.height, target.label).toBeGreaterThanOrEqual(44);
    expect.soft(target.width, target.label).toBeGreaterThanOrEqual(44);
  }
  navigationBounds.push(...previousStepBounds);
  checks.touch_target = checks.touch_target && previousStepBounds.length >= 2 && previousStepBounds.every(target => target.height >= 44 && target.width >= 44);
  await page.getByLabel("Username", { exact: true }).fill("phase33-admin");
  await page.getByLabel("Password", { exact: true }).fill(process.env.PHASE34_TEST_PASSWORD!);
  await page.getByLabel("Repeat password", { exact: true }).fill(process.env.PHASE34_TEST_PASSWORD!);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const assigned = page.waitForResponse(response => response.url().endsWith("/api/setup/folders/assign") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Finish", exact: true }).click();
  const assignment = await assigned;
  expect(assignment.ok()).toBe(true);
  const saved = await assignment.json();
  expect(saved.ready).toBe(true);
  expect(saved.mappings.map((mapping: { folder_name: string }) => mapping.folder_name).sort()).toEqual(["My Games", "pc"]);
  expect(saved.mappings.every((mapping: { mapping_id: number }) => mapping.mapping_id > 0)).toBe(true);
  checks.ready = true;
  await expect(page.getByRole("link", { name: "Start first scan", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("link", { name: "Start first scan", exact: true })).toBeVisible();
  checks.reload = true;
  await Promise.all(pending);
  const boundary = receipts.length;
  await page.goto("/scan");
  await clearMetadataProviders(page);
  const start = page.locator(".r-v2-scan-card__start");
  await expect(start).toBeEnabled();
  await Promise.all(pending);
  expect(receipts.slice(boundary).filter(receipt => receipt.method !== "GET")).toEqual([]);
  checks.get_only = true;
  const accepted = page.waitForResponse(response => response.url().endsWith("/api/scan-operations") && response.request().method() === "POST");
  await start.click();
  const operation = await (await accepted).json();
  expect(operation.id).toBeTruthy();
  await expect.poll(async () => {
    const response = await page.request.get("/api/scan-operations/" + operation.id);
    expect(response.ok()).toBe(true);
    return (await response.json()).state;
  }, { timeout: 60000 }).toBe("completed");
  checks.scan_completed = true;
  const initialSnapshot = await (await page.request.get("/api/scan-operations/" + operation.id)).json();
  const romsResponse = await page.request.get("/api/roms?limit=100");
  expect(romsResponse.ok()).toBe(true);
  const roms = await romsResponse.json();
  expect(roms.items.length).toBeGreaterThanOrEqual(2);
  expect(new Set(roms.items.map((rom: { platform_id: number }) => rom.platform_id)).size).toBe(2);
  checks.mapped_reads = true;
  const parent = roms.items.find((rom: { fs_name: string }) => rom.fs_name === "Castlevania");
  expect(parent).toBeTruthy();
  expect(roms.items.some((rom: { fs_name: string }) => rom.fs_name === "Belmonts.Curse")).toBe(false);
  const platformsResponse = await page.request.get("/api/platforms");
  const platforms = await platformsResponse.json();
  const windows = platforms.find((platform: { slug: string }) => platform.slug === "win");
  expect(windows).toBeTruthy();
  const mappingResponse = await page.request.get("/api/storage/mappings/platforms/" + windows.id);
  expect(mappingResponse.ok()).toBe(true);
  const mapping = await mappingResponse.json();
  const seed = fixture("seed-parent", parent.id);
  expect(seed.seeded).toBe(true);
  const parentRow = page.locator(".r-v2-scan-platform__rom").filter({ hasText: "Castlevania" });
  await expect(parentRow).toHaveCount(1);
  await parentRow.getByRole("button", { name: "Scan", exact: true }).click();
  const selectedEntry = page.locator(".pc-subfolder-scan__entry").filter({ hasText: "Belmonts.Curse" });
  await expect(selectedEntry).toBeVisible();
  const promotedRequest = page.waitForRequest(request => request.method() === "POST" && request.url().endsWith("/api/scan-operations"));
  const promotedResponse = page.waitForResponse(response => response.request().method() === "POST" && response.url().endsWith("/api/scan-operations"));
  await selectedEntry.getByRole("button", { name: "Scan", exact: true }).click();
  const payload = (await promotedRequest).postDataJSON();
  expect(payload.collection_promotion).toEqual({
    parent_rom_id: parent.id, mapping_id: mapping.id, expected_revision: mapping.version,
    parent_relative_path: "Castlevania", selected_child_relative_path: "Castlevania/Belmonts.Curse",
  });
  expect(payload.filesystem_scope_paths[windows.fs_slug]).toBe("Castlevania/Belmonts.Curse");
  const scopedResponse = await promotedResponse;
  expect(scopedResponse.status()).toBe(202);
  const scoped = await scopedResponse.json();
  await expect.poll(async () => {
    const response = await page.request.get("/api/scan-operations/" + scoped.id);
    return (await response.json()).state;
  }, { timeout: 60000 }).toBe("completed");
  const afterResponse = await page.request.get("/api/roms?limit=100");
  const afterRoms = await afterResponse.json();
  const child = afterRoms.items.filter((rom: { fs_name: string }) => rom.fs_name === "Belmonts.Curse");
  expect(child).toHaveLength(1);
  expect(child[0].fs_path).toBe("pc/Castlevania");
  const childDetailResponse = await page.request.get("/api/roms/" + child[0].id);
  expect(childDetailResponse.ok()).toBe(true);
  const childDetail = await childDetailResponse.json();
  expect(childDetail.files.map((file: { file_name: string }) => file.file_name).sort()).toEqual(["game.part01.rar", "game.part02.rar"]);
  expect(afterRoms.items.some((rom: { fs_name: string }) => rom.fs_name === "Lords.of.Shadow2")).toBe(false);
  expect(afterRoms.items.some((rom: { id: number }) => rom.id === parent.id)).toBe(false);
  const selectedSnapshot = await (await page.request.get("/api/scan-operations/" + scoped.id)).json();
  checks.explicit_child_scope = true;
  checks.parent_retired = true;
  const promoted = fixture("inspect-parent", parent.id);
  expect(promoted.classified).toBe(true);
  expect(promoted.parent_absent).toBe(true);
  expect(promoted.user_state_retained).toBe(true);
  expect(promoted.user_state_not_attached_to_child).toBe(true);
  fixture("run-cleanup");
  await expect.poll(() => fixture("inspect-parent", parent.id).owned_media_removed, { timeout: 30000 }).toBe(true);
  const cleaned = fixture("inspect-parent", parent.id);
  expect(cleaned.shared_media_preserved).toBe(true);
  expect(cleaned.source_media_preserved).toBe(true);
  checks.safe_owned_cleanup = true;

  await addFixture("normal");
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === "romm_csrftoken");
  expect(csrf?.value).toBeTruthy();
  const normalResponse = await page.request.post("/api/scan-operations", {
    headers: { "x-csrftoken": csrf!.value },
    data: { request_key: randomUUID(), platforms: [windows.id], apis: [], type: "complete" },
  });
  expect(normalResponse.status()).toBe(202);
  const normal = await normalResponse.json();
  await expect.poll(async () => {
    const response = await page.request.get("/api/scan-operations/" + normal.id);
    return (await response.json()).state;
  }, { timeout: 60000 }).toBe("completed");
  const normalRoms = await (await page.request.get("/api/roms?limit=100")).json();
  for (const name of ["Belmonts.Curse", "Lords.of.Shadow2", "Newly.Added.Game"]) {
    const found = normalRoms.items.filter((rom: { fs_name: string }) => rom.fs_name === name);
    expect(found).toHaveLength(1);
    expect(found[0].fs_path).toBe("pc/Castlevania");
    expect(found[0].missing_from_fs).toBe(false);
  }
  expect(normalRoms.items.some((rom: { fs_name: string }) => rom.fs_name === "Castlevania")).toBe(false);
  checks.known_child_preserved = true;
  checks.normal_discovers_children = true;
  const normalSnapshot = await (await page.request.get("/api/scan-operations/" + normal.id)).json();

  await addFixture("scheduled");
  const scheduled = fixture("run-scheduled", windows.id);
  expect(scheduled.completed).toBe(true);
  const finalRoms = await (await page.request.get("/api/roms?limit=100")).json();
  expect(finalRoms.items.some((rom: { fs_name: string }) => rom.fs_name === "Scheduled.New.Game")).toBe(true);
  expect(finalRoms.items.some((rom: { fs_name: string }) => rom.fs_name === "Castlevania")).toBe(false);
  checks.scheduled_discovers_children = true;
  const counts = {
    initial: initialSnapshot.scan_stats,
    selected: selectedSnapshot.scan_stats,
    full: normalSnapshot.scan_stats,
    scheduled: scheduled.scan_stats,
  };
  const windowsCount = normalRoms.items.filter((rom: { platform_id: number }) => rom.platform_id === windows.id).length;
  const expectedTotals = { initial: roms.items.length, selected: 1, full: windowsCount, scheduled: finalRoms.items.length };
  for (const stage of ["initial", "selected", "full", "scheduled"] as const) {
    expect.soft(counts[stage].total_roms, stage).toBe(expectedTotals[stage]);
    expect.soft(counts[stage].scanned_roms, stage).toBeLessThanOrEqual(expectedTotals[stage]);
    expect.soft(counts[stage].scanned_roms, stage).toBeGreaterThan(0);
  }
  checks.progress_counts = (["initial", "selected", "full", "scheduled"] as const).every(stage => counts[stage].total_roms === expectedTotals[stage] && counts[stage].scanned_roms > 0 && counts[stage].scanned_roms <= expectedTotals[stage]);

  await screenshot("mapped-scan-completed.png");
  await Promise.all(pending);
  const gamepads = await page.evaluate(() => Array.from(navigator.getGamepads()).filter(Boolean).length);
  expect(gamepads).toBe(0);
  writeFileSync("/phase34/evidence/browser.json", JSON.stringify({
    status: Object.values(checks).every(Boolean) ? "PASS" : "FAIL", checks, screenshots, navigationBounds, discovery: folders, assignment: saved,
    receipts, post_setup_receipts: receipts.slice(boundary), operation_id: operation.id, scoped_operation_id: scoped.id, child: { id: child[0].id, fs_name: child[0].fs_name, fs_path: child[0].fs_path, files: childDetail.files.map((file: { file_name: string }) => file.file_name) }, rom_count: finalRoms.items.length, promotion: promoted, cleanup: cleaned, scheduled, counts, expectedTotals,
    gamepad: { status: "BLOCKED", attempted: "navigator.getGamepads()", connected: gamepads, reason: "No physical gamepad is connected to the disposable headless Chromium runner." },
  }, null, 2));
});
