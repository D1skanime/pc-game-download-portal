import { computed, toValue, type MaybeRefOrGetter } from "vue";
import type { ScanOperationItemResult } from "@/v2/data/contracts";

export function useScanInventoryStatus(
  source: MaybeRefOrGetter<ScanOperationItemResult>,
) {
  return computed(() => {
    const item = toValue(source);
    const inventory = item.inventory ?? undefined;
    const provider = item.provider_execution ?? undefined;
    return {
      inventory,
      provider,
      unresolved:
        inventory?.identified_windows == null
          ? undefined
          : !inventory.identified_windows,
      nextEligibleAt: inventory?.next_eligible_at ?? undefined,
      requests: provider?.requests,
      isIdentifying:
        provider?.state === "requested" &&
        provider.invoked &&
        provider.requests > 0 &&
        provider.is_identifying === true,
    };
  });
}
