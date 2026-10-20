import {
  AxiosError,
  type AxiosAdapter,
  type InternalAxiosRequestConfig,
} from "axios";
import Cookies from "js-cookie";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";
import type { ScanOperationSnapshot, UserSchema } from "@/__generated__";
import api from "@/services/api";
import socket from "@/services/socket";
import useAuthStore from "@/stores/auth";
import { buildLibraryScanRequest, toScanOperationRequest } from "../operations";
import { startLegacyScan, stopLegacyScan } from "./legacy/scan";
import scanOperations from "./scanOperations";

vi.mock("@/plugins/router", () => ({
  default: {
    currentRoute: { value: { name: "scan" } },
    resolve: () => ({ name: "scan" }),
    push: vi.fn(),
  },
  ROUTES: { LOGIN: "login" },
  isAuthExemptRoute: () => false,
}));
vi.mock("@/services/socket", () => ({ default: { emit: vi.fn() } }));

const actor = (id = 7): UserSchema => ({
  id,
  username: "synthetic-admin",
  email: null,
  enabled: true,
  role: "admin",
  oauth_scopes: ["tasks.run"],
  avatar_path: "",
  last_login: null,
  last_active: null,
  created_at: "2026-10-19T00:00:00Z",
  updated_at: "2026-10-19T00:00:00Z",
});
const request = () =>
  buildLibraryScanRequest({
    operationId: "request-34-07",
    kind: "metadata-refresh",
    scope: {
      kind: "filesystem",
      platformFsSlugs: ["win"],
      relativePaths: { win: "Games/Spiel 日本" },
    },
    profiles: [
      {
        rootId: "library",
        mappingId: 12,
        mappingRevision: 3,
        layout: "pc-nested",
        itemKind: "game",
        platformId: 7,
        platformFsSlug: "win",
      },
    ],
    uiLocale: "de-DE",
    metadataLocale: "de-DE",
    providers: ["steam", "igdb"],
    playmatchEnabled: true,
    launchboxRemoteEnabled: false,
    scanType: "complete",
  });
const snapshot = (
  overrides: Partial<ScanOperationSnapshot> = {},
): ScanOperationSnapshot => ({
  id: "11111111-1111-4111-8111-111111111111",
  request_key: "request-34-07",
  job_id: "scan-server-job",
  attempt_id: "server-attempt",
  version: 8,
  state: "queued",
  intentional_cancel: false,
  dispatch_pending: false,
  scan_stats: { scanned: 2 },
  queue_condition: "available",
  created_at: "2026-10-19T00:00:00Z",
  updated_at: "2026-10-19T00:00:01Z",
  ...overrides,
});
function response(
  config: InternalAxiosRequestConfig,
  data: unknown,
  status = 200,
) {
  return { data, status, statusText: "synthetic", headers: {}, config };
}
function failure(config: InternalAxiosRequestConfig, status?: number) {
  return new AxiosError(
    "synthetic failure",
    status ? "ERR_BAD_RESPONSE" : "ECONNABORTED",
    config,
    undefined,
    status ? response(config, { detail: "safe_test_code" }, status) : undefined,
  );
}

const transport = vi.fn<AxiosAdapter>();
const originalAdapter = api.defaults.adapter;
beforeEach(() => {
  setActivePinia(createPinia());
  useAuthStore().setCurrentUser(actor());
  localStorage.clear();
  vi.clearAllMocks();
  Cookies.set("romm_csrftoken", "synthetic-csrf");
  api.defaults.adapter = transport;
  transport.mockImplementation(async (config) => response(config, snapshot()));
});
afterEach(() => {
  useAuthStore().reset();
  api.defaults.adapter = originalAdapter;
  Cookies.remove("romm_csrftoken");
  vi.useRealTimers();
});

describe("shared authenticated scan commands", () => {
  it("returns server lineage through the compatibility export without emitting", async () => {
    const result = await startLegacyScan(request());
    expect(result).toEqual(snapshot());
    expect(transport).toHaveBeenCalledTimes(1);
    const config = transport.mock.calls[0][0];
    expect(config.url).toBe("/scan-operations");
    expect(JSON.parse(config.data)).toEqual(toScanOperationRequest(request()));
    expect(config.headers.get("x-csrftoken")).toBe("synthetic-csrf");
    expect(config.timeout).toBeLessThanOrEqual(10000);
    expect(socket.emit).not.toHaveBeenCalled();
  });

  it("reconciles a lost acceptance response by its original key before retrying", async () => {
    transport.mockImplementation(async (config) => {
      if (config.method === "post") throw failure(config);
      return response(config, snapshot({ version: 9, state: "running" }));
    });
    expect(await startLegacyScan(request())).toEqual(
      snapshot({ version: 9, state: "running" }),
    );
    expect(
      transport.mock.calls.map(([config]) => [config.method, config.url]),
    ).toEqual([
      ["post", "/scan-operations"],
      ["get", "/scan-operations/by-request/request-34-07"],
    ]);
    expect(socket.emit).not.toHaveBeenCalled();
  });

  it("waits for a server stopping snapshot through the compatibility cancel export", async () => {
    await startLegacyScan(request());
    transport.mockImplementation(async (config) =>
      response(
        config,
        config.method === "post"
          ? snapshot({
              state: "stopping",
              version: 9,
              intentional_cancel: true,
            })
          : snapshot(),
      ),
    );
    expect(await stopLegacyScan()).toEqual(
      snapshot({ state: "stopping", version: 9, intentional_cancel: true }),
    );
    expect(socket.emit).not.toHaveBeenCalled();
  });
});

describe("durable scan reconciliation", () => {
  it("accepts a reactive mapped request without mutating its scope", async () => {
    const input = reactive(request());
    const result = await scanOperations.submit(input);
    expect(result).toEqual(snapshot());
    expect(JSON.parse(transport.mock.calls[0][0].data)).toEqual(
      toScanOperationRequest(request()),
    );
    expect(input.scope).toEqual(request().scope);
  });

  it("retains the original key on confirmed absence after a lost response without blind resubmission", async () => {
    transport.mockImplementation(async (config) => {
      throw failure(config, config.method === "get" ? 404 : undefined);
    });
    await expect(scanOperations.submit(request())).rejects.toMatchObject({
      code: "ECONNABORTED",
    });
    expect(transport.mock.calls.map(([config]) => config.method)).toEqual([
      "post",
      "get",
    ]);
    expect(JSON.parse(localStorage.getItem("pgdp.scan-operation.7")!)).toEqual({
      request_key: "request-34-07",
    });
  });

  it("allows a new request after an authoritative stale-key 404", async () => {
    localStorage.setItem(
      "pgdp.scan-operation.7",
      JSON.stringify({ request_key: "stale-request" }),
    );
    transport.mockImplementation(async (config) => {
      if (config.url === "/scan-operations/by-request/stale-request")
        throw failure(config, 404);
      return response(config, snapshot());
    });
    expect((await scanOperations.submit(request())).id).toBe(snapshot().id);
    expect(transport.mock.calls.map(([config]) => config.method)).toEqual([
      "get",
      "post",
    ]);
  });

  it("never repeats POST when the original-key lookup also times out", async () => {
    transport.mockImplementation(async (config) => {
      throw failure(config);
    });
    await expect(scanOperations.submit(request())).rejects.toMatchObject({
      code: "ECONNABORTED",
    });
    expect(transport.mock.calls.map(([c]) => [c.method, c.url])).toEqual([
      ["post", "/scan-operations"],
      ["get", "/scan-operations/by-request/request-34-07"],
    ]);
    expect(JSON.parse(localStorage.getItem("pgdp.scan-operation.7")!)).toEqual({
      request_key: "request-34-07",
    });
    transport.mockClear();
    await expect(scanOperations.submit(request())).rejects.toMatchObject({
      code: "ECONNABORTED",
    });
    expect(transport.mock.calls.map(([c]) => c.method)).toEqual(["get"]);
    transport.mockClear();
    const different = request();
    different.idempotencyKey = "another-request";
    await expect(scanOperations.submit(different)).rejects.toMatchObject({
      code: "ECONNABORTED",
    });
    expect(transport.mock.calls.map(([c]) => c.url)).toEqual([
      "/scan-operations/by-request/request-34-07",
    ]);
  });

  it("coalesces immediate repeated clicks while delayed acceptance remains unresolved", async () => {
    let release!: (value: ReturnType<typeof response>) => void;
    transport.mockImplementation(
      (config) =>
        new Promise((resolve) => {
          release = (value) => resolve({ ...value, config });
        }),
    );
    const input = request();
    input.permissions.actorId = 99;
    const first = scanOperations.submit(input);
    const second = scanOperations.submit(input);
    await vi.waitFor(() => expect(transport).toHaveBeenCalledTimes(1));
    const changed = request();
    changed.idempotencyKey = "second-click";
    await expect(scanOperations.submit(changed)).rejects.toThrow(
      "scan_submission_pending",
    );
    release(response(transport.mock.calls[0][0], snapshot()));
    expect(await first).toEqual(snapshot());
    expect(await second).toEqual(snapshot());
    expect(transport).toHaveBeenCalledTimes(1);
    expect(socket.emit).not.toHaveBeenCalled();
    expect(JSON.parse(localStorage.getItem("pgdp.scan-operation.7")!)).toEqual({
      request_key: "request-34-07",
      operation_id: snapshot().id,
    });
    expect(localStorage.getItem("pgdp.scan-operation.99")).toBeNull();
  });

  it("keeps server digest conflicts authoritative on an explicit same-key replay", async () => {
    await scanOperations.submit(request());
    transport.mockClear();
    transport.mockImplementation(async (config) => {
      if (config.method === "post") throw failure(config, 409);
      return response(config, snapshot());
    });
    const changed = request();
    changed.providerPolicy.providers = ["steam"];
    await expect(scanOperations.submit(changed)).rejects.toMatchObject({
      response: { status: 409 },
    });
    expect(transport.mock.calls.map(([c]) => c.method)).toEqual([
      "get",
      "post",
    ]);
    expect(JSON.parse(transport.mock.calls[1][0].data)).toMatchObject({
      request_key: "request-34-07",
      apis: ["steam", "playmatch"],
    });
  });

  it("recovers stored confirmed identity after memory loss without any submission", async () => {
    await scanOperations.submit(request());
    const saved = localStorage.getItem("pgdp.scan-operation.7")!;
    useAuthStore().reset();
    useAuthStore().setCurrentUser(actor());
    localStorage.setItem("pgdp.scan-operation.7", saved);
    transport.mockClear();
    expect(await scanOperations.restore()).toEqual(snapshot());
    expect(transport.mock.calls.map(([c]) => [c.method, c.url])).toEqual([
      ["get", "/scan-operations/" + snapshot().id],
    ]);
  });

  it("recovers a pending request from its original key without creating work", async () => {
    localStorage.setItem(
      "pgdp.scan-operation.7",
      JSON.stringify({ request_key: "request-34-07" }),
    );
    expect(await scanOperations.restore()).toEqual(snapshot());
    expect(transport.mock.calls.map(([c]) => [c.method, c.url])).toEqual([
      ["get", "/scan-operations/by-request/request-34-07"],
    ]);
  });

  it("uses server active lookup when browser identity is absent", async () => {
    expect(await scanOperations.restore()).toEqual(snapshot({}));
    expect(transport.mock.calls.map(([c]) => [c.method, c.url])).toEqual([
      ["get", "/scan-operations/active"],
    ]);
  });

  it("handles a missing saved operation through active lookup but propagates outages", async () => {
    localStorage.setItem(
      "pgdp.scan-operation.7",
      JSON.stringify({
        request_key: "request-34-07",
        operation_id: snapshot().id,
      }),
    );
    transport.mockImplementation(async (config) => {
      if (config.url?.endsWith("/active")) return response(config, null);
      throw failure(config, 404);
    });
    expect(await scanOperations.restore()).toBeNull();
    expect(transport.mock.calls.map(([c]) => c.url)).toEqual([
      "/scan-operations/" + snapshot().id,
      "/scan-operations/active",
    ]);
    transport.mockClear();
    transport.mockImplementation(async (config) => {
      throw failure(config, 503);
    });
    await expect(scanOperations.restore()).rejects.toMatchObject({
      response: { status: 503 },
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it("removes identity on authenticated reset and isolates the next actor", async () => {
    await scanOperations.submit(request());
    useAuthStore().reset();
    expect(localStorage.getItem("pgdp.scan-operation.7")).toBeNull();
    useAuthStore().setCurrentUser(actor(8));
    transport.mockClear();
    await scanOperations.restore();
    expect(transport.mock.calls[0][0].url).toBe("/scan-operations/active");
    expect(localStorage.getItem("pgdp.scan-operation.7")).toBeNull();
    expect(JSON.parse(localStorage.getItem("pgdp.scan-operation.8")!)).toEqual({
      request_key: snapshot().request_key,
      operation_id: snapshot().id,
    });
  });

  it("clears on real shared-client logout and rejects delayed responses after logout", async () => {
    let release!: () => void;
    transport.mockImplementation((config) => {
      if (config.url === "/logout")
        return Promise.resolve(response(config, {}));
      return new Promise((resolve) => {
        release = () => resolve(response(config, snapshot()));
      });
    });
    const pending = scanOperations.submit(request());
    const rejected = expect(pending).rejects.toThrow("scan_session_changed");
    await vi.waitFor(() => expect(transport).toHaveBeenCalledTimes(1));
    await api.post("/logout", {});
    expect(localStorage.getItem("pgdp.scan-operation.7")).toBeNull();
    release();
    await rejected;
    expect(localStorage.getItem("pgdp.scan-operation.7")).toBeNull();
  });

  it("rejects a delayed response from an old actor without saving it for the new actor", async () => {
    let release!: () => void;
    transport.mockImplementation(
      (config) =>
        new Promise((resolve) => {
          release = () => resolve(response(config, snapshot()));
        }),
    );
    const pending = scanOperations.submit(request());
    const rejected = expect(pending).rejects.toThrow("scan_session_changed");
    await vi.waitFor(() => expect(transport).toHaveBeenCalledTimes(1));
    useAuthStore().setCurrentUser(actor(8));
    release();
    await rejected;
    expect(localStorage.getItem("pgdp.scan-operation.7")).toBeNull();
    expect(localStorage.getItem("pgdp.scan-operation.8")).toBeNull();
  });

  it.each([403, 404, 409, 503])(
    "preserves HTTP %i lookup failures without mutation",
    async (code) => {
      transport.mockImplementation(async (config) => {
        throw failure(config, code);
      });
      await expect(
        scanOperations.byRequest("request-34-07"),
      ).rejects.toMatchObject({ response: { status: code } });
      expect(transport.mock.calls.map(([c]) => c.method)).toEqual(["get"]);
    },
  );

  it("rejects anonymous and malformed lookup requests before transport", async () => {
    await expect(scanOperations.byRequest("../unsafe")).rejects.toThrow(
      "invalid_scan_request_key",
    );
    expect(transport).not.toHaveBeenCalled();
    useAuthStore().reset();
    await expect(scanOperations.submit(request())).rejects.toThrow(
      "scan_authentication_required",
    );
    expect(transport).not.toHaveBeenCalled();
  });

  it("uses the existing CSRF refresh without automatically repeating a forbidden POST", async () => {
    transport.mockImplementation(async (config) => {
      if (config.url === "/heartbeat") {
        Cookies.set("romm_csrftoken", "refreshed-synthetic-csrf");
        return response(config, {});
      }
      throw new AxiosError(
        "CSRF",
        "ERR_BAD_RESPONSE",
        config,
        undefined,
        response(config, "CSRF failed", 403),
      );
    });
    await expect(scanOperations.submit(request())).rejects.toMatchObject({
      response: { status: 403 },
    });
    expect(transport.mock.calls.map(([c]) => [c.method, c.url])).toEqual([
      ["post", "/scan-operations"],
      ["get", "/heartbeat"],
    ]);
    transport.mockClear();
    transport.mockImplementation(async (config) => {
      if (config.method === "get") throw failure(config, 404);
      return response(config, snapshot());
    });
    await scanOperations.submit(request());
    const posted = transport.mock.calls.find(([c]) => c.method === "post")![0];
    expect(posted.headers.get("x-csrftoken")).toBe("refreshed-synthetic-csrf");
  });

  it.each([
    "accepted",
    "queued",
    "running",
    "stopping",
    "cancelled",
    "interrupted",
    "recovering",
    "blocked",
    "failed",
    "completed",
    "completed-with-warnings",
  ] as const)(
    "retains confirmed %s state and version, attempt, job, item and queue lineage",
    async (state) => {
      const server = snapshot({
        state,
        version: 42,
        queue_condition: "expired",
        cause_code: "source_identity_changed",
        next_action: "verify_source",
        items: [
          {
            id: 11,
            target_key: "target-11",
            mapping_id: 12,
            expected_revision: 3,
            relative_path: "Games/Spiel 日本",
            provider: "steam",
            outcome: "warning",
            cause_code: "provider_unavailable",
            attempt_id: "server-attempt",
          },
        ],
      });
      transport.mockImplementation(async (config) => response(config, server));
      expect(await scanOperations.status(server.id, 2, 10)).toEqual(server);
      expect(transport.mock.calls[0][0].params).toEqual({
        offset: 2,
        limit: 10,
      });
    },
  );

  it("keeps restore functional if storage is unavailable and discards malformed local identities", async () => {
    localStorage.setItem(
      "pgdp.scan-operation.7",
      JSON.stringify({ request_key: 123 }),
    );
    await scanOperations.restore();
    expect(transport.mock.calls[0][0].url).toBe("/scan-operations/active");
    useAuthStore().reset();
    useAuthStore().setCurrentUser(actor());
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("storage disabled");
    });
    transport.mockClear();
    expect(await scanOperations.submit(request())).toEqual(snapshot());
    expect(transport).toHaveBeenCalledTimes(1);
    vi.restoreAllMocks();
  });

  it.each([
    [-1, 100],
    [0, 101],
    [0, 0],
    [1.5, 100],
    [0, NaN],
  ])(
    "rejects unsafe detail page offset %s limit %s before transport",
    async (offset, limit) => {
      await expect(
        scanOperations.status(snapshot().id, offset, limit),
      ).rejects.toThrow("invalid_scan_page");
      expect(transport).not.toHaveBeenCalled();
    },
  );
  it("rejects mismatched operation identity in a detail page", async () => {
    transport.mockImplementation(async (config) =>
      response(config, { ...snapshot(), id: "other-operation" }),
    );
    await expect(
      scanOperations.status(snapshot().id, 100, 100),
    ).rejects.toThrow("scan_response_identity_mismatch");
  });
});

describe("confirmed scan control", () => {
  it("sends explicit versioned resume and selected metadata retry commands", async () => {
    const stopped = snapshot({ state: "cancelled", intentional_cancel: true });
    const recovered = snapshot({
      state: "recovering",
      version: 9,
      attempt_id: "new-attempt",
      job_id: "new-job",
    });
    transport.mockImplementation(async (config) => response(config, recovered));
    expect(await scanOperations.resume(stopped, "resume-34-07")).toEqual(
      recovered,
    );
    expect(JSON.parse(transport.mock.calls[0][0].data)).toEqual({
      request_key: "resume-34-07",
      expected_version: 8,
      item_ids: [],
    });
    expect(transport.mock.calls[0][0].url).toBe(
      "/scan-operations/" + stopped.id + "/resume",
    );
    expect(
      await scanOperations.retryMetadata(stopped, [9, 3, 9], "retry-34-07"),
    ).toEqual(recovered);
    expect(JSON.parse(transport.mock.calls[1][0].data)).toEqual({
      request_key: "retry-34-07",
      expected_version: 8,
      item_ids: [3, 9],
    });
    expect(transport.mock.calls[1][0].url).toBe(
      "/scan-operations/" + stopped.id + "/retry-metadata",
    );
    expect(
      transport.mock.calls.every(
        ([c]) => c.headers.get("x-csrftoken") === "synthetic-csrf",
      ),
    ).toBe(true);
    expect(socket.emit).not.toHaveBeenCalled();
  });

  it("looks up the original operation after lost cancellation and returns confirmed stopping", async () => {
    transport.mockImplementation(async (config) => {
      if (config.method === "post") throw failure(config);
      return response(
        config,
        snapshot({ version: 9, state: "stopping", intentional_cancel: true }),
      );
    });
    expect(await scanOperations.cancel(snapshot(), "cancel-34-07")).toEqual(
      snapshot({ version: 9, state: "stopping", intentional_cancel: true }),
    );
    expect(transport.mock.calls.map(([c]) => [c.method, c.url])).toEqual([
      ["post", "/scan-operations/" + snapshot().id + "/cancel"],
      ["get", "/scan-operations/by-request/request-34-07"],
    ]);
  });

  it("replays an unobserved mutation with the same key and expected version after lookup", async () => {
    let posts = 0;
    transport.mockImplementation(async (config) => {
      if (config.method === "post" && ++posts === 1) throw failure(config);
      return response(
        config,
        config.method === "get"
          ? snapshot()
          : snapshot({ version: 9, state: "stopping" }),
      );
    });
    await scanOperations.cancel(snapshot(), "cancel-34-07");
    expect(transport.mock.calls.map(([c]) => c.method)).toEqual([
      "post",
      "get",
      "post",
    ]);
    const bodies = transport.mock.calls
      .filter(([c]) => c.method === "post")
      .map(([c]) => JSON.parse(c.data));
    expect(bodies).toEqual([
      { request_key: "cancel-34-07", expected_version: 8, item_ids: [] },
      { request_key: "cancel-34-07", expected_version: 8, item_ids: [] },
    ]);
  });

  it("never retries a mutation after lookup timeout or masked not-found", async () => {
    transport.mockImplementation(async (config) => {
      throw failure(config);
    });
    await expect(
      scanOperations.resume(snapshot(), "resume-34-07"),
    ).rejects.toMatchObject({ code: "ECONNABORTED" });
    expect(transport.mock.calls.map(([c]) => c.method)).toEqual([
      "post",
      "get",
    ]);
    transport.mockClear();
    transport.mockImplementation(async (config) => {
      throw failure(config, config.method === "get" ? 404 : undefined);
    });
    await expect(
      scanOperations.cancel(snapshot(), "cancel-34-07"),
    ).rejects.toMatchObject({ response: { status: 404 } });
    expect(transport.mock.calls.map(([c]) => c.method)).toEqual([
      "post",
      "get",
    ]);
  });

  it("rejects empty, oversized and unsafe metadata retry scopes before transport", async () => {
    for (const items of [
      [],
      [0],
      [-1],
      [1.5],
      Array.from({ length: 101 }, (_, i) => i + 1),
    ]) {
      await expect(
        scanOperations.retryMetadata(snapshot(), items, "retry-34-07"),
      ).rejects.toThrow();
    }
    await expect(
      scanOperations.cancel(snapshot({ version: 0 }), "cancel-34-07"),
    ).rejects.toThrow("invalid_scan_mutation");
    expect(transport).not.toHaveBeenCalled();
  });
});
