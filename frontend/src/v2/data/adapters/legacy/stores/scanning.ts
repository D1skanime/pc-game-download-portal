import type { ScanStatsTransport } from "@/v2/data/contracts";

export { default } from "@/stores/scanning";
export * from "@/stores/scanning";

export function transportScanStats(
  stats: ScanStatsTransport | undefined,
): ScanStatsTransport | undefined {
  return stats === undefined ? undefined : { ...stats };
}
