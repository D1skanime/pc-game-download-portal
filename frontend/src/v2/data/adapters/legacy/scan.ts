import type { OperationRequest } from "../../contracts";
import { toLegacyScanOptions, type LegacyScanOptions } from "../../operations";
import socket from "./services/socket";

export function toLegacyScanPayload(
  request: OperationRequest,
): LegacyScanOptions {
  return toLegacyScanOptions(request);
}

export function startLegacyScan(request: OperationRequest): LegacyScanOptions {
  const payload = toLegacyScanPayload(request);
  socket.emit("scan", payload);
  return payload;
}

export function stopLegacyScan(): void {
  socket.emit("scan:stop");
}
