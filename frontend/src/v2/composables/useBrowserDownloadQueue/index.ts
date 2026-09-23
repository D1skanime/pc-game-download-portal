import { createSHA256 } from "hash-wasm";
import { computed, ref } from "vue";
import type { DownloadManifestResponse } from "@/__generated__";
import api from "@/services/api";
import configApi from "@/services/api/config";
import downloadTransfersApi from "@/services/api/downloadTransfers";
import { validateDownloadDestination } from "@/v2/utils/downloadManifestPath";
import { getBrowserDownloadQueueConcurrency } from "./config";

/** A blocked FSA prompt/write must not hold the queue forever. */
export const ENHANCED_MEMBER_TIMEOUT_MS = 30_000;

/**
 * A member may take longer than the watchdog while it is actively streaming
 * or hashing. Only an uninterrupted idle interval is a failed transfer.
 */
export function createEnhancedInactivityTimeout(onTimeout: () => void) {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const refresh = () => {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
    timeoutId = setTimeout(onTimeout, ENHANCED_MEMBER_TIMEOUT_MS);
  };

  refresh();
  return {
    refresh,
    clear: () => {
      if (timeoutId !== undefined) clearTimeout(timeoutId);
      timeoutId = undefined;
    },
  };
}

type DirectoryPicker = (options?: {
  mode?: "readwrite";
}) => Promise<FileSystemDirectoryHandle>;
type EnhancedWindow = Window & { showDirectoryPicker?: DirectoryPicker };

export function getEnhancedDirectoryPicker(): DirectoryPicker | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as EnhancedWindow).showDirectoryPicker;
}

export function isEnhancedDownloadSupported(): boolean {
  return typeof getEnhancedDirectoryPicker() === "function";
}

export function validateEnhancedResponse(
  response: Response,
  offset: number,
  size: number,
): boolean {
  if (offset === 0) return response.status === 200;
  if (response.status !== 206) return false;
  return (
    response.headers.get("Content-Range") ===
    `bytes ${offset}-${size - 1}/${size}`
  );
}

export function getAttributedDownloadUrl(
  download: string,
  transferId: string,
  itemId: number,
): string {
  const separator = download.includes("?") ? "&" : "?";
  return `${download}${separator}transfer_id=${encodeURIComponent(transferId)}&item_id=${itemId}`;
}

function createHashWorker() {
  return new Worker(
    new URL("../../workers/downloadHash.worker.ts", import.meta.url),
    {
      type: "module",
    },
  );
}

type Sha256Hasher = Awaited<ReturnType<typeof createSHA256>>;

function createHasher() {
  let worker: Worker | null = null;
  let fallback: Sha256Hasher | null = null;
  try {
    worker = createHashWorker();
  } catch {
    // Some browser/build combinations reject module workers. Keep the
    // transfer usable with the same streaming WASM hasher on the main thread.
  }
  let id = 0;
  const send = (message: object, transfer?: Transferable[]) =>
    new Promise<any>((resolve, reject) => {
      if (!worker) {
        reject(new Error("hash_worker_unavailable"));
        return;
      }
      const currentWorker = worker;
      if (!currentWorker) {
        reject(new Error("hash_worker_unavailable"));
        return;
      }
      const requestId = ++id;
      const onMessage = (event: MessageEvent) => {
        if (event.data.id !== requestId) return;
        currentWorker.removeEventListener("message", onMessage);
        currentWorker.removeEventListener("error", onError);
        if (event.data.error) reject(new Error(event.data.error));
        else resolve(event.data);
      };
      const onError = (event: ErrorEvent) => {
        currentWorker.removeEventListener("message", onMessage);
        currentWorker.removeEventListener("error", onError);
        reject(event.error ?? new Error(event.message));
      };
      currentWorker.addEventListener("message", onMessage);
      currentWorker.addEventListener("error", onError);
      currentWorker.postMessage({ ...message, id: requestId }, transfer ?? []);
    });
  return {
    reset: async () => {
      if (worker) {
        try {
          await send({ type: "reset" });
          return;
        } catch {
          worker.terminate();
          worker = null;
        }
      }
      fallback = await createSHA256();
    },
    update: async (chunk: Uint8Array) => {
      const copy = chunk.slice();
      if (worker) {
        try {
          await send({ type: "update", chunk: copy.buffer }, [copy.buffer]);
          return;
        } catch {
          worker.terminate();
          worker = null;
          fallback = await createSHA256();
        }
      }
      fallback?.update(copy);
    },
    digest: async () => {
      if (worker) {
        try {
          return (await send({ type: "digest" })).digest as string;
        } catch {
          worker.terminate();
          worker = null;
          fallback = await createSHA256();
        }
      }
      if (!fallback) throw new Error("hash_unavailable");
      return fallback.digest();
    },
    terminate: () => worker?.terminate(),
  };
}

async function hashExisting(
  file: File,
  hasher: ReturnType<typeof createHasher>,
  onActivity: () => void = () => undefined,
) {
  await hasher.reset();
  const reader = file.stream().getReader();
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      await hasher.update(next.value);
      onActivity();
    }
  } finally {
    reader.releaseLock();
  }
}

async function permission(handle: FileSystemDirectoryHandle) {
  const permissionHandle = handle as FileSystemDirectoryHandle & {
    queryPermission: (descriptor?: {
      mode?: "readwrite";
    }) => Promise<PermissionState>;
    requestPermission: (descriptor?: {
      mode?: "readwrite";
    }) => Promise<PermissionState>;
  };
  const permissionState = await permissionHandle.queryPermission({
    mode: "readwrite",
  });
  return (
    permissionState === "granted" ||
    (permissionState === "prompt" &&
      (await permissionHandle.requestPermission({ mode: "readwrite" })) ===
        "granted")
  );
}

async function openDestination(
  root: FileSystemDirectoryHandle,
  destination: string,
  resume: boolean,
) {
  const segments = validateDownloadDestination(destination);
  if (!segments) throw new Error("unsafe_destination");
  let directory = root;
  for (const segment of segments.slice(0, -1)) {
    directory = await directory.getDirectoryHandle(segment, { create: true });
    if (!(await permission(directory))) throw new Error("permission_denied");
  }
  const filename = segments.at(-1)!;
  let file: FileSystemFileHandle;
  let existed = true;
  try {
    file = await directory.getFileHandle(filename, { create: false });
  } catch {
    existed = false;
    file = await directory.getFileHandle(filename, { create: true });
  }
  const existing = await file.getFile();
  // A zero-byte placeholder can be safely restarted. Non-empty files are
  // retained for validator-checked resume, while standard mode still refuses
  // accidental overwrites when resume is disabled.
  if (existed && !resume) throw new Error("destination_exists");
  return { file, existing };
}

async function enhancedMember(
  root: FileSystemDirectoryHandle,
  member: DownloadManifestResponse["members"][number],
  signal: AbortSignal,
  abortReason: () => "pause" | "cancel" | null,
  onProgress: (bytes: number) => void,
  onActivity: () => void,
) {
  const { file, existing } = await openDestination(
    root,
    member.destination,
    true,
  );
  const offset = existing.size;
  onProgress(offset);
  if (offset > member.size) throw new Error("local_file_too_large");
  const hasher = createHasher();
  let writable: FileSystemWritableFileStream | null = null;
  try {
    onActivity();
    await hasher.reset();
    if (offset) await hashExisting(existing, hasher, onActivity);
    if (offset === member.size) {
      const digest = await hasher.digest();
      if (digest.toLowerCase() !== member.sha256.toLowerCase()) {
        throw new Error("checksum_mismatch");
      }
      return;
    }
    const headers: Record<string, string> = { "If-Match": member.snapshot };
    if (offset > 0) headers.Range = `bytes=${offset}-`;
    const response = await fetch(member.download, {
      credentials: "same-origin",
      signal,
      headers,
    });
    if (!validateEnhancedResponse(response, offset, member.size)) {
      throw new Error(
        response.status === 412 ? "source_changed" : "invalid_resume_response",
      );
    }
    writable = await file.createWritable({
      keepExistingData: offset > 0,
    });
    onActivity();
    if (offset) await writable.seek(offset);
    if (!response.body) throw new Error("missing_response_body");
    const reader = response.body.getReader();
    let observed = offset;
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      if (signal.aborted) {
        throw new Error(abortReason() ?? "download_aborted");
      }
      await writable.write(next.value);
      observed += next.value.byteLength;
      onProgress(observed);
      await hasher.update(next.value);
      onActivity();
    }
    await writable.close();
    writable = null;
    if (signal.aborted) throw new Error(abortReason() ?? "download_aborted");
    if (observed !== member.size) throw new Error("size_mismatch");
    const digest = await hasher.digest();
    if (digest.toLowerCase() !== member.sha256.toLowerCase())
      throw new Error("checksum_mismatch");
  } finally {
    if (signal.aborted && writable !== null) {
      await writable.close();
      const persisted = await file.getFile();
      onProgress(persisted.size);
      writable = null;
    }
    hasher.terminate();
  }
}

export type BrowserQueueItem = DownloadManifestResponse["members"][number] & {
  observedBytes?: number;
  transferItemId?: number;
  status:
    | "queued"
    | "handed_to_browser"
    | "downloading"
    | "paused"
    | "verified"
    | "failed"
    | "cancelled";
};
export function useBrowserDownloadQueue() {
  const items = ref<BrowserQueueItem[]>([]);
  const sessionId = ref<string | null>(null);
  const starting = ref(false);
  const operations = new Map<
    string,
    {
      controller: AbortController;
      reason: "pause" | "cancel" | "timeout" | null;
    }
  >();
  let enhancedRoot: FileSystemDirectoryHandle | null = null;
  const queued = computed(() =>
    items.value.filter((item) => item.status === "queued"),
  );
  function hasActiveItems() {
    return items.value.some((item) =>
      ["queued", "downloading", "paused"].includes(item.status),
    );
  }
  function canStart() {
    if (starting.value || hasActiveItems()) return false;
    // A terminal previous attempt is history, not an active lock.
    if (sessionId.value) sessionId.value = null;
    return true;
  }
  async function pickEnhancedDirectory() {
    const picker = getEnhancedDirectoryPicker();
    if (!picker) return null;
    const root = await picker({ mode: "readwrite" });
    if (!(await permission(root))) return null;
    return root;
  }
  async function start(manifest: DownloadManifestResponse) {
    if (!canStart()) return false;
    starting.value = true;
    try {
      const config = await configApi.getBrowserDownloadQueueConfig();
      const limit = getBrowserDownloadQueueConcurrency(config.data);
      const session = await downloadTransfersApi.create({
        manifest_id: manifest.id,
        mode: "standard",
      });
      sessionId.value = session.data.id;
      items.value = manifest.members.map((member) => ({
        ...member,
        observedBytes: 0,
        transferItemId: session.data.items.find(
          (candidate) => candidate.manifest_member_id === member.file_id,
        )?.id,
        status: "queued" as const,
      }));
      for (let index = 0; index < items.value.length; index += limit) {
        await Promise.all(
          items.value.slice(index, index + limit).map(async (item) => {
            if (item.transferItemId === undefined) return;
            await downloadTransfersApi.observe(
              session.data.id,
              item.transferItemId,
              { event_type: "handoff" },
            );
            item.status = "handed_to_browser";
            const anchor = document.createElement("a");
            anchor.href = getAttributedDownloadUrl(
              item.download,
              session.data.id,
              item.transferItemId,
            );
            anchor.download = item.destination.split("/").pop() ?? "download";
            anchor.click();
          }),
        );
      }
      return true;
    } finally {
      starting.value = false;
    }
  }
  async function startEnhanced(
    manifest: DownloadManifestResponse,
    selectedRoot?: FileSystemDirectoryHandle | null,
  ) {
    if (!canStart()) return false;
    const root = selectedRoot ?? (await pickEnhancedDirectory());
    if (!root) return false;
    starting.value = true;
    try {
      const config = await configApi.getBrowserDownloadQueueConfig();
      const limit = getBrowserDownloadQueueConcurrency(config.data);
      const session = await downloadTransfersApi.create({
        manifest_id: manifest.id,
        mode: "enhanced",
      });
      sessionId.value = session.data.id;
      enhancedRoot = root;
      items.value = manifest.members.map((member) => ({
        ...member,
        observedBytes: 0,
        transferItemId: session.data.items.find(
          (candidate) => candidate.manifest_member_id === member.file_id,
        )?.id,
        status: "queued" as const,
      }));
      for (let index = 0; index < items.value.length; index += limit) {
        await Promise.all(
          items.value
            .slice(index, index + limit)
            .map((item) => runEnhancedItem(root, item, session.data.id)),
        );
      }
      return true;
    } finally {
      starting.value = false;
    }
  }
  async function runEnhancedItem(
    root: FileSystemDirectoryHandle,
    item: BrowserQueueItem,
    transferId: string,
  ) {
    if (item.transferItemId === undefined) return;
    const wasPaused = item.status === "paused";
    item.status = "downloading";
    const operation = { controller: new AbortController(), reason: null } as {
      controller: AbortController;
      reason: "pause" | "cancel" | "timeout" | null;
    };
    operations.set(item.file_id, operation);
    const timeout = createEnhancedInactivityTimeout(() => {
      operation.reason = "timeout";
      operation.controller.abort();
    });
    try {
      await downloadTransfersApi.observe(transferId, item.transferItemId, {
        event_type: wasPaused ? "resume" : "progress",
        observed_bytes: item.observedBytes ?? 0,
      });
      const attributedMember = {
        ...item,
        download: getAttributedDownloadUrl(
          item.download,
          transferId,
          item.transferItemId,
        ),
      };
      const transfer = enhancedMember(
        root,
        attributedMember,
        operation.controller.signal,
        () =>
          operation.reason === "pause" || operation.reason === "cancel"
            ? operation.reason
            : null,
        (bytes) => {
          item.observedBytes = bytes;
        },
        timeout.refresh,
      );
      await transfer;
      await downloadTransfersApi.observe(transferId, item.transferItemId, {
        event_type: "verified",
        observed_bytes: item.size,
        sha256: item.sha256,
      });
      item.status = "verified";
    } catch (error) {
      const reason = operation.reason;
      if (reason === "pause" || reason === "cancel") {
        await downloadTransfersApi.observe(transferId, item.transferItemId, {
          event_type: reason,
          observed_bytes: item.observedBytes ?? 0,
        });
        item.status = reason === "pause" ? "paused" : "cancelled";
      } else {
        const errorCode =
          error instanceof Error ? error.message : "enhanced_download_failed";
        console.error("[RomM] Enhanced download failed", {
          fileId: item.file_id,
          destination: item.destination,
          error: errorCode,
        });
        try {
          await downloadTransfersApi.observe(transferId, item.transferItemId, {
            event_type: "fail",
            error_code: errorCode.slice(0, 64),
            observed_bytes: item.observedBytes ?? 0,
          });
        } catch (observationError) {
          console.error("[RomM] Could not record enhanced download failure", {
            fileId: item.file_id,
            error:
              observationError instanceof Error
                ? observationError.message
                : "transfer_observation_failed",
          });
        }
        item.status = "failed";
      }
    } finally {
      timeout.clear();
      operations.delete(item.file_id);
    }
  }
  async function resume(fileId: string) {
    const item = items.value.find((candidate) => candidate.file_id === fileId);
    if (!item || item.status !== "paused" || !enhancedRoot || !sessionId.value)
      return false;
    await runEnhancedItem(enhancedRoot, item, sessionId.value);
    return (item.status as BrowserQueueItem["status"]) === "verified";
  }
  async function resumeSession(
    transferId: string,
    manifestMemberId?: string | null,
  ) {
    const root = await pickEnhancedDirectory();
    if (!root) return false;
    const previous = await downloadTransfersApi.get(transferId);
    if (previous.data.mode !== "enhanced") return false;
    const manifest = await api.get<DownloadManifestResponse>(
      `/download-manifests/${previous.data.manifest_id}`,
    );
    const config = await configApi.getBrowserDownloadQueueConfig();
    const limit = getBrowserDownloadQueueConcurrency(config.data);
    const session = await downloadTransfersApi.create({
      manifest_id: manifest.data.id,
      mode: "enhanced",
      ...(manifestMemberId ? { member_ids: [manifestMemberId] } : {}),
    });
    if (previous.data.status === "active") {
      await downloadTransfersApi.cancel(transferId);
    }
    enhancedRoot = root;
    sessionId.value = session.data.id;
    const members = manifest.data.members.filter(
      (member) => !manifestMemberId || member.file_id === manifestMemberId,
    );
    items.value = members.map((member) => {
      const persisted = session.data.items.find(
        (item) => item.manifest_member_id === member.file_id,
      );
      return {
        ...member,
        observedBytes: 0,
        transferItemId: persisted?.id,
        status: "queued" as const,
      };
    });
    const pending = items.value.filter((item) => item.status === "queued");
    for (let index = 0; index < pending.length; index += limit) {
      await Promise.all(
        pending
          .slice(index, index + limit)
          .map((item) => runEnhancedItem(root, item, session.data.id)),
      );
    }
    return true;
  }
  function pause(fileId: string) {
    const operation = operations.get(fileId);
    if (operation) {
      operation.reason = "pause";
      operation.controller.abort();
    }
  }
  function cancel(fileId: string) {
    const operation = operations.get(fileId);
    if (operation) {
      operation.reason = "cancel";
      operation.controller.abort();
    }
    const item = items.value.find((candidate) => candidate.file_id === fileId);
    if (item) item.status = "cancelled";
  }
  function clearTerminal(fileIds: string[]) {
    const fileIdSet = new Set(fileIds);
    items.value = items.value.filter((item) => !fileIdSet.has(item.file_id));
    if (items.value.length === 0) {
      sessionId.value = null;
      enhancedRoot = null;
    }
  }
  return {
    items,
    queued,
    sessionId,
    starting,
    start,
    pickEnhancedDirectory,
    startEnhanced,
    resume,
    resumeSession,
    pause,
    cancel,
    clearTerminal,
  };
}
export { getBrowserDownloadQueueConcurrency } from "./config";
