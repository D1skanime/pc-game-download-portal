import type { BulkOperationResponse, FirmwareSchema } from "@/__generated__";
import api from "@/services/api";

export const firmwareApi = api;

async function getFirmware({
  platformId = null,
}: {
  platformId?: number | null;
}) {
  return firmwareApi.get<FirmwareSchema[]>(`/firmware`, {
    params: {
      platform_id: platformId,
    },
  });
}

async function deleteFirmware({ firmware }: { firmware: FirmwareSchema[] }) {
  return api.post<BulkOperationResponse>("/firmware/delete", {
    firmware: firmware.map((s) => s.id),
  });
}

export default {
  getFirmware,
  deleteFirmware,
};
