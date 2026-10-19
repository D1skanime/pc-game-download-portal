import axios from "axios";
import {
  computed,
  getCurrentScope,
  onScopeDispose,
  ref,
  watch,
  type Ref,
} from "vue";
import { useScanOperationStatus } from "@/v2/composables/useScanOperationStatus";
import scanOperations from "@/v2/data/adapters/scanOperations";
import type {
  OperationDiagnostic,
  OperationItemResult,
  OperationRequest,
  OperationResult,
  OperationStatus,
  ScanOperationSnapshot,
} from "@/v2/data/contracts";
import {
  normalizeOperationRequest,
  operationItemIds,
} from "@/v2/data/operations";

export interface LibraryOperationState {
  status: Ref<OperationStatus>;
  request: Ref<OperationRequest | null>;
  result: Ref<OperationResult | null>;
  diagnostics: Ref<OperationDiagnostic[]>;
}

export interface RetryPolicy {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
  sleep?: (delayMs: number) => Promise<void>;
}

export interface RetryableFailure {
  retryable: boolean;
  retryAfterMs?: number;
  status?: number;
}

export async function withRateLimitBackoff<T>(
  work: (attempt: number) => Promise<T>,
  policy: RetryPolicy,
  isRetryable: (error: unknown) => boolean = (error) =>
    Boolean((error as RetryableFailure).retryable),
): Promise<T> {
  const sleep =
    policy.sleep ??
    ((delayMs) => new Promise((resolve) => setTimeout(resolve, delayMs)));
  let attempt = 0;
  while (true) {
    try {
      return await work(attempt);
    } catch (error) {
      attempt += 1;
      if (attempt >= Math.max(1, policy.maxAttempts) || !isRetryable(error))
        throw error;
      const retryAfterMs = (error as RetryableFailure).retryAfterMs;
      const delay =
        retryAfterMs ??
        Math.min(policy.maxDelayMs, policy.baseDelayMs * 2 ** (attempt - 1));
      await sleep(Math.max(0, delay));
    }
  }
}

export async function runWithConcurrency<T, R>(
  items: readonly T[],
  worker: (item: T, index: number) => Promise<R>,
  maxConcurrency: number,
  signal?: AbortSignal,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let nextIndex = 0;
  const concurrency = Math.max(1, Math.min(16, Math.floor(maxConcurrency)));
  const run = async (): Promise<void> => {
    while (true) {
      if (signal?.aborted)
        throw new DOMException("Operation cancelled", "AbortError");
      const index = nextIndex++;
      if (index >= items.length) return;
      results[index] = await worker(items[index], index);
    }
  };
  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, run),
  );
  return results;
}

function itemResults(
  request: OperationRequest,
  outcome: OperationItemResult["outcome"],
): OperationItemResult[] {
  return (request.retry?.itemIds ?? operationItemIds(request)).map(
    (itemId) => ({
      itemId,
      outcome,
      operationId: request.operationId,
      jobId: request.jobId,
      attempt: 1,
    }),
  );
}

function impact(request: OperationRequest): OperationResult["impact"] {
  return {
    scope: request.scope.kind,
    providers: [
      ...request.providerPolicy.providers,
      ...request.providerPolicy.fallbackProviders,
    ],
    metadataMode: request.metadataPolicy.mode,
    mediaMode: request.mediaPolicy.mode,
  };
}

export function useLibraryOperation() {
  const server = useScanOperationStatus();
  const request = ref<OperationRequest | null>(null);
  const result = ref<OperationResult | null>(null);
  const diagnostics = ref<OperationDiagnostic[]>([]);
  const checking = ref(false);
  const uncertain = ref(false);
  const localError = ref<string | null>(null);
  const actionError = computed(
    () => localError.value ?? server.errorCode.value,
  );
  const pendingStop = ref(false);
  const mutating = ref(false);
  const status = computed<OperationStatus>(() =>
    pendingStop.value
      ? "stopping"
      : (server.snapshot.value?.state ?? result.value?.status ?? "queued"),
  );
  const holdsSlot = computed(
    () =>
      server.active.value ||
      ["blocked", "interrupted"].includes(server.snapshot.value?.state ?? ""),
  );
  const busy = computed(
    () =>
      checking.value ||
      uncertain.value ||
      server.reconciling.value ||
      holdsSlot.value ||
      mutating.value,
  );
  let alive = true;
  let startFlight: Promise<OperationResult> | undefined;
  let reconciliationTimer: ReturnType<typeof setTimeout> | undefined;
  let releaseWait: (() => void) | undefined;
  let mutationKey: string | undefined;

  function project(next: ScanOperationSnapshot): OperationResult {
    const projected: OperationResult = {
      confirmed: next,
      operationId: next.id,
      jobId: next.job_id,
      status: next.state,
      items: (next.items ?? []).map((item) => ({
        itemId: String(item.id),
        outcome:
          item.outcome === "indexed" || item.outcome === "completed"
            ? "changed"
            : item.outcome === "warning" || item.outcome === "failed"
              ? "retryable"
              : "skipped",
        operationId: next.id,
        jobId: next.job_id,
      })),
      preview: false,
    };
    result.value = projected;
    if (!["accepted", "queued", "running", "recovering"].includes(next.state))
      pendingStop.value = false;
    return projected;
  }
  const unwatch = watch(
    server.snapshot,
    (next) => {
      if (next) project(next);
      else {
        result.value = null;
        pendingStop.value = false;
      }
    },
    { immediate: true },
  );
  function failed(code: string): OperationResult {
    localError.value = code;
    const active = request.value;
    const failure: OperationResult = {
      operationId: active?.operationId ?? "",
      jobId: active?.jobId ?? "",
      status: code === "permission-denied" ? "permission-denied" : "failed",
      items: [],
      preview: false,
    };
    result.value = failure;
    return failure;
  }
  function pause() {
    return new Promise<void>((resolve) => {
      releaseWait = resolve;
      reconciliationTimer = setTimeout(() => {
        releaseWait = undefined;
        resolve();
      }, 2000);
    });
  }
  async function reconcile(): Promise<OperationResult> {
    const key = request.value?.idempotencyKey;
    if (!key) return failed("start-failed");
    const deadline = Date.now() + 30000;
    uncertain.value = true;
    while (alive && Date.now() < deadline) {
      try {
        const next = await scanOperations.byRequest(key);
        if (!alive) break;
        uncertain.value = false;
        localError.value = null;
        return project(server.accept(next));
      } catch (error) {
        if (
          axios.isAxiosError(error) &&
          [401, 403].includes(error.response?.status ?? 0)
        ) {
          uncertain.value = false;
          return failed("permission-denied");
        }
      }
      await pause();
    }
    return failed("acceptance-uncertain");
  }

  function start(input: OperationRequest): Promise<OperationResult> {
    if (startFlight) return startFlight;
    if (uncertain.value) return retryStatus();
    if (holdsSlot.value)
      return Promise.resolve(project(server.snapshot.value!));
    const normalized = normalizeOperationRequest(input);
    request.value = normalized;
    localError.value = null;
    diagnostics.value = [];
    checking.value = true;
    const run = async () => {
      if (!normalized.permissions.scopes.includes("tasks:run"))
        return failed("permission-denied");
      if (normalized.preview) {
        const preview: OperationResult = {
          operationId: normalized.operationId,
          jobId: normalized.jobId,
          status: "completed",
          items: itemResults(normalized, "unchanged"),
          preview: true,
          impact: impact(normalized),
        };
        result.value = preview;
        return preview;
      }
      try {
        const next = await scanOperations.submit(normalized);
        if (!alive) return result.value ?? failed("start-failed");
        return project(server.accept(next));
      } catch (error) {
        if (
          axios.isAxiosError(error) &&
          (!error.response || error.response.status >= 500)
        )
          return reconcile();
        return failed(
          axios.isAxiosError(error) &&
            [401, 403].includes(error.response?.status ?? 0)
            ? "permission-denied"
            : "start-failed",
        );
      }
    };
    startFlight = run().finally(() => {
      checking.value = false;
      startFlight = undefined;
    });
    return startFlight;
  }
  async function retryStatus(): Promise<OperationResult> {
    if (!uncertain.value) {
      const next = await server.refresh();
      return next
        ? project(next)
        : (result.value ?? failed("status-unavailable"));
    }
    if (checking.value && startFlight) return startFlight;
    checking.value = true;
    try {
      return await reconcile();
    } finally {
      checking.value = false;
    }
  }
  async function mutate(
    kind: "cancel" | "resume" | "retry",
    itemIds: readonly string[] = [],
  ) {
    const current = server.snapshot.value;
    if (!current || mutating.value) return result.value;
    if (
      kind === "resume" &&
      current.state !== "cancelled" &&
      current.state !== "interrupted"
    )
      return result.value;
    const selected = itemIds.map(Number);
    const failedIds = new Set(
      (current.items ?? [])
        .filter(
          (item) => item.outcome === "warning" || item.outcome === "failed",
        )
        .map((item) => item.id),
    );
    if (
      kind === "retry" &&
      (!selected.length || selected.some((id) => !failedIds.has(id)))
    )
      return failed("select-failed-items");
    mutating.value = true;
    mutationKey ??= crypto.randomUUID();
    if (kind === "cancel") pendingStop.value = true;
    localError.value = null;
    try {
      const next =
        kind === "cancel"
          ? await scanOperations.cancel(current, mutationKey)
          : kind === "resume"
            ? await scanOperations.resume(current, mutationKey)
            : await scanOperations.retryMetadata(
                current,
                selected,
                mutationKey,
              );
      if (!alive) return result.value;
      mutationKey = undefined;
      return project(server.accept(next));
    } catch {
      localError.value = "status-unavailable";
      await server.refresh();
      return result.value;
    } finally {
      mutating.value = false;
    }
  }
  function dispose() {
    if (!alive) return;
    alive = false;
    unwatch();
    if (reconciliationTimer) clearTimeout(reconciliationTimer);
    releaseWait?.();
    server.dispose();
  }
  if (getCurrentScope()) onScopeDispose(dispose);
  return {
    status,
    request,
    result,
    diagnostics,
    checking,
    uncertain,
    busy,
    actionError,
    snapshot: server.snapshot,
    disconnected: server.disconnected,
    reconciling: server.reconciling,
    start,
    cancel: () => mutate("cancel"),
    resume: () => mutate("resume"),
    retry: (ids?: readonly string[]) => mutate("retry", ids),
    retryStatus,
    dispose,
  };
}
