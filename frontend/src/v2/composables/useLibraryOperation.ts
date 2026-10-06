import { ref, type Ref } from "vue";
import {
  observeScanLifecycle,
  type ScanLifecycleEvent,
} from "@/v2/composables/useScanLifecycle";
import {
  startLegacyScan,
  stopLegacyScan,
} from "@/v2/data/adapters/legacy/scan";
import storeScanning from "@/v2/data/adapters/legacy/stores/scanning";
import type {
  OperationDiagnostic,
  OperationItemResult,
  OperationRequest,
  OperationResult,
  OperationStatus,
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

function eventDiagnostic(
  request: OperationRequest,
  event: ScanLifecycleEvent,
): OperationDiagnostic | null {
  if (event.type !== "failed") return null;
  const retryable = /rate|timeout|temporar|busy|network/i.test(event.message);
  return {
    code: retryable ? "provider-failed" : "validation-failed",
    operationId: request.operationId,
    jobId: request.jobId,
    retryable,
    message: retryable
      ? "The operation can be retried."
      : "The operation failed validation or execution.",
  };
}

export function useLibraryOperation(): LibraryOperationState & {
  start(request: OperationRequest): Promise<OperationResult>;
  cancel(): void;
  resume(): Promise<OperationResult | null>;
  retry(itemIds?: readonly string[]): Promise<OperationResult | null>;
  dispose(): void;
} {
  const status = ref<OperationStatus>("queued");
  const request = ref<OperationRequest | null>(null);
  const result = ref<OperationResult | null>(null);
  const diagnostics = ref<OperationDiagnostic[]>([]);
  const scanningStore = storeScanning();
  const completedByIdempotency = new Map<string, OperationResult>();
  let disposed = false;

  const onLifecycle = (event: ScanLifecycleEvent): void => {
    const active = request.value;
    if (!active || disposed) return;
    if (event.type === "stats") return;
    if (event.type === "started") {
      status.value = "running";
      return;
    }
    if (event.type === "completed") {
      status.value = "completed";
      result.value = {
        operationId: active.operationId,
        jobId: active.jobId,
        status: "completed",
        items: itemResults(active, "changed"),
        preview: active.preview,
        diagnostics: diagnostics.value,
        impact: impact(active),
      };
      completedByIdempotency.set(active.idempotencyKey, result.value);
      return;
    }
    const diagnostic = eventDiagnostic(active, event);
    if (diagnostic) diagnostics.value = [...diagnostics.value, diagnostic];
    status.value = diagnostic?.retryable ? "retryable" : "failed";
    result.value = {
      operationId: active.operationId,
      jobId: active.jobId,
      status: status.value,
      items: itemResults(
        active,
        diagnostic?.retryable ? "retryable" : "failed",
      ),
      preview: active.preview,
      diagnostics: diagnostics.value,
      impact: impact(active),
    };
  };

  const removeObserver = observeScanLifecycle(onLifecycle);

  async function start(input: OperationRequest): Promise<OperationResult> {
    const normalized = normalizeOperationRequest(input);
    request.value = normalized;
    diagnostics.value = [];
    const existing = completedByIdempotency.get(normalized.idempotencyKey);
    if (existing) {
      result.value = existing;
      status.value = existing.status;
      return existing;
    }

    if (!normalized.permissions.scopes.includes("tasks:run")) {
      status.value = "permission-denied";
      const diagnostic: OperationDiagnostic = {
        code: "permission-denied",
        operationId: normalized.operationId,
        jobId: normalized.jobId,
        retryable: false,
        message: "The current user cannot run this operation.",
      };
      diagnostics.value = [diagnostic];
      const denied: OperationResult = {
        operationId: normalized.operationId,
        jobId: normalized.jobId,
        status: "permission-denied",
        items: itemResults(normalized, "skipped"),
        preview: normalized.preview,
        diagnostics: diagnostics.value,
        impact: impact(normalized),
      };
      result.value = denied;
      return denied;
    }

    status.value = "queued";
    scanningStore.reset();
    if (normalized.preview) {
      status.value = "completed";
      const previewResult: OperationResult = {
        operationId: normalized.operationId,
        jobId: normalized.jobId,
        status: "completed",
        items: itemResults(normalized, "unchanged"),
        preview: true,
        diagnostics: [
          {
            code: "preview",
            operationId: normalized.operationId,
            jobId: normalized.jobId,
            retryable: false,
            message: "Preview completed without changing library data.",
          },
        ],
        impact: impact(normalized),
      };
      result.value = previewResult;
      completedByIdempotency.set(normalized.idempotencyKey, previewResult);
      return previewResult;
    }

    scanningStore.setScanning(true);
    startLegacyScan(normalized);
    status.value = "running";
    return {
      operationId: normalized.operationId,
      jobId: normalized.jobId,
      status: "running",
      items: itemResults(normalized, "unchanged"),
      preview: false,
      diagnostics: diagnostics.value,
      impact: impact(normalized),
    };
  }

  function cancel(): void {
    if (
      !request.value ||
      (status.value !== "running" && status.value !== "queued")
    )
      return;
    status.value = "stopping";
    stopLegacyScan();
    scanningStore.setScanning(false);
    status.value = "cancelled";
    const active = request.value;
    result.value = {
      operationId: active.operationId,
      jobId: active.jobId,
      status: "cancelled",
      items: itemResults(active, "retryable"),
      preview: active.preview,
      diagnostics: [
        {
          code: "cancelled",
          operationId: active.operationId,
          jobId: active.jobId,
          retryable: true,
          message: "The operation was cancelled and can be resumed.",
        },
      ],
      impact: impact(active),
    };
  }

  async function resume(): Promise<OperationResult | null> {
    const active = request.value;
    if (!active || status.value !== "cancelled") return result.value;
    return start({
      ...active,
      idempotencyKey: active.idempotencyKey + ":resume",
      retry: {
        ...active.retry,
        resumeFrom: active.jobId,
        maxAttempts: active.retry?.maxAttempts ?? 1,
      },
    });
  }

  async function retry(
    itemIds?: readonly string[],
  ): Promise<OperationResult | null> {
    const active = request.value;
    if (!active || (status.value !== "retryable" && status.value !== "partial"))
      return result.value;
    return start({
      ...active,
      idempotencyKey: active.idempotencyKey + ":retry",
      retry: {
        ...active.retry,
        itemIds: itemIds ? [...itemIds] : active.retry?.itemIds,
        maxAttempts: active.retry?.maxAttempts ?? 1,
      },
    });
  }

  function dispose(): void {
    disposed = true;
    removeObserver();
  }

  return {
    status,
    request,
    result,
    diagnostics,
    start,
    cancel,
    resume,
    retry,
    dispose,
  };
}
