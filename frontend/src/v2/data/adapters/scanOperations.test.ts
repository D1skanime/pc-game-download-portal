import {
  AxiosError,
  type AxiosAdapter,
  type InternalAxiosRequestConfig,
} from "axios";
import Cookies from "js-cookie";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ScanOperationSnapshot, UserSchema } from "@/__generated__";
import api from "@/services/api";
import socket from "@/services/socket";
import useAuthStore from "@/stores/auth";
import { buildLibraryScanRequest, toScanOperationRequest } from "../operations";
import { startLegacyScan, stopLegacyScan } from "./legacy/scan";

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
