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
import storeScanning from "@/v2/data/adapters/legacy/stores/scanning";
import scanOperations from "@/v2/data/adapters/scanOperations";
import type { ScanOperationSnapshot } from "@/v2/data/contracts";

const snapshot = ref<ScanOperationSnapshot | null>(null);
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
  snapshot.value = next;
  const store = storeScanning();
  store.setScanning(activeStates.has(next.state));
  if (next.scan_stats) {
    const stats = next.scan_stats;
    store.setScanStats({
      total_platforms: stats.total_platforms ?? 0,
      total_roms: stats.total_roms ?? 0,
      scanned_platforms: stats.scanned_platforms ?? 0,
      new_platforms: stats.new_platforms ?? 0,
      identified_platforms: stats.identified_platforms ?? 0,
      scanned_roms: stats.scanned_roms ?? 0,
      new_roms: stats.new_roms ?? 0,
      identified_roms: stats.identified_roms ?? 0,
      scanned_firmware: stats.scanned_firmware ?? 0,
      new_firmware: stats.new_firmware ?? 0,
    });
  }
  errorCode.value = null;
  return next;
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
        clearTimer();
        flight = undefined;
        snapshot.value = null;
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
