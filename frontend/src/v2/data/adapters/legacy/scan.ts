import type { OperationRequest } from "../../contracts";
import { toLegacyScanOptions, type LegacyScanOptions } from "../../operations";
import scanOperations from "../scanOperations";

export function toLegacyScanPayload(
  request: OperationRequest,
): LegacyScanOptions {
  return toLegacyScanOptions(request);
}

export function startLegacyScan(request: OperationRequest) {
  return scanOperations.submit(request);
}

export async function stopLegacyScan() {
  const snapshot = await scanOperations.restore();
  return snapshot ? scanOperations.cancel(snapshot) : null;
}
