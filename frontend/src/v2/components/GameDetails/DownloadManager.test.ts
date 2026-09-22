import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DownloadManager from "./DownloadManager.vue";

const { list, get, removeAll } = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  removeAll: vi.fn(),
}));

vi.mock("@/services/api/downloadTransfers", () => ({
  default: { list, get, removeAll },
}));

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

const transfer = (
  id: string,
  romId: number,
  itemStatus = "handed_to_browser",
) => ({
  schema_version: 1,
  id,
  manifest_id: "manifest-a",
  rom_id: romId,
  mode: "standard",
  status: "active",
  selected_items: 1,
  selected_bytes: 1024,
  observed_bytes: 0,
  started_at: "2026-09-18T08:00:00Z",
  last_activity_at: "2026-09-18T08:01:00Z",
  ended_at: null,
  items: [
    {
      id: 42,
      manifest_member_id: "member-a",
      expected_bytes: 1024,
      observed_bytes: 0,
      status: itemStatus,
      started_at: null,
      last_activity_at: null,
      ended_at: null,
    },
  ],
  events: [],
});

describe("DownloadManager", () => {
  beforeEach(() => {
    list.mockReset();
    get.mockReset();
    removeAll.mockReset();
    list.mockResolvedValue({ data: [] });
    get.mockResolvedValue({ data: transfer("session-a", 7) });
    removeAll.mockResolvedValue({});
  });

  it("does not offer enhanced mode when directory access is unavailable", () => {
    const wrapper = mount(DownloadManager, {
      props: { romId: 7, items: [] },
    });
    expect(wrapper.text()).not.toContain("Enhanced folder download");
  });

  it("hydrates ROM history and the current manifest session through typed filters", async () => {
    const wrapper = mount(DownloadManager, {
      props: {
        romId: 7,
        selectedManifestId: "manifest-a",
        sessionId: "session-a",
        items: [],
      },
    });

    await vi.waitFor(() => expect(list).toHaveBeenCalled());
    expect(list).toHaveBeenCalledWith({ romId: 7, manifestId: "manifest-a" });
    expect(get).toHaveBeenCalledWith("session-a");
    await wrapper.setProps({ selectedManifestId: "manifest-b" });
    await vi.waitFor(() =>
      expect(list).toHaveBeenLastCalledWith({
        romId: 7,
        manifestId: "manifest-b",
      }),
    );
  });

  it("ignores a response for the previous ROM after selection changes", async () => {
    let resolveFirst!: (value: { data: unknown[] }) => void;
    let resolveSecond!: (value: { data: unknown[] }) => void;
    list
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockReturnValueOnce(new Promise((resolve) => (resolveSecond = resolve)));
    const wrapper = mount(DownloadManager, { props: { romId: 7, items: [] } });
    await wrapper.setProps({ romId: 8 });
    resolveFirst({ data: [transfer("old-session", 7, "handed_to_browser")] });
    resolveSecond({ data: [transfer("new-session", 8, "served")] });
    await vi.waitFor(() => expect(list).toHaveBeenCalledTimes(2));
    expect(wrapper.text()).not.toContain("rom.download-served");
    expect(wrapper.text()).not.toContain("rom.download-handed-to-browser");
    wrapper.unmount();
  });

  it("clears completed local rows after the server history is removed", async () => {
    const completed = transfer("completed-session", 7, "verified");
    completed.status = "completed";
    list.mockResolvedValue({ data: [completed] });
    const wrapper = mount(DownloadManager, {
      props: {
        romId: 7,
        items: [
          {
            file_id: "member-a",
            destination: "game/file.zip",
            size: 1024,
            sha256: "a".repeat(64),
            snapshot: "snapshot",
            download: "https://example.invalid/download",
            status: "verified",
          },
        ],
      },
    });

    await vi.waitFor(() =>
      expect(
        wrapper
          .findAll("button")
          .some((button) => button.text() === "rom.download-remove-all"),
      ).toBe(true),
    );
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "rom.download-remove-all")
      ?.trigger("click");

    await vi.waitFor(() =>
      expect(removeAll).toHaveBeenCalledWith({ romId: 7 }),
    );
    expect(wrapper.emitted("clear-terminal")).toEqual([[["member-a"]]]);
  });
});
