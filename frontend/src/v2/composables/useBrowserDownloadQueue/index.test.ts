import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DownloadManifestResponse } from "@/__generated__";
import {
  getEnhancedDirectoryPicker,
  getAttributedDownloadUrl,
  isEnhancedDownloadSupported,
  createEnhancedInactivityTimeout,
  useBrowserDownloadQueue,
  validateEnhancedResponse,
} from ".";

const {
  getConfig,
  createSession,
  observe,
  getSession,
  cancelSession,
  getManifest,
} = vi.hoisted(() => ({
  getConfig: vi.fn(),
  createSession: vi.fn(),
  observe: vi.fn(),
  getSession: vi.fn(),
  cancelSession: vi.fn(),
  getManifest: vi.fn(),
}));

vi.mock("@/services/api", () => ({ default: { get: getManifest } }));
vi.mock("@/services/api/config", () => ({
  default: { getBrowserDownloadQueueConfig: getConfig },
}));
vi.mock("@/services/api/downloadTransfers", () => ({
  default: {
    create: createSession,
    observe,
    get: getSession,
    cancel: cancelSession,
  },
}));

const manifest = {
  id: "manifest-a",
  created_at: "2026-09-18T08:00:00Z",
  expires_at: "2026-09-19T08:00:00Z",
  components: [],
  members: ["a", "b", "c"].map((fileId) => ({
    file_id: fileId,
    destination: `files/${fileId}.bin`,
    size: 1,
    sha256: "a".repeat(64),
    snapshot: "snapshot",
    download: `https://example.invalid/${fileId}`,
  })),
} satisfies DownloadManifestResponse;

describe("enhanced browser download protocol", () => {
  it("times out only after an uninterrupted period without activity", () => {
    vi.useFakeTimers();
    const onTimeout = vi.fn();
    const timeout = createEnhancedInactivityTimeout(onTimeout);

    vi.advanceTimersByTime(29_999);
    timeout.refresh();
    vi.advanceTimersByTime(29_999);
    expect(onTimeout).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(onTimeout).toHaveBeenCalledTimes(1);

    timeout.clear();
    vi.useRealTimers();
  });

  it("binds member URLs to the owning transfer item", () => {
    expect(
      getAttributedDownloadUrl("/download?existing=true", "session/a", 7),
    ).toBe("/download?existing=true&transfer_id=session%2Fa&item_id=7");
  });

  it("is capability detected instead of user-agent detected", () => {
    expect(isEnhancedDownloadSupported()).toBe(
      typeof window !== "undefined" &&
        typeof (window as Window & { showDirectoryPicker?: unknown })
          .showDirectoryPicker === "function",
    );
    expect(getEnhancedDirectoryPicker()).toBeTypeOf("undefined");
  });

  it("requires exact 206 content range for resumed responses", () => {
    expect(
      validateEnhancedResponse(
        new Response("bytes", {
          status: 206,
          headers: { "Content-Range": "bytes 4-8/9" },
        }),
        4,
        9,
      ),
    ).toBe(true);
    expect(
      validateEnhancedResponse(
        new Response("bytes", {
          status: 200,
          headers: { "Content-Length": "5" },
        }),
        4,
        9,
      ),
    ).toBe(false);
  });
});

describe("useBrowserDownloadQueue standard mode", () => {
  beforeEach(() => {
    getConfig.mockReset();
    createSession.mockReset();
    observe.mockReset();
    getSession.mockReset();
    cancelSession.mockReset();
    getManifest.mockReset();
    getConfig.mockResolvedValue({
      data: { browser_download_queue_concurrency: 2 },
    });
    createSession.mockResolvedValue({
      data: {
        id: "session-a",
        items: [
          { id: 1, manifest_member_id: "a" },
          { id: 2, manifest_member_id: "b" },
          { id: 3, manifest_member_id: "c" },
        ],
      },
    });
    observe.mockResolvedValue({ data: {} });
  });

  it("hands off every member in controlled concurrency batches", async () => {
    const hrefs: string[] = [];
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        hrefs.push(this.href);
      });

    const queue = useBrowserDownloadQueue();
    await expect(queue.start(manifest)).resolves.toBe(true);

    expect(click).toHaveBeenCalledTimes(3);
    expect(queue.items.value.map((item) => item.status)).toEqual([
      "handed_to_browser",
      "handed_to_browser",
      "handed_to_browser",
    ]);
    expect(hrefs[0]).toContain("transfer_id=session-a");
    expect(observe).toHaveBeenCalledTimes(3);
    click.mockRestore();
  });

  it("forgets a completed session when its final local row is cleared", () => {
    const queue = useBrowserDownloadQueue();
    queue.sessionId.value = "completed-session";
    queue.items.value = [
      {
        ...manifest.members[0],
        status: "verified",
      },
    ];

    queue.clearTerminal(["a"]);

    expect(queue.items.value).toEqual([]);
    expect(queue.sessionId.value).toBeNull();
  });

  it("keeps the previous session untouched when its manifest has expired", async () => {
    const picker = vi.fn().mockResolvedValue({
      queryPermission: vi.fn().mockResolvedValue("granted"),
      requestPermission: vi.fn(),
    });
    Object.assign(window, { showDirectoryPicker: picker });
    getSession.mockResolvedValue({
      data: { mode: "enhanced", status: "active" },
    });
    getManifest.mockRejectedValue(new Error("manifest_expired"));

    const queue = useBrowserDownloadQueue();

    await expect(
      queue.resumeSession("previous-session", "member-a"),
    ).rejects.toThrow("manifest_expired");
    expect(cancelSession).not.toHaveBeenCalled();

    delete (window as Window & { showDirectoryPicker?: unknown })
      .showDirectoryPicker;
  });
});
