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
    expect(loading.text()).toContain("Loading");

    const error = mount(DownloadTransferHistory, {
      props: { sessions: [], error: "opaque backend detail" },
    });
    expect(error.text()).toContain("Download history is unavailable");
    expect(error.text()).not.toContain("opaque backend detail");
  });
});
