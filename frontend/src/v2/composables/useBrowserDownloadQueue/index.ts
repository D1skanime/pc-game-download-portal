import { computed, ref } from "vue";
import type { DownloadManifestResponse } from "@/__generated__";
import configApi from "@/services/api/config";
import downloadTransfersApi from "@/services/api/downloadTransfers";
import { validateDownloadDestination } from "@/v2/utils/downloadManifestPath";
import { getBrowserDownloadQueueConcurrency } from "./config";

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

function createHashWorker() {
  return new Worker(
    new URL("../../workers/downloadHash.worker.ts", import.meta.url),
    {
      type: "module",
    },
  );
}

function createHasher(worker: Worker) {
  let id = 0;
  const send = (message: object, transfer?: Transferable[]) =>
    new Promise<any>((resolve, reject) => {
      const requestId = ++id;
      const onMessage = (event: MessageEvent) => {
        if (event.data.id !== requestId) return;
        worker.removeEventListener("message", onMessage);
        worker.removeEventListener("error", onError);
        if (event.data.error) reject(new Error(event.data.error));
        else resolve(event.data);
      };
      const onError = (event: ErrorEvent) => {
        worker.removeEventListener("message", onMessage);
        worker.removeEventListener("error", onError);
        reject(event.error ?? new Error(event.message));
      };
      worker.addEventListener("message", onMessage);
      worker.addEventListener("error", onError);
      worker.postMessage({ ...message, id: requestId }, transfer ?? []);
    });
  return {
    reset: () => send({ type: "reset" }),
    update: (chunk: Uint8Array) => {
      const copy = chunk.slice();
      return send({ type: "update", chunk: copy.buffer }, [copy.buffer]);
    },
    digest: async () => (await send({ type: "digest" })).digest as string,
  };
}

async function hashExisting(
  file: File,
  hasher: ReturnType<typeof createHasher>,
) {
  await hasher.reset();
  const reader = file.stream().getReader();
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      await hasher.update(next.value);
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
  if (existed && (!resume || existing.size === 0))
    throw new Error("destination_exists");
  return { file, existing };
}

async function enhancedMember(
  root: FileSystemDirectoryHandle,
  member: DownloadManifestResponse["members"][number],
  signal: AbortSignal,
) {
  const { file, existing } = await openDestination(
    root,
    member.destination,
    true,
  );
  const offset = existing.size;
  if (offset > member.size) throw new Error("local_file_too_large");
  const worker = createHashWorker();
  try {
    const hasher = createHasher(worker);
    await hasher.reset();
    if (offset) await hashExisting(existing, hasher);
    if (offset === member.size) {
      const digest = await hasher.digest();
      if (digest.toLowerCase() !== member.sha256.toLowerCase()) {
        throw new Error("checksum_mismatch");
      }
      return;
    }
    const headers: Record<string, string> = { "If-Match": member.snapshot };
    if (offset > 0) headers.Range = `bytes=${offset}-`;
    const response = await fetch(member.download, { signal, headers });
    if (!validateEnhancedResponse(response, offset, member.size)) {
      throw new Error(
        response.status === 412 ? "source_changed" : "invalid_resume_response",
      );
    }
    const writable = await file.createWritable({
      keepExistingData: offset > 0,
    });
    if (offset) await writable.seek(offset);
    if (!response.body) throw new Error("missing_response_body");
    const reader = response.body.getReader();
    let observed = offset;
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      await writable.write(next.value);
      observed += next.value.byteLength;
      await hasher.update(next.value);
    }
    await writable.close();
    if (observed !== member.size) throw new Error("size_mismatch");
    const digest = await hasher.digest();
    if (digest.toLowerCase() !== member.sha256.toLowerCase())
      throw new Error("checksum_mismatch");
  } finally {
    worker.terminate();
  }
}

export type BrowserQueueItem = DownloadManifestResponse["members"][number] & {
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
  const controllers = new Map<string, AbortController>();
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
        status: "queued" as const,
      }));
      for (let index = 0; index < items.value.length; index += limit) {
        await Promise.all(
          items.value.slice(index, index + limit).map(async (item) => {
            const anchor = document.createElement("a");
            anchor.href = item.download;
            anchor.download = item.destination.split("/").pop() ?? "download";
            anchor.click();
            item.status = "handed_to_browser";
            const transferItem = session.data.items.find(
              (candidate) => candidate.manifest_member_id === item.file_id,
            );
            if (transferItem)
              await downloadTransfersApi.observe(
                session.data.id,
                transferItem.id,
                { event_type: "handoff" },
              );
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
      items.value = manifest.members.map((member) => ({
        ...member,
        status: "queued" as const,
      }));
      for (let index = 0; index < items.value.length; index += limit) {
        await Promise.all(
          items.value.slice(index, index + limit).map(async (item) => {
            item.status = "downloading";
            const controller = new AbortController();
            controllers.set(item.file_id, controller);
            try {
              await enhancedMember(root, item, controller.signal);
              item.status = "verified";
            } catch (error) {
              item.status = controller.signal.aborted ? "paused" : "failed";
            } finally {
              controllers.delete(item.file_id);
            }
          }),
        );
      }
      return true;
    } finally {
      starting.value = false;
    }
  }
  function pause(fileId: string) {
    controllers.get(fileId)?.abort();
  }
  function cancel(fileId: string) {
    controllers.get(fileId)?.abort();
    const item = items.value.find((candidate) => candidate.file_id === fileId);
    if (item) item.status = "cancelled";
  }
  return {
    items,
    queued,
    sessionId,
    starting,
    start,
    pickEnhancedDirectory,
    startEnhanced,
    pause,
    cancel,
  };
}
export { getBrowserDownloadQueueConcurrency } from "./config";
