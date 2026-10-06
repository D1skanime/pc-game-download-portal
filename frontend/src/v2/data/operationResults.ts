import type {
  OperationItemResult,
  OperationResult,
  OperationStatus,
  RetryInput,
} from "./contracts";

export interface OperationItemInput extends Omit<
  OperationItemResult,
  "operationId" | "jobId"
> {}

export interface CreateOperationResultInput {
  operationId: string;
  jobId: string;
  status: OperationStatus;
  preview: boolean;
  items: OperationItemInput[];
  diagnostics?: OperationResult["diagnostics"];
  impact?: OperationResult["impact"];
}

export function createOperationResult(
  input: CreateOperationResultInput,
): OperationResult {
  return {
    operationId: input.operationId,
    jobId: input.jobId,
    status: input.status,
    preview: input.preview,
    items: input.items.map((item) => ({
      ...item,
      operationId: input.operationId,
      jobId: input.jobId,
    })),
    diagnostics: input.diagnostics,
    impact: input.impact,
  };
}

export function retryIdentity(item: OperationItemResult): string {
  return [item.operationId, item.jobId, item.itemId].join("/");
}

export function isRetryable(item: OperationItemResult): boolean {
  return item.outcome === "retryable";
}

export function createRetryInput(
  result: OperationResult,
  maxAttempts = 3,
): RetryInput {
  const retryableItems = result.items.filter(isRetryable);
  return {
    itemIds: retryableItems.map((item) => item.itemId),
    maxAttempts,
    ...(retryableItems[0]
      ? { resumeFrom: retryIdentity(retryableItems[0]) }
      : {}),
  };
}
