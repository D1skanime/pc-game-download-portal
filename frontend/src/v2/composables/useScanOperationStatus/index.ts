import axios from "axios";
import {
  computed,
  effectScope,
  getCurrentScope,
  onScopeDispose,
  ref,
  watch,
} from "vue";
import socket from "@/v2/data/adapters/legacy/services/socket";
import useAuthStore from "@/v2/data/adapters/legacy/stores/auth";
import storeScanning, {
  transportScanStats,
} from "@/v2/data/adapters/legacy/stores/scanning";
import scanOperations from "@/v2/data/adapters/scanOperations";
import type { ScanOperationSnapshot } from "@/v2/data/contracts";

const snapshot = ref<ScanOperationSnapshot | null>(null);
const nextOffset = ref(0);
const loadingMore = ref(false);
const hasMore = computed(
  () =>
    snapshot.value?.items_total !== undefined &&
    nextOffset.value < snapshot.value.items_total,
);
let pageFlight: Promise<ScanOperationSnapshot | null | undefined> | undefined;
const disconnected = ref(false);
const reconciling = ref(false);
const errorCode = ref<string | null>(null);
const activeStates = new Set([
  "accepted",
  "queued",
  "running",
  "stopping",
  "recovering",
]);
let owners = 0;
let epoch = 0;
let timer: ReturnType<typeof setTimeout> | undefined;
let flight: Promise<ScanOperationSnapshot | null> | undefined;
let stopOwner: (() => void) | undefined;
let backoff = 2000;
let refreshAgain = false;

function clearTimer() {
  if (timer) clearTimeout(timer);
  timer = undefined;
}

function accept(next: ScanOperationSnapshot) {
  const current = snapshot.value;
  if (current?.id === next.id) {
    if (next.version < current.version) return current;
    if (
      next.version === current.version &&
      (next.attempt_id !== current.attempt_id ||
        next.state !== current.state ||
        next.updated_at < current.updated_at)
    )
      return current;
  }
  const sameAttempt =
    current?.id === next.id && current.attempt_id === next.attempt_id;
  if (!sameAttempt) nextOffset.value = 0;
  const incoming = (next.items ?? []).filter(
    (item) => item.attempt_id === next.attempt_id,
  );
  const items = new Map<string, (typeof incoming)[number]>();
  for (const item of [
    ...(sameAttempt ? (current?.items ?? []) : []),
    ...incoming,
  ]) {
    const key = JSON.stringify([
      item.mapping_id,
      item.expected_revision,
      item.relative_path,
      item.target_key,
      item.inventory?.rom_id,
      item.provider,
    ]);
    items.set(key, item);
  }
  if (next.items !== undefined) {
    nextOffset.value = Math.max(
      nextOffset.value,
      (next.items_offset ?? 0) + next.items.length,
    );
  }
  snapshot.value = {
    ...next,
    items:
      next.items === undefined && !sameAttempt
        ? undefined
        : [...items.values()],
  };
  const store = storeScanning();
  store.setScanning(activeStates.has(next.state));
  projectStats(next.scan_stats);
  errorCode.value = null;
  return snapshot.value;
}

function projectStats(stats?: ScanOperationSnapshot["scan_stats"]) {
  const store = storeScanning();
  const projection = store.scanStats;
  for (const key of Object.keys(projection))
    Reflect.deleteProperty(projection, key);
  Object.assign(projection, transportScanStats(stats));
  store.setScanStats(projection);
}

function resetDetails() {
  nextOffset.value = 0;
  pageFlight = undefined;
  loadingMore.value = false;
  projectStats();
}

async function loadMore() {
  const current = snapshot.value;
  if (!owners || !current || !hasMore.value) return snapshot.value;
  if (pageFlight) return pageFlight;
  const generation = epoch;
  const offset = nextOffset.value;
  loadingMore.value = true;
  const task = (async () => {
    try {
      const next = await scanOperations.status(current.id, offset, 100);
      const latest = snapshot.value;
      if (
        generation !== epoch ||
        !owners ||
        latest?.id !== current.id ||
        latest.attempt_id !== current.attempt_id ||
        latest.version !== current.version ||
        latest.updated_at !== current.updated_at ||
        next.id !== current.id ||
        next.attempt_id !== current.attempt_id ||
        next.version !== current.version ||
        next.items_offset !== offset
      )
        return latest;
      return accept(next);
    } catch (error) {
      if (generation === epoch) {
        if (
          axios.isAxiosError(error) &&
          [401, 403].includes(error.response?.status ?? 0)
        ) {
          snapshot.value = null;
          resetDetails();
          storeScanning().setScanning(false);
          errorCode.value = "permission-denied";
        } else errorCode.value = "status-unavailable";
      }
      return snapshot.value;
    } finally {
      if (generation === epoch) {
        pageFlight = undefined;
        loadingMore.value = false;
      }
    }
  })();
  pageFlight = task;
  return task;
}

function schedule() {
  clearTimer();
  if (
    owners &&
    (activeStates.has(snapshot.value?.state ?? "") || errorCode.value)
  )
    timer = setTimeout(() => {
      void refresh();
    }, backoff);
}

async function refresh(): Promise<ScanOperationSnapshot | null> {
  if (!owners) return snapshot.value;
  if (flight) {
    refreshAgain = true;
    return flight;
  }
  clearTimer();
  const generation = epoch;
  const id = snapshot.value?.id;
  reconciling.value = true;
  const task = (async () => {
    try {
      let next: ScanOperationSnapshot | null;
      try {
        next = id
          ? await scanOperations.status(id)
          : await scanOperations.restore();
      } catch (error) {
        if (axios.isAxiosError(error) && error.response?.status === 404)
          next = await scanOperations.active();
        else throw error;
      }
      if (generation !== epoch || !owners || snapshot.value?.id !== id)
        return snapshot.value;
      if (next) accept(next);
      else {
        snapshot.value = null;
        resetDetails();
        storeScanning().setScanning(false);
      }
      disconnected.value = false;
      backoff = 2000;
      errorCode.value = null;
      return next;
    } catch (error) {
      if (generation !== epoch) return null;
      if (
        axios.isAxiosError(error) &&
        [401, 403].includes(error.response?.status ?? 0)
      ) {
        snapshot.value = null;
        resetDetails();
        storeScanning().setScanning(false);
        errorCode.value = "permission-denied";
      } else {
        disconnected.value = true;
        errorCode.value = "status-unavailable";
        backoff = Math.min(10000, backoff * 2);
      }
      return snapshot.value;
    } finally {
      if (generation === epoch) {
        flight = undefined;
        reconciling.value = false;
        if (refreshAgain) {
          refreshAgain = false;
          queueMicrotask(() => {
            void refresh();
          });
        } else schedule();
      }
    }
  })();
  flight = task;
  return task;
}

function install() {
  const auth = useAuthStore();
  const scope = effectScope(true);
  const reconnect = () => {
    disconnected.value = false;
    void refresh();
  };
  const disconnect = () => {
    disconnected.value = true;
  };
  const invalidate = () => {
    void refresh();
  };
  socket.on("connect", reconnect);
  socket.on("disconnect", disconnect);
  socket.on("scan:operation", invalidate);
  scope.run(() =>
    watch(
      () => auth.user?.id,
      () => {
        epoch += 1;
        refreshAgain = false;
        clearTimer();
        flight = undefined;
        snapshot.value = null;
        resetDetails();
        errorCode.value = null;
        reconciling.value = false;
        storeScanning().setScanning(false);
        if (auth.user) void refresh();
      },
      { flush: "sync" },
    ),
  );
  stopOwner = () => {
    scope.stop();
    socket.off("connect", reconnect);
    socket.off("disconnect", disconnect);
    socket.off("scan:operation", invalidate);
    epoch += 1;
    flight = undefined;
    refreshAgain = false;
    clearTimer();
    reconciling.value = false;
    snapshot.value = null;
    resetDetails();
    errorCode.value = null;
    disconnected.value = false;
  };
  if (auth.user) void refresh();
}

export function useScanOperationStatus() {
  owners += 1;
  if (owners === 1) install();
  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    owners -= 1;
    if (!owners) stopOwner?.();
  };
  if (getCurrentScope()) onScopeDispose(dispose);
  return {
    snapshot,
    hasMore,
    loadingMore,
    loadMore,
    disconnected,
    reconciling,
    errorCode,
    active: computed(() => activeStates.has(snapshot.value?.state ?? "")),
    refresh,
    accept(next: ScanOperationSnapshot) {
      const accepted = accept(next);
      schedule();
      return accepted;
    },
    dispose,
  };
}
