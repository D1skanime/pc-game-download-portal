import type { AxiosResponse } from "axios";
import type {
  DownloadTransferEventResponse,
  DownloadTransferResponse,
} from "@/__generated__";
import api from "@/services/api";

export type DownloadTransferMode = "standard" | "enhanced";
export type DownloadTransferCreatePayload = {
  manifest_id: string;
  mode: DownloadTransferMode;
};
export type DownloadTransferEvent = {
  event_type:
    | "handoff"
    | "progress"
    | "pause"
    | "resume"
    | "verified"
    | "cancel"
    | "fail";
  observed_bytes?: number;
  error_code?: string | null;
  sha256?: string | null;
};

function create(payload: DownloadTransferCreatePayload) {
  return api.post<
    DownloadTransferResponse,
    AxiosResponse<DownloadTransferResponse>,
    DownloadTransferCreatePayload
  >("/download-transfer-sessions", payload);
}
function list(params?: { romId?: number; manifestId?: string }) {
  return api.get<DownloadTransferResponse[]>("/download-transfer-sessions", {
    params: { rom_id: params?.romId, manifest_id: params?.manifestId },
  });
}
function get(sessionId: string) {
  return api.get<DownloadTransferResponse>(
    `/download-transfer-sessions/${encodeURIComponent(sessionId)}`,
  );
}
function observe(
  sessionId: string,
  itemId: number,
  payload: DownloadTransferEvent,
) {
  return api.post<DownloadTransferEventResponse>(
    `/download-transfer-sessions/${encodeURIComponent(sessionId)}/items/${itemId}/events`,
    payload,
  );
}
export default { create, list, get, observe };
