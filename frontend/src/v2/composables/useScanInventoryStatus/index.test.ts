import { describe, expect, it } from "vitest";
import { ref } from "vue";
import type { ScanOperationItemResult } from "@/v2/data/contracts";
import { useScanInventoryStatus } from "./index";

function item(): ScanOperationItemResult {
  return {
    id: 1,
    target_key: "target",
    mapping_id: 2,
    expected_revision: 3,
    relative_path: "Collection/Unknown",
    provider: "",
    outcome: "skipped",
    attempt_id: "attempt",
    inventory: {
      rom_id: 4,
      inventory_state: "unchanged",
      identified_windows: false,
      existing_game: true,
      retry_state: "cooldown",
      retry_eligible: false,
      next_eligible_at: "2026-10-22T12:00:00Z",
      is_identifying: false,
    },
  };
}
describe("inventory presentation", () => {
  it("retains orthogonal terminal unknown and server eligibility facts reactively", () => {
    const source = ref(item());
    const status = useScanInventoryStatus(source);
    expect(status.value.inventory).toEqual(source.value.inventory);
    expect(status.value.unresolved).toBe(true);
    expect(status.value.isIdentifying).toBe(false);
    expect(status.value.nextEligibleAt).toBe("2026-10-22T12:00:00Z");
    source.value = {
      ...item(),
      inventory: { ...item().inventory!, retry_state: "budget_deferred" },
    };
    expect(status.value.inventory?.retry_state).toBe("budget_deferred");
  });
  it("keeps absent observations unavailable", () => {
    const status = useScanInventoryStatus({
      ...item(),
      inventory: undefined,
    }).value;
    expect(status.inventory).toBeUndefined();
    expect(status.unresolved).toBeUndefined();
    expect(status.provider).toBeUndefined();
    expect(status.requests).toBeUndefined();
    expect(status.nextEligibleAt).toBeUndefined();
  });
  it.each(["cached", "no_request", "no_match", "failed"] as const)(
    "never animates restored %s observations as an active request",
    (state) => {
      const status = useScanInventoryStatus({
        ...item(),
        provider_execution: {
          state,
          invoked: state !== "no_request",
          requests: state === "cached" ? 0 : 2,
          is_identifying: false,
        },
      }).value;
      expect(status.provider?.state).toBe(state);
      expect(status.isIdentifying).toBe(false);
      expect(status.requests).toBe(state === "cached" ? 0 : 2);
    },
  );
  it("requires observed active dispatch without changing source", () => {
    const source = {
      ...item(),
      provider_execution: {
        state: "requested" as const,
        invoked: true,
        requests: 2,
        is_identifying: true,
      },
    };
    expect(useScanInventoryStatus(source).value.isIdentifying).toBe(true);
    expect(
      useScanInventoryStatus({
        ...source,
        provider_execution: {
          ...source.provider_execution,
          requests: 0,
        },
      }).value.isIdentifying,
    ).toBe(false);
    expect(source.inventory?.retry_eligible).toBe(false);
  });
});
