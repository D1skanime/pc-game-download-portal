import { describe, expect, it } from "vitest";
import {
  createOperationResult,
  createRetryInput,
  retryIdentity,
} from "./operationResults";

describe("operation results", () => {
  it("preserves explicit per-item outcomes and stable retry identity", () => {
    const result = createOperationResult({
      operationId: "op-24-09",
      jobId: "job-7",
      status: "partial",
      preview: false,
      items: [
        { itemId: "rom:41", outcome: "changed", message: "Updated title" },
        {
          itemId: "rom:42",
          outcome: "protected",
          message: "Manual value kept",
        },
        { itemId: "component:9", outcome: "retryable", attempt: 1 },
      ],
    });

    expect(result.items.map((item) => item.outcome)).toEqual([
      "changed",
      "protected",
      "retryable",
    ]);
    expect(retryIdentity(result.items[2])).toBe("op-24-09/job-7/component:9");
    expect(createRetryInput(result)).toEqual({
      itemIds: ["component:9"],
      maxAttempts: 3,
      resumeFrom: "op-24-09/job-7/component:9",
    });
  });

  it("keeps not-found and failed outcomes independently explainable", () => {
    const result = createOperationResult({
      operationId: "op-24-09",
      jobId: "job-8",
      status: "failed",
      preview: false,
      items: [
        {
          itemId: "rom:50",
          outcome: "not-found",
          message: "No provider match",
        },
        { itemId: "rom:51", outcome: "failed", message: "Provider timeout" },
        { itemId: "rom:52", outcome: "unchanged" },
      ],
    });

    expect(result.items).toMatchObject([
      { itemId: "rom:50", outcome: "not-found", message: "No provider match" },
      { itemId: "rom:51", outcome: "failed", message: "Provider timeout" },
      { itemId: "rom:52", outcome: "unchanged" },
    ]);
    expect(createRetryInput(result)).toEqual({
      itemIds: [],
      maxAttempts: 3,
    });
  });
});
