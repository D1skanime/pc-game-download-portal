import type {
  PcAutomationBatchRequest,
  PcAutomationBatchResponse,
  PcAutomationQueueResponse,
  PcAutomationReviewActionRequest,
  PcAutomationReviewActionResponse,
} from "@/__generated__";
import api from "@/services/api";

function getReviewQueue(limit: number, offset: number) {
  return api.get<PcAutomationQueueResponse>(
    "/roms/pc-automation/review-queue",
    {
      params: { limit, offset },
    },
  );
}

function acceptReviewItem(
  queueId: number,
  body: PcAutomationReviewActionRequest,
) {
  return api.post<PcAutomationReviewActionResponse>(
    `/roms/pc-automation/review-queue/${queueId}/accept`,
    body,
  );
}

function skipReviewItem(
  queueId: number,
  body: PcAutomationReviewActionRequest,
) {
  return api.post<PcAutomationReviewActionResponse>(
    `/roms/pc-automation/review-queue/${queueId}/skip`,
    body,
  );
}

function batchAcceptReviewItems(body: PcAutomationBatchRequest) {
  return api.post<PcAutomationBatchResponse>(
    "/roms/pc-automation/review-queue/batch-accept",
    body,
  );
}

export default {
  getReviewQueue,
  acceptReviewItem,
  skipReviewItem,
  batchAcceptReviewItems,
};
