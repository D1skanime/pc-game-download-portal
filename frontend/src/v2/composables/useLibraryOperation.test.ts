import { flushPromises } from "@vue/test-utils";
import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";
import type {
  OperationRequest,
  ScanOperationSnapshot,
} from "@/v2/data/contracts";

const fake = vi.hoisted(() => ({
  submit: vi.fn(),
  byRequest: vi.fn(),
  cancel: vi.fn(),
  resume: vi.fn(),
  retryMetadata: vi.fn(),
  refresh: vi.fn(),
  dispose: vi.fn(),
}));
const snapshot = ref<ScanOperationSnapshot | null>(null);
vi.mock("@/v2/data/adapters/scanOperations", () => ({ default: fake }));
vi.mock("@/v2/composables/useScanOperationStatus", () => ({
  useScanOperationStatus: () => ({
    snapshot,
    active: ref(false),
    reconciling: ref(false),
    disconnected: ref(false),
    errorCode: ref(null),
    refresh: fake.refresh,
    dispose: fake.dispose,
    accept(next: ScanOperationSnapshot) {
      snapshot.value = next;
      return next;
    },
  }),
}));
const state = (
  value: ScanOperationSnapshot["state"] = "queued",
  version = 1,
): ScanOperationSnapshot => ({
  id: "server-id",
  request_key: "request-one",
  job_id: "server-job",
  attempt_id: "attempt-one",
  state: value,
  version,
  intentional_cancel: value === "cancelled",
  dispatch_pending: false,
  created_at: "",
  updated_at: "",
  items: [],
});
const request = (): OperationRequest => ({
  operationId: "local-id",
  jobId: "local-job",
  idempotencyKey: "request-one",
  kind: "discovery",
  scope: { kind: "library" },
  profiles: [],
  uiLocale: "en_US",
  metadataLocale: "en_US",
  providerPolicy: {
    providers: ["steam"],
    fallbackProviders: [],
    allowUnexpectedLocale: false,
  },
  metadataPolicy: { mode: "missing-only", fields: [] },
  mediaPolicy: { mode: "none", targets: [] },
  capabilities: {
    discovery: true,
    creation: true,
    metadata: true,
    media: false,
    fileMutation: false,
    pcDlc: true,
    preview: true,
    retry: true,
    resume: true,
  },
  preview: false,
  permissions: { scopes: ["tasks:run"] },
  execution: { maxConcurrency: 1, cancelable: true, resumable: true },
});
describe("confirmed library operation facade", () => {
  const scopes: ReturnType<typeof effectScope>[] = [];
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    snapshot.value = null;
    fake.submit.mockResolvedValue(state());
  });
  afterEach(() => {
    scopes.splice(0).forEach((scope) => scope.stop());
    vi.useRealTimers();
  });
  async function owner() {
    const { useLibraryOperation } = await import("./useLibraryOperation");
    const scope = effectScope();
    scopes.push(scope);
    return scope.run(useLibraryOperation)!;
  }
  it("awaits acceptance and coalesces repeated clicks without optimistic running", async () => {
    let resolve: (value: ScanOperationSnapshot) => void = () => {};
    fake.submit.mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const operation = await owner();
    const first = operation.start(request());
    const second = operation.start(request());
    expect(operation.checking.value).toBe(true);
    expect(operation.status.value).not.toBe("running");
    expect(fake.submit).toHaveBeenCalledTimes(1);
    resolve(state("accepted"));
    await Promise.all([first, second]);
    expect(operation.status.value).toBe("accepted");
    expect(operation.result.value?.operationId).toBe("server-id");
  });
  it("reconciles lost acceptance by the same request key without another POST", async () => {
    fake.submit.mockRejectedValue(
      new axios.AxiosError("timeout", "ECONNABORTED"),
    );
    fake.byRequest.mockResolvedValue(state("queued"));
    const operation = await owner();
    await operation.start(request());
    expect(fake.submit).toHaveBeenCalledTimes(1);
    expect(fake.byRequest).toHaveBeenCalledWith("request-one");
    expect(operation.status.value).toBe("queued");
  });
  it("keeps uncertain identity and offers another GET after the bounded budget", async () => {
    fake.submit.mockRejectedValue(
      new axios.AxiosError("timeout", "ECONNABORTED"),
    );
    fake.byRequest.mockRejectedValue(new Error("not found"));
    const operation = await owner();
    const pending = operation.start(request());
    await flushPromises();
    await vi.advanceTimersByTimeAsync(32000);
    await pending;
    expect(operation.uncertain.value).toBe(true);
    expect(operation.actionError.value).toBe("acceptance-uncertain");
    fake.byRequest.mockResolvedValue(state("running"));
    await operation.retryStatus();
    expect(fake.submit).toHaveBeenCalledTimes(1);
    expect(operation.uncertain.value).toBe(false);
  });
  it("waits for cancellation acknowledgement and resumes only explicitly", async () => {
    const operation = await owner();
    await operation.start(request());
    let resolve: (value: ScanOperationSnapshot) => void = () => {};
    fake.cancel.mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const pending = operation.cancel();
    expect(operation.status.value).toBe("stopping");
    expect(fake.resume).not.toHaveBeenCalled();
    resolve(state("stopping", 2));
    await pending;
    expect(operation.status.value).toBe("stopping");
    snapshot.value = state("cancelled", 3);
    await flushPromises();
    fake.resume.mockResolvedValue(state("queued", 4));
    await operation.resume();
    expect(fake.resume).toHaveBeenCalledTimes(1);
  });
  it("retries selected warning rows only and disposal never cancels", async () => {
    const operation = await owner();
    const warning = {
      id: 7,
      target_key: "game",
      mapping_id: 1,
      expected_revision: 1,
      relative_path: "game",
      provider: "steam",
      outcome: "warning" as const,
      attempt_id: "attempt-one",
    };
    snapshot.value = { ...state("completed-with-warnings"), items: [warning] };
    await flushPromises();
    fake.retryMetadata.mockResolvedValue(state("queued", 2));
    await operation.retry(["7"]);
    expect(fake.retryMetadata).toHaveBeenCalledWith(
      expect.objectContaining({ id: "server-id" }),
      [7],
      expect.any(String),
    );
    operation.dispose();
    expect(fake.cancel).not.toHaveBeenCalled();
  });
  it("bounds concurrency and preserves order", async () => {
    const { runWithConcurrency, withRateLimitBackoff } =
      await import("./useLibraryOperation");
    let active = 0,
      peak = 0;
    expect(
      await runWithConcurrency(
        [1, 2, 3],
        async (value) => {
          active++;
          peak = Math.max(peak, active);
          await Promise.resolve();
          active--;
          return value * 2;
        },
        2,
      ),
    ).toEqual([2, 4, 6]);
    expect(peak).toBe(2);
    let calls = 0;
    expect(
      await withRateLimitBackoff(
        async () => {
          if (++calls < 2) throw { retryable: true };
          return "ok";
        },
        {
          maxAttempts: 2,
          baseDelayMs: 0,
          maxDelayMs: 0,
          sleep: async () => {},
        },
      ),
    ).toBe("ok");
  });
});
