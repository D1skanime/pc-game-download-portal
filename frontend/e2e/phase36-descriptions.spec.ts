import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { clearMetadataProviders, identity, login } from "./fixtures/phase34";
import { presentation } from "./fixtures/phase36-description-presentation";

test("actual localized descriptions, manual protection and controlled presentation", async ({
  page,
  browser,
}) => {
  const checks = new Proxy<Record<string, boolean>>(
    {},
    {
      set(target, key, value) {
        Reflect.set(target, key, value);
        writeFileSync(
          "/phase34/evidence/browser-progress.json",
          JSON.stringify({ passed: false, checks: target }, null, 2),
        );
        return true;
      },
    },
  );
  const interactive: string[] = [];
  const entrypoints: Record<string, unknown>[] = [];
  const text = (key: string) =>
    page.evaluate(async (key) => {
      const path = "/src/locales/index.ts";
      return (await import(path)).default.global.t(key);
    }, key);
  const csrf = async () => {
    const cookie = (await page.context().cookies()).find(
      (item) => item.name === "romm_csrftoken",
    );
    return { "x-csrftoken": cookie?.value ?? "" };
  };
  const editDirect = async (id: number, tag: string, value: string | null) => {
    const row = await (await page.request.get("/api/roms/" + id)).json();
    const result = await page.request.put("/api/roms/" + id + "/description", {
      headers: await csrf(),
      data: {
        locale: tag,
        description: value,
        expected_version: row.updated_at,
      },
    });
    expect(result.ok()).toBe(true);
    return result.json();
  };
  const fixture = (
    action: string,
    stage: string,
    locale = "de",
    provider = "steam",
  ) => {
    execFileSync(
      "/app/.venv/bin/python",
      [
        "tools/phase36_description_client.py",
        action,
        "--stage",
        stage,
        "--locale",
        locale,
        "--provider",
        provider,
      ],
      {
        cwd: "/app/backend",
        env: process.env,
        encoding: "utf8",
        timeout: 180000,
      },
    );
    return JSON.parse(
      readFileSync("/phase34/evidence/" + stage + ".json", "utf8"),
    );
  };
  const initial = fixture("inspect", "browser-before");
  const known = initial.descriptions.find(
    (row: { name: string }) => row.name === "Known.Game",
  );
  const manual = initial.descriptions.find(
    (row: { name: string }) => row.name === "Manual",
  );
  await login(page);
  const locale = async (value: string) =>
    page.evaluate(async (value) => {
      const path = "/src/locales/index.ts";
      const module = await import(path);
      module.default.global.locale.value = value;
    }, value);
  const open = async (id: number) => {
    await page.goto("/rom/" + id);
    await locale("de_DE");
    await expect(page.locator(".overview-tab__summary")).toBeVisible();
  };
  await open(known.id);
  await expect(page.locator(".overview-tab__summary")).not.toContainText(
    "Untouched legacy scalar",
  );
  await expect(page.getByTestId("overview-description-edit")).toBeVisible();
  checks.legacy_empty = true;
  fixture("language", "browser-language-de");
  fixture("scan", "browser-repair");
  await open(known.id);
  await locale("de_DE");
  await expect(page.locator(".overview-tab__summary")).toContainText(
    "Deutscher Beschreibungstext",
  );
  await expect(page.locator(".overview-tab__summary")).toHaveAttribute(
    "lang",
    "de",
  );
  checks.actual_worker_refetch = true;
  const repaired = fixture("inspect", "browser-repaired");
  expect(
    repaired.descriptions.find((row: { id: number }) => row.id === manual.id)
      .manual,
  ).toEqual(manual.manual);
  checks.manual_protection = true;
  await page.getByTestId("overview-description-edit").click();
  const editor = page.getByTestId("localized-description-editor");
  await expect(editor).toBeVisible();
  await editor.locator("textarea").fill("Exact browser manual Deutsch");
  await expect(editor.locator(".r-select__field")).toHaveAttribute(
    "aria-disabled",
    "true",
  );
  const saved = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      response.url().includes("/description"),
  );
  await editor.locator("button").last().click();
  expect((await saved).ok()).toBe(true);
  await expect(editor).toHaveCount(0);
  await expect(page.locator(".overview-tab__summary")).toHaveText(
    "Exact browser manual Deutsch",
  );
  checks.actual_editor_save = true;
  await page.reload();
  await locale("de_DE");
  await expect(page.locator(".overview-tab__summary")).toHaveText(
    "Exact browser manual Deutsch",
  );
  checks.durable_manual = true;

  await page.getByTestId("overview-description-edit").click();
  await editor.locator("textarea").fill("Unsaved exact draft");
  await locale("fr_FR");
  await expect(editor.locator("textarea")).toHaveValue("Unsaved exact draft");
  await expect(editor.locator(".r-select__field")).toHaveAttribute(
    "aria-disabled",
    "true",
  );
  checks.dirty_locale = true;
  await editDirect(known.id, "fr", "Concurrent French manual");
  const conflict = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      response.url().includes("/description"),
  );
  await editor.locator("button").last().click();
  expect((await conflict).status()).toBe(409);
  await expect(editor.locator("textarea")).toHaveValue("Unsaved exact draft");
  checks.conflict409 = checks.background_refresh = true;
  await page.keyboard.press("Escape");
  await open(known.id);
  await page.getByTestId("overview-description-edit").click();
  await editor.locator("textarea").fill("Draft survives connection loss");
  await page.route("**/api/roms/" + known.id + "/description", (route) =>
    route.abort("failed"),
  );
  await editor.locator("button").last().click();
  await expect(editor.locator("textarea")).toHaveValue(
    "Draft survives connection loss",
  );
  await expect(editor.locator("button").last()).toBeEnabled();
  await page.unroute("**/api/roms/" + known.id + "/description");
  checks.error_retention = true;
  await page.keyboard.press("Escape");
  await editDirect(
    known.id,
    "de-DE",
    "<img src=x onerror=alert(1)> safe prose",
  );
  await open(known.id);
  await expect(page.locator(".overview-tab__summary")).toHaveText(
    "<img src=x onerror=alert(1)> safe prose",
  );
  await expect(page.locator(".overview-tab__summary img")).toHaveCount(0);
  checks.safe_markup = true;
  await page.getByTestId("overview-description-edit").click();
  const cleared = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      response.url().includes("/description"),
  );
  await editor.locator("button").nth(1).click();
  await editor.locator("button").last().click();
  expect((await cleared).ok()).toBe(true);
  const afterClear = await (
    await page.request.get("/api/roms/" + known.id)
  ).json();
  expect(afterClear.manual_metadata?.descriptions?.["de-DE"]).toBeUndefined();
  expect(afterClear.manual_metadata?.descriptions?.fr).toBe(
    "Concurrent French manual",
  );
  checks.clear_exact = true;
  const components = await (
    await page.request.get("/api/roms/" + known.id)
  ).json();
  const component = components.components.find(
    (row: { kind: string }) => row.kind === "dlc",
  );
  expect(component).toBeTruthy();
  await page.goto("/rom/" + known.id + "/dlc/" + component.id);
  await locale("de_DE");
  await expect(page.locator(".pc-dlc-detail__summary")).toContainText(
    "Deutscher Beschreibungstext",
  );
  await expect(page.locator(".pc-dlc-detail__summary")).toHaveAttribute(
    "lang",
    "de",
  );
  await page.getByTestId("pc-dlc-description-edit").click();
  await expect(editor.locator("textarea")).toHaveValue("");
  await page.keyboard.press("Escape");
  checks.component = true;
  await editDirect(known.id, "fr", null);

  const providerMarkup = (enabled: boolean) => {
    execFileSync(
      "/app/.venv/bin/python",
      [
        "-c",
        "import sys,json; sys.path.insert(0,'tools'); from phase33_collection_fixture import authority; authority(); " +
          "from pathlib import Path; p=Path('/phase34/evidence/provider-control.json'); " +
          "assert p.is_file() and not p.is_symlink(); d=json.loads(p.read_text()); " +
          "d['markup']=sys.argv[1]=='true'; p.write_text(json.dumps(d))",
        String(enabled),
      ],
      { cwd: "/app/backend", env: process.env, encoding: "utf8" },
    );
  };
  for (const provider of ["steam", "ss"]) {
    for (const tag of ["de", "fr", "en"]) {
      const malicious = provider === "steam" && tag === "de";
      providerMarkup(malicious);
      fixture("reset", "browser-reset-" + provider + tag, tag, provider);
      const target = initial.descriptions.find(
        (row: { name: string }) =>
          row.name === (provider === "steam" ? "Known.Game" : "Control.sfc"),
      );
      await open(target.id);
      await locale({ de: "de_DE", fr: "fr_FR", en: "en_US" }[tag]!);
      await page.locator(".r-v2-game-btn--action-more").click();
      await page
        .getByRole("menu")
        .getByRole("button", {
          name: await text("rom.match-rom"),
          exact: true,
        })
        .click();
      const search = page.locator("#r-v2-match-search");
      await search.fill(provider === "steam" ? "Known Game" : "Control");
      const nameSearch = page.waitForResponse(
        (response) => new URL(response.url()).pathname === "/api/search/roms",
      );
      await page.locator(".r-v2-match__search-btn").click();
      const nameResponse = await nameSearch;
      expect(nameResponse.ok()).toBe(true);
      expect(
        new URL(nameResponse.url()).searchParams
          .get("metadata_locale")
          ?.split("-")[0],
      ).toBe(tag);
      await expect(page.locator(".match-grid__card").first()).toBeVisible();
      await page.locator(".r-v2-match__by .r-select__field").click();
      await page
        .getByRole("option", {
          name: await text("rom.search-by-id"),
          exact: true,
        })
        .click();
      await search.fill(String(target[provider + "_id"]));
      const idSearch = page.waitForResponse(
        (response) => new URL(response.url()).pathname === "/api/search/roms",
      );
      await page.locator(".r-v2-match__search-btn").click();
      expect((await idSearch).ok()).toBe(true);
      await page
        .locator(".match-grid__card")
        .filter({ hasText: provider === "steam" ? "Known Game" : "Control" })
        .first()
        .click();
      await expect(page.locator(".match-grid__panel")).toBeVisible();
      const update = page.waitForResponse(
        (response) =>
          response.request().method() === "PUT" &&
          new URL(response.url()).pathname === "/api/roms/" + target.id,
      );
      await page
        .getByRole("button", {
          name: await text("rom.match-this-game"),
          exact: true,
        })
        .click();
      const confirmed = await update;
      expect(confirmed.ok()).toBe(true);
      expect(
        new URL(confirmed.url()).searchParams
          .get("metadata_locale")
          ?.split("-")[0],
      ).toBe(tag);
      await expect(page.locator(".r-v2-match__body")).toHaveCount(0);
      await page.reload();
      await locale({ de: "de_DE", fr: "fr_FR", en: "en_US" }[tag]!);
      const current = await (
        await page.request.get("/api/roms/" + target.id)
      ).json();
      expect(current[provider + "_id"]).toBe(target[provider + "_id"]);
      expect(
        current[provider + "_metadata"].text_variants[tag].summary,
      ).toBeTruthy();
      await expect(page.locator(".overview-tab__summary")).toHaveAttribute(
        "lang",
        tag,
      );
      const durable = fixture("inspect", "browser-confirmed-" + provider + tag);
      const stored = durable.descriptions.find(
        (row: { id: number }) => row.id === target.id,
      );
      expect(stored[provider].text_variants[tag].summary).toBe(
        current[provider + "_metadata"].text_variants[tag].summary,
      );
      const summary =
        current[provider + "_metadata"].text_variants[tag].summary;
      const summarySha = createHash("sha256").update(summary).digest("hex");
      const wire = readFileSync("/phase34/evidence/observations.jsonl", "utf8")
        .trim()
        .split("\n")
        .map((line) => JSON.parse(line))
        .filter(
          (row) =>
            row.kind === "provider_http" &&
            row.provider === provider &&
            row.response_text_variants?.some(
              (slot: { summary_sha256: string }) =>
                slot.summary_sha256 === summarySha,
            ),
        );
      expect(wire.length).toBeGreaterThan(0);
      expect(
        wire.every((row) => /^[a-f0-9]{64}$/.test(row.response_sha256)),
      ).toBe(true);
      if (malicious) {
        await expect(page.locator(".overview-tab__summary")).toContainText(
          "<img",
        );
        await expect(page.locator(".overview-tab__summary img")).toHaveCount(0);
        checks.safe_provider_markup = true;
      }
      entrypoints.push({
        provider,
        locale: tag,
        summarySha,
        rawPayloadHashes: wire.map((row) => row.response_sha256),
        rawSourceLanguage: provider === "ss" ? tag : null,
        languageEvidence:
          provider === "ss"
            ? "raw synopsis language"
            : "requested Steam language plus validated distinct variant",
      });
      providerMarkup(false);
      interactive.push("interactive-" + provider + tag);
      entrypoints.push({
        provider,
        locale: tag,
        nameSearch: nameResponse.status(),
        sameId: true,
        durable: stored.id,
      });
    }
  }
  checks.source_language = true;
  const manualEnglish = initial.descriptions.find(
    (row: { name: string }) => row.name === "ManualEnglish",
  );
  await open(manualEnglish.id);
  await expect(page.locator(".overview-tab__summary")).toContainText(
    "Deutscher Beschreibungstext",
  );
  const manualEnglishApi = await (
    await page.request.get("/api/roms/" + manualEnglish.id)
  ).json();
  expect(manualEnglishApi.manual_metadata.descriptions.en).toBe(
    "Protected manual English",
  );
  await open(manual.id);
  await expect(page.locator(".overview-tab__summary")).toHaveText(
    "Protected Deutsch",
  );
  await locale("en_US");
  await expect(page.locator(".overview-tab__summary")).toHaveText(
    "Protected English",
  );
  const auth = fixture("auth", "browser-auth");
  expect(auth.me_write_global_status).toBe(403);
  expect(auth.readonly_description_status).toBe(403);
  checks.authorization = true;

  await page.goto("/user-interface");
  await locale("en_US");
  const languageField = page
    .locator(".r-v2-ui__field .r-select__field")
    .first();
  await languageField.click();
  const languageWrite = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      new URL(response.url()).pathname === "/api/config/scan/language",
  );
  await page.getByRole("option", { name: "Français", exact: true }).click();
  expect((await languageWrite).ok()).toBe(true);
  const configured = await (await page.request.get("/api/config")).json();
  expect(configured.SCAN_LANGUAGE_PRIORITY[0]).toBe("fr");
  checks.admin_language = true;
  const scheduled = fixture("scheduled", "browser-scheduled-fr", "de");
  expect(scheduled.accepted_request.metadata_locale).toBe("fr");
  checks.scheduled_language = true;
  await page.route("**/api/config/scan/language", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "controlled config write failure" }),
    }),
  );
  await languageField.click();
  const failedConfig = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      new URL(response.url()).pathname === "/api/config/scan/language",
  );
  await page.getByRole("option", { name: "Deutsch", exact: true }).click();
  expect((await failedConfig).status()).toBe(500);
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: /controlled config write failure|500/ }),
  ).toBeVisible();
  await expect
    .poll(
      async () =>
        (await (await page.request.get("/api/config")).json())
          .SCAN_LANGUAGE_PRIORITY[0],
    )
    .toBe("fr");
  await page.unroute("**/api/config/scan/language");
  checks.config_failure = true;

  await page.route("**/api/config/scan/language", async (route) => {
    const current = route.request().postDataJSON();
    expect(
      (
        await page.request.put("/api/config/scan/language", {
          headers: await csrf(),
          data: {
            language_priority: ["en", "fr", "de"],
            expected_language_priority: current.expected_language_priority,
          },
        })
      ).ok(),
    ).toBe(true);
    await route.continue();
  });
  await languageField.click();
  const cas = page.waitForResponse(
    (r) =>
      r.request().method() === "PUT" &&
      new URL(r.url()).pathname === "/api/config/scan/language",
  );
  await page.getByRole("option", { name: "Deutsch", exact: true }).click();
  expect((await cas).status()).toBe(409);
  await page.unroute("**/api/config/scan/language");
  checks.config_cas = true;
  const waitOperation = async (id: string) => {
    await expect
      .poll(
        async () =>
          (await (await page.request.get("/api/scan-operations/" + id)).json())
            .state,
        { timeout: 240000 },
      )
      .toBe("completed");
    return (await page.request.get("/api/scan-operations/" + id)).json();
  };
  for (const provider of ["steam", "ss"]) {
    fixture("reset", "browser-refresh-reset-" + provider, "en", provider);
    const target = initial.descriptions.find(
      (row: { name: string }) =>
        row.name === (provider === "steam" ? "Known.Game" : "Control.sfc"),
    );
    await open(target.id);
    await locale("en_US");
    await page.locator(".r-v2-game-btn--action-more").click();
    await page
      .getByRole("menu")
      .getByRole("button", {
        name: await text("rom.refresh-metadata"),
        exact: true,
      })
      .click();
    const submitted = page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        new URL(r.url()).pathname === "/api/scan-operations",
    );
    await page
      .getByRole("button", {
        name: await text("rom.refresh-metadata"),
        exact: true,
      })
      .click();
    const accepted = await (await submitted).json();
    await waitOperation(accepted.id);
    const refreshed = await (
      await page.request.get("/api/roms/" + target.id)
    ).json();
    expect(
      refreshed[provider + "_metadata"].text_variants.en.summary,
    ).toBeTruthy();
    entrypoints.push({
      provider,
      entrypoint: "game-refresh",
      operation: accepted.id,
      locale: "en",
    });
  }
  checks.game_refresh = true;
  await page.goto("/scan");
  await locale("en_US");
  await clearMetadataProviders(page);
  await page
    .locator(".r-v2-scan-card__providers-group")
    .first()
    .locator(".r-select__field")
    .click();
  await page.getByRole("option", { name: "Steam", exact: true }).click();
  await page
    .getByRole("option", { name: "ScreenScraper", exact: true })
    .click();
  await page.keyboard.press("Escape");
  const submitted = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      new URL(r.url()).pathname === "/api/scan-operations",
  );
  await page.locator(".r-v2-scan-card__start").click();
  const acceptedResponse = await submitted;
  expect(acceptedResponse.ok()).toBe(true);
  const accepted = await acceptedResponse.json();
  expect(
    acceptedResponse.request().postDataJSON().metadata_locale.split("-")[0],
  ).toBe("en");
  await locale("fr_FR");
  await waitOperation(accepted.id);
  const captured = execFileSync(
    "/app/.venv/bin/python",
    [
      "-c",
      "import sys; sys.path.insert(0, 'tools'); from phase33_collection_fixture import authority; authority(); " +
        "from handler.database.base_handler import sync_session; from models.scan_operation import ScanOperation; " +
        "s=sync_session(); print(s.get(ScanOperation,sys.argv[1]).command['request']['metadata_locale']); s.close()",
      accepted.id,
    ],
    { cwd: "/app/backend", env: process.env, encoding: "utf8" },
  ).trim();
  expect(captured.split("-")[0]).toBe("en");
  checks.manual_scan = checks.accepted_snapshot = true;
  expect(
    (
      await page.request.post("/api/users", {
        headers: await csrf(),
        data: {
          username: "phase36-viewer",
          email: "phase36-viewer@example.test",
          password: identity().password,
          role: "viewer",
        },
      })
    ).ok(),
  ).toBe(true);
  const viewerContext = await browser.newContext({
    baseURL: "http://127.0.0.1:3345",
    serviceWorkers: "block",
  });
  try {
    const viewer = await viewerContext.newPage();
    await viewer.goto("/login");
    await viewer
      .locator("form.r-v2-login-form input[name=username]")
      .fill("phase36-viewer");
    await viewer
      .locator("form.r-v2-login-form input[name=password]")
      .fill(identity().password);
    await viewer.locator("form.r-v2-login-form button[type=submit]").click();
    await expect(viewer).not.toHaveURL(new RegExp("/login"));
    await viewer.goto("/rom/" + known.id);
    await expect(viewer.locator(".overview-tab__summary")).toBeVisible();
    await expect(viewer.getByTestId("overview-description-edit")).toHaveCount(
      0,
    );
    checks.read_only = true;
    const globalBefore = (await (await page.request.get("/api/config")).json())
      .SCAN_LANGUAGE_PRIORITY;
    let writes = 0;
    viewer.on("request", (r) => {
      if (
        r.method() === "PUT" &&
        new URL(r.url()).pathname === "/api/config/scan/language"
      )
        writes++;
    });
    await viewer.goto("/user-interface");
    await viewer.locator(".r-v2-ui__field .r-select__field").first().click();
    await viewer.getByRole("option", { name: "Deutsch", exact: true }).click();
    await expect
      .poll(() =>
        viewer.evaluate(() => localStorage.getItem("settings.locale")),
      )
      .toContain("de_DE");
    expect(writes).toBe(0);
    expect(
      (await (await page.request.get("/api/config")).json())
        .SCAN_LANGUAGE_PRIORITY,
    ).toEqual(globalBefore);
    checks.personal_no_global_write = true;
  } finally {
    await viewerContext.close();
  }

  fixture("interactive", "browser-view-fr", "fr", "steam");
  const beforeViewApi = await (
    await page.request.get("/api/roms/" + known.id)
  ).json();
  expect(beforeViewApi.steam_metadata.text_variants.fr.summary).toBeTruthy();
  expect(beforeViewApi.steam_metadata.text_variants.en.summary).toBeTruthy();
  await open(known.id);
  const beforeView = readFileSync(
    "/phase34/evidence/observations.jsonl",
    "utf8",
  );
  await locale("fr_FR");
  await expect(page.locator(".overview-tab__summary")).toHaveAttribute(
    "lang",
    "fr",
  );
  await locale("en_US");
  await expect(page.locator(".overview-tab__summary")).toHaveAttribute(
    "lang",
    "en",
  );
  expect(readFileSync("/phase34/evidence/observations.jsonl", "utf8")).toBe(
    beforeView,
  );
  checks.no_view_transport = true;
  const matrix = await presentation(page);
  Object.assign(checks, matrix.checks);

  writeFileSync(
    "/phase34/evidence/browser.json",
    JSON.stringify(
      {
        phase: 36,
        passed: true,
        checks,
        matrix,
        interactive,
        entrypoints,
        controlledPresentation: true,
        physicalController: "unverified",
      },
      null,
      2,
    ),
  );
});
