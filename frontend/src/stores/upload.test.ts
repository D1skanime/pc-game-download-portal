import type { AxiosProgressEvent } from "axios";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import storeUpload from "@/stores/upload";

type UploadStore = ReturnType<typeof storeUpload>;
type OperationUploadStore = UploadStore & {
  startOperation(operationId: string, displayFilename: string): void;
  updateOperation(operationId: string, progressEvent: AxiosProgressEvent): void;
  failOperation(operationId: string, reason: string): void;
};
type OperationFile = UploadStore["files"][number] & {
  operationKey?: string;
};

function progress(
  loaded: number,
  total: number,
  rate = 256,
): AxiosProgressEvent {
  return {
    bytes: loaded,
    event: new ProgressEvent("progress"),
    lengthComputable: true,
    loaded,
    progress: loaded / total,
    rate,
    total,
  };
}

describe("upload store compatibility", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("preserves filename-keyed start, update, and fail transitions", () => {
    const store = storeUpload();
    store.start("same.bin");
    store.start("same.bin");

    const event = progress(25, 100);
    store.update("same.bin", event);
    store.fail("same.bin", "bounded failure");

    expect(store.files).toHaveLength(2);
    expect(store.files[0]).toMatchObject({
      failed: true,
      failureReason: "bounded failure",
      filename: "same.bin",
      finished: false,
      loaded: 25,
      progress: 25,
      rate: 256,
      total: 100,
    });
    expect(store.files[1]).toMatchObject({
      failed: false,
      failureReason: "",
      filename: "same.bin",
      finished: false,
      loaded: 0,
      progress: 0,
      rate: 0,
      total: 0,
    });
  });

  it("preserves chunk progress, clearFinished, and reset behavior", () => {
    const store = storeUpload();
    store.start("active.bin");
    store.start("done.bin");
    store.start("failed.bin");

    store.updateChunkProgress("done.bin", 100, 200, 50);
    store.updateChunkProgress("active.bin", 25, 400);
    store.fail("failed.bin", "failed");

    expect(store.files[0]).toMatchObject({
      filename: "active.bin",
      finished: false,
      loaded: 100,
      progress: 25,
      total: 400,
    });
    expect(store.files[1]).toMatchObject({
      filename: "done.bin",
      finished: true,
      loaded: 200,
      progress: 100,
      rate: 50,
      total: 200,
    });

    store.clearFinished();
    expect(store.files.map((file) => file.filename)).toEqual(["active.bin"]);
    store.reset();
    expect(store.files).toEqual([]);
  });

  it("replaces only the stale record for the same operation key", () => {
    const store = storeUpload() as OperationUploadStore;
    expect(typeof store.startOperation).toBe("function");

    store.start("retry.pdf");
    store.startOperation("primary-manual:41", "retry.pdf");
    store.failOperation("primary-manual:41", "old failure");
    store.startOperation("primary-manual:42", "other.pdf");
    store.startOperation("primary-manual:41", "retry.md");

    expect(
      (store.files as OperationFile[]).map((file) => ({
        failed: file.failed,
        filename: file.filename,
        operationKey: file.operationKey,
      })),
    ).toEqual([
      {
        failed: false,
        filename: "retry.pdf",
        operationKey: undefined,
      },
      {
        failed: false,
        filename: "other.pdf",
        operationKey: "primary-manual:42",
      },
      {
        failed: false,
        filename: "retry.md",
        operationKey: "primary-manual:41",
      },
    ]);

    const event = progress(75, 100);
    store.updateOperation("primary-manual:41", event);
    store.failOperation("primary-manual:41", "new failure");

    expect(store.files[1]).toMatchObject({
      failed: false,
      filename: "other.pdf",
      progress: 0,
    });
    expect(store.files[2]).toMatchObject({
      failed: true,
      failureReason: "new failure",
      filename: "retry.md",
      loaded: 75,
      progress: 75,
    });

    store.startOperation("primary-manual:41", "retry.md");
    expect(store.files).toHaveLength(3);
    expect(store.files[2]).toMatchObject({
      failed: false,
      failureReason: "",
      filename: "retry.md",
      loaded: 0,
      progress: 0,
    });
  });
});
