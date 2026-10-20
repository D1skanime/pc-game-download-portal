import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { ScanOperationItemResult } from "@/v2/data/contracts";
import InventoryStatusSummary from "./InventoryStatusSummary.vue";

vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    locale: { value: "de_DE" },
    t: (key: string, args?: Record<string, unknown>) =>
      key + (args ? JSON.stringify(args) : ""),
  }),
}));
const item: ScanOperationItemResult = {
  id: 1,
  target_key: "Unknown <game>",
  relative_path: "child/game",
  mapping_id: 1,
  expected_revision: 2,
  attempt_id: "attempt",
  provider: "steam",
  outcome: "completed",
  inventory: {
    rom_id: 7,
    inventory_state: "unchanged",
    identified_windows: false,
    existing_game: true,
    retry_state: "cooldown",
    next_eligible_at: "2026-10-21T12:00:00Z",
  },
  provider_execution: { state: "no_request", invoked: false, requests: 0 },
};
function render(stats = {}, items = [item]) {
  return mount(InventoryStatusSummary, {
    props: { stats, items, hasMore: true, loadingMore: false },
    global: {
      stubs: {
        RBtn: {
          props: ["loading"],
          template: "<button @click=\"$emit('click')\"><slot /></button>",
        },
        RTag: { props: ["text"], template: "<span>{{ text }}</span>" },
      },
    },
  });
}
describe("InventoryStatusSummary", () => {
  it("keeps absent counters unavailable and uses global game/request units", () => {
    const panel = render({
      inventory_checked: 500,
      inventory_unchanged: 490,
      unresolved_games: 12,
      provider_requests: 700,
    });
    expect(panel.text()).toContain('"n":500');
    expect(panel.text()).toContain('"n":700');
    expect(panel.text()).not.toContain("scan.inventory-changed");
    expect(panel.text()).not.toContain('"n":1}');
  });
  it("renders escaped terminal unresolved facts and server eligibility with timezone", () => {
    const panel = render();
    expect(panel.text()).toContain("scan.not-identified");
    expect(panel.text()).toContain("scan.inventory-unchanged");
    expect(panel.text()).toContain("scan.provider-no-request");
    expect(panel.text()).toContain("scan.metadata-retry-available-after");
    expect(panel.text()).toMatch(/UTC|GMT|MEZ|MESZ/);
    expect(panel.find("game").exists()).toBe(false);
    expect(panel.find(".r-v2-scan-platform__identifying").exists()).toBe(false);
  });
  it("requests another page only through an explicit existing-owner event", async () => {
    const panel = render();
    expect(panel.emitted("loadMore")).toBeUndefined();
    await panel.get("button").trigger("click");
    expect(panel.emitted("loadMore")).toHaveLength(1);
  });
});
