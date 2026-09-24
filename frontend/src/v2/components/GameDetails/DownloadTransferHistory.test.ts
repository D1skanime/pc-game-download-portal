import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { DownloadTransferResponse } from "@/__generated__";
import DownloadTransferHistory from "./DownloadTransferHistory.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) =>
      ({
        "rom.download-cancelled": "Cancelled",
        "rom.download-expired": "Expired",
        "rom.download-failed": "Download failed",
        "rom.download-handed-to-browser": "Handed to browser",
        "rom.download-queued": "Queued",
        "rom.download-served": "Served by RomM",
        "rom.download-stale": "Source changed. Prepare the download again.",
        "rom.download-verified": "Verified",
        "rom.download-cancel": "Cancel download",
        "rom.download-remove-entry": "Delete download entry",
        "rom.download-resume": "Resume download",
      })[key] ?? key,
  }),
}));

const session = (status: string): DownloadTransferResponse => ({
  schema_version: 1,
  id: `opaque-${status}`,
  manifest_id: "manifest-a",
  rom_id: 7,
  mode: status === "verified" ? "enhanced" : "standard",
  status: "active",
  selected_items: 1,
  selected_bytes: 1024,
  observed_bytes: status === "served" ? 1024 : 0,
  started_at: "2026-09-18T08:00:00Z",
  last_activity_at: "2026-09-18T08:01:00Z",
  ended_at: null,
  items: [
    {
      id: 42,
      manifest_member_id: `member-${status}`,
      destination: `game/${status}.bin`,
      expected_bytes: 1024,
      observed_bytes: status === "served" ? 1024 : 0,
      status,
      started_at: "2026-09-18T08:00:00Z",
      last_activity_at: "2026-09-18T08:01:00Z",
      ended_at: null,
    },
  ],
  events: [],
});

describe("DownloadTransferHistory", () => {
  it("maps every persisted outcome to truthful localized text", () => {
    const wrapper = mount(DownloadTransferHistory, {
      props: {
        sessions: [
          session("handed_to_browser"),
          session("served"),
          session("verified"),
          session("stale"),
          session("cancelled"),
          session("expired"),
          session("failed"),
        ],
      },
    });

    expect(wrapper.text()).toContain("Handed to browser");
    expect(wrapper.text()).toContain("Served by RomM");
    expect(wrapper.text()).toContain("Verified");
    expect(wrapper.text()).toContain(
      "Source changed. Prepare the download again.",
    );
    expect(wrapper.text()).toContain("Cancelled");
    expect(wrapper.text()).toContain("Expired");
    expect(wrapper.text()).toContain("Download failed");
  });

  it("renders safe aggregate facts without opaque identifiers or local-save claims", () => {
    const wrapper = mount(DownloadTransferHistory, {
      props: {
        sessions: [session("handed_to_browser")],
        componentLabels: ["Main game", "Updates"],
      },
    });

    expect(wrapper.text()).toContain("Main game, Updates");
    expect(wrapper.text()).toContain("1 KB");
    expect(wrapper.text()).not.toContain("opaque-handed_to_browser");
    expect(wrapper.text()).not.toMatch(
      /(source|NAS|local|saved|downloaded|completed|checksum|resumable|https?:\/\/|token)/i,
    );
  });

  it("shows bounded loading and error states without leaking response data", () => {
    const loading = mount(DownloadTransferHistory, {
      props: { sessions: [], loading: true },
    });
    expect(
      loading.find("[data-testid='download-history-loading']").exists(),
    ).toBe(true);

    const error = mount(DownloadTransferHistory, {
      props: { sessions: [], error: true },
    });
    expect(error.text()).toContain("rom.download-failed-description");
    expect(error.text()).not.toContain("opaque backend detail");
  });

  it("does not confuse an empty history with an unavailable download set", () => {
    const wrapper = mount(DownloadTransferHistory, {
      props: { sessions: [], queueItems: [] },
    });

    expect(
      wrapper.find("[data-testid='download-history-empty']").exists(),
    ).toBe(false);
    expect(wrapper.text()).not.toContain(
      "No complete download set is available",
    );
  });

  it("renders an enhanced queue verification as successful", () => {
    const wrapper = mount(DownloadTransferHistory, {
      props: {
        sessions: [],
        queueItems: [
          {
            file_id: "member-verified",
            destination: "game.bin",
            size: 1024,
            sha256: "a".repeat(64),
            snapshot: "snapshot",
            download: "https://example.invalid/download",
            status: "verified",
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("Verified");
    expect(wrapper.text()).not.toContain("Download failed");
  });

  it("offers a per-file cancel action for persisted transfer items", async () => {
    const wrapper = mount(DownloadTransferHistory, {
      props: { sessions: [session("queued")] },
    });

    expect(
      wrapper
        .findAll("button")
        .filter((button) => button.text() === "Cancel download"),
    ).toHaveLength(1);

    const rowCancel = wrapper
      .findAll("li button")
      .find((button) => button.text() === "Cancel download");
    await rowCancel?.trigger("click");

    expect(wrapper.emitted("cancel-item")).toEqual([["opaque-queued", 42]]);
  });

  it("removes one terminal file entry without removing the session", async () => {
    const completed = session("served");
    completed.status = "completed";
    const wrapper = mount(DownloadTransferHistory, {
      props: { sessions: [completed] },
    });

    await wrapper
      .findAll("li button")
      .find((button) => button.text() === "Delete download entry")
      ?.trigger("click");

    expect(wrapper.emitted("remove-item")).toEqual([["opaque-served", 42]]);
  });

  it("offers retry for a failed enhanced member in a completed partial session", async () => {
    const partial = session("failed");
    partial.mode = "enhanced";
    partial.status = "completed";
    const wrapper = mount(DownloadTransferHistory, {
      props: { sessions: [partial] },
    });

    const retry = wrapper
      .findAll("li button")
      .find((button) => button.text() === "Resume download");
    expect(retry).toBeDefined();

    await retry?.trigger("click");

    expect(wrapper.emitted("resume-session")).toEqual([
      ["opaque-failed", "member-failed"],
    ]);
  });

  it("keeps previous attempts visible when a file is retried", () => {
    const older = session("failed");
    older.id = "older-session";
    const newer = session("served");
    newer.id = "newer-session";
    older.items[0].manifest_member_id = newer.items[0].manifest_member_id;
    const wrapper = mount(DownloadTransferHistory, {
      props: { sessions: [newer, older] },
    });

    expect(
      wrapper.findAll("[data-testid='download-history-list'] > li"),
    ).toHaveLength(2);
  });
});
