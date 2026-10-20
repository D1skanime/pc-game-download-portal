import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import type { ScanOperationSnapshot } from "../src/__generated__";
import { clearMetadataProviders, login } from "./fixtures/phase34";
import { presentation } from "./fixtures/phase35-presentation";

test("isolated durable incremental scan and controlled UI projections", async ({
  page,
}) => {
  const checks: Record<string, boolean> = {};
  const screenshots: { case: string; file: string; sha256: string }[] = [];
  const variants: string[] = [];
  const commands: { method: string; path: string }[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (path.startsWith("/api/scan-operations"))
      commands.push({ method: request.method(), path });
  });
  const fixture = (action: string, stage: string) => {
    execFileSync(
      "/app/.venv/bin/python",
      action === "seed"
        ? ["tools/phase35_browser_fixture.py"]
        : ["tools/phase35_incremental_client.py", action, "--stage", stage],
      {
        cwd: "/app/backend",
        env: process.env,
        encoding: "utf8",
        timeout: 300000,
      },
    );
    if (action === "seed") return null;
    return JSON.parse(
      readFileSync("/phase34/evidence/" + stage + ".json", "utf8"),
    );
  };
  const capture = async (name: string) => {
    const file = name + ".png";
    await page.screenshot({
      path: "/phase34/evidence/" + file,
      fullPage: true,
    });
    screenshots.push({
      case: name,
      file,
      sha256: createHash("sha256")
        .update(readFileSync("/phase34/evidence/" + file))
        .digest("hex"),
    });
    writeFileSync("/phase34/evidence/" + name + ".html", await page.content());
  };
  const accept = async (snapshot: ScanOperationSnapshot) =>
    page.evaluate(async (snapshot) => {
      const path = "/src/v2/composables/useScanOperationStatus/index.ts";
      const module = await import(path);
      const status = module.useScanOperationStatus();
      const result = status.accept(snapshot);
      status.dispose();
      return result;
    }, snapshot);
  const assertCounters = async (snapshot: ScanOperationSnapshot) => {
    const fields = [
      "inventory_checked",
      "inventory_unchanged",
      "inventory_changed",
      "inventory_refresh_required",
      "inventory_incomplete",
      "unresolved_games",
      "metadata_retry_games",
      "provider_requests",
    ];
    const expected = fields.flatMap((field) =>
      snapshot.scan_stats?.[field] === undefined
        ? []
        : [snapshot.scan_stats[field]],
    );
    await expect
      .poll(() =>
        page
          .getByTestId("operation-status")
          .locator(".r-v2-inventory-summary__metrics dd")
          .evaluateAll((nodes) =>
            nodes.map((node) => Number(node.textContent?.match(/[0-9]+/)?.[0])),
          ),
      )
      .toEqual(expected);
  };
  const waitCompleted = async (id: string): Promise<ScanOperationSnapshot> => {
    await expect
      .poll(
        async () => {
          const response = await page.request.get("/api/scan-operations/" + id);
          expect(response.ok()).toBe(true);
          const state = (await response.json()).state;
          if (["failed", "interrupted", "cancelled"].includes(state))
            throw new Error("Worker terminated: " + state);
          return state;
        },
        { timeout: 300000 },
      )
      .toBe("completed");
    return (await page.request.get("/api/scan-operations/" + id)).json();
  };
  await login(page);
  await page.goto("/scan");
  await clearMetadataProviders(page);
  await page
    .locator(".r-v2-scan-card__providers-group")
    .first()
    .locator(".r-select__field")
    .click();
  await page.getByRole("option", { name: "Steam", exact: true }).click();
  await page.keyboard.press("Escape");
  const start = page.locator(".r-v2-scan-card__start");
  await expect(start).toBeEnabled();
  const submitted = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/scan-operations",
  );
  const coldObservationOffset = readFileSync(
    "/phase34/evidence/observations.jsonl",
    "utf8",
  )
    .split("\n")
    .filter(Boolean).length;
  await start.click();
  const response = await submitted;
  expect(response.status()).toBe(202);
  expect(response.request().postDataJSON().apis).toEqual(["steam"]);
  const cold = await waitCompleted((await response.json()).id);
  checks.actual_ui_submit = true;
  checks.mouse = true;
  expect(cold.items_total).toBeGreaterThan(100);
  expect(cold.items!.length).toBeLessThanOrEqual(100);
  await page.reload();
  const panel = page.getByTestId("operation-status");
  await expect(panel.getByRole("status")).toContainText("Completed");
  checks.reload = true;
  await assertCounters(cold);
  const coldRequests = readFileSync(
    "/phase34/evidence/observations.jsonl",
    "utf8",
  )
    .split("\n")
    .filter(Boolean)
    .slice(coldObservationOffset)
    .map((line) => JSON.parse(line))
    .filter((row) => row.kind === "provider_http").length;
  expect(cold.scan_stats!.provider_requests).toBe(coldRequests);
  checks.terminal_unknown =
    (await panel.getByText("Not identified", { exact: true }).count()) > 0;
  expect(checks.terminal_unknown).toBe(true);
  await expect(panel.locator(".r-v2-inventory-summary__metrics")).toBeVisible();
  const beforeCount = await panel.locator(".r-v2-inventory-detail").count();
  const more = panel.getByRole("button", { name: "Load more", exact: true });
  await expect(more).toBeVisible();
  await more.click();
  await expect(more).toHaveCount(0);
  await expect(panel.getByRole("status")).toBeFocused();
  await expect
    .poll(() => panel.locator(".r-v2-inventory-detail").count())
    .toBeGreaterThan(beforeCount);
  const second = await page.request.get(
    "/api/scan-operations/" + cold.id + "?offset=100&limit=100",
  );
  expect(second.ok()).toBe(true);
  const pageTwo = await second.json();
  expect(pageTwo.items_offset).toBe(100);
  expect(pageTwo.items.length).toBeLessThanOrEqual(100);
  expect(pageTwo.scan_stats).toEqual(cold.scan_stats);
  checks.paged_details = true;
  checks.durable_counts = true;
  await clearMetadataProviders(page);
  fixture("seed", "seed");
  const before = fixture("inspect", "browser-warm-before");
  const observationOffset = readFileSync(
    "/phase34/evidence/observations.jsonl",
    "utf8",
  )
    .split("\n")
    .filter(Boolean).length;
  const warmResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/scan-operations",
  );
  await start.click();
  const warm = await waitCompleted((await (await warmResponse).json()).id);
  expect(warm.scan_stats!.inventory_unchanged).toBeGreaterThan(0);
  const scheduled = fixture(
    "scheduled",
    "browser-scheduled",
  ) as ScanOperationSnapshot;
  expect(scheduled.state).toBe("completed");
  expect(scheduled.scan_stats!.inventory_unchanged).toBeGreaterThan(0);
  checks.actual_scheduler = true;
  await accept(scheduled);
  await assertCounters(scheduled);
  const after = fixture("inspect", "browser-warm-after");
  expect(after.media).toEqual(before.media);
  expect(after.files).toEqual(before.files);
  expect(after.components).toEqual(before.components);
  const warmObservations = readFileSync(
    "/phase34/evidence/observations.jsonl",
    "utf8",
  )
    .split("\n")
    .filter(Boolean)
    .slice(observationOffset)
    .map((line) => JSON.parse(line));
  expect(
    warmObservations.filter((row) =>
      [
        "hash",
        "components",
        "enrichment",
        "media_prepare",
        "provider_http",
      ].includes(row.kind),
    ),
  ).toEqual([]);
  const boundary = commands.length;
  await page.context().setOffline(true);
  await page.evaluate(async () => {
    const path = "/src/services/socket.ts";
    const module = await import(path);
    module.default.disconnect();
  });
  await expect(panel).toContainText("Connection", { timeout: 30000 });
  await page.context().setOffline(false);
  const recoveredStatus = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      response.url().includes("/api/scan-operations/") &&
      response.status() === 200,
  );
  await panel
    .getByRole("button", { name: "Retry status", exact: true })
    .click();
  await recoveredStatus;
  await expect(panel.getByRole("status")).toContainText("Completed");
  await expect(panel.getByRole("status")).toBeFocused();
  await page.evaluate(async () => {
    const path = "/src/services/socket.ts";
    const module = await import(path);
    module.default.connect();
  });
  expect(
    commands.slice(boundary).filter((row) => row.method === "POST"),
  ).toEqual([]);
  checks.reconnect = true;
  checks.status_only = true;
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe(
    "BODY",
  );
  checks.keyboard = true;
  await start.scrollIntoViewIfNeeded();
  const box = await start.boundingBox();
  expect(box).toBeTruthy();
  const touchSubmitted = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/scan-operations",
  );
  await page.touchscreen.tap(box!.x + box!.width / 2, box!.y + box!.height / 2);
  checks.touch = true;
  await waitCompleted((await (await touchSubmitted).json()).id);
  const { states, stale, retained, physical, targets, heights } =
    await presentation(page, warm, accept, capture, checks, variants);
  const anonymous = await page
    .context()
    .browser()!
    .newContext({ baseURL: "http://127.0.0.1:3345" });
  const denied = await anonymous.request.get("/api/scan-operations/" + warm.id);
  expect([401, 403]).toContain(denied.status());
  await anonymous.close();
  await page.evaluate(async () => {
    const path = "/src/stores/auth.ts";
    const module = await import(path);
    module.default().user = null;
  });
  await expect(panel.locator(".r-v2-inventory-detail")).toHaveCount(0);
  checks.auth_isolation = true;
  writeFileSync(
    "/phase34/evidence/browser.json",
    JSON.stringify(
      {
        passed: Object.values(checks).every(Boolean),
        checks,
        screenshots,
        variants,
        actual: { cold, warm, scheduled, source_media_preserved: true },
        controlled_projection: {
          states,
          stale_version: stale.version,
          retained_version: retained.version,
        },
        gamepad: {
          physical_connected: physical,
          physical_test: "unavailable",
          synthetic_bridge: true,
        },
        targets,
        row_heights: heights,
        requests: commands,
      },
      null,
      2,
    ),
  );
});
