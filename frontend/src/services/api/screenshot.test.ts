import type { AxiosProgressEvent } from "axios";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import screenshotApi from "@/services/api/screenshot";
import storeUpload from "@/stores/upload";

const mocks = vi.hoisted(() => ({
  apiPost: vi.fn(),
}));

vi.mock("@/services/api", () => ({
  default: {
    post: mocks.apiPost,
  },
}));

function progress(loaded: number, total: number): AxiosProgressEvent {
  return {
    bytes: loaded,
    event: new ProgressEvent("progress"),
    lengthComputable: true,
    loaded,
    progress: loaded / total,
    rate: 64,
    total,
  };
}

describe("screenshot service upload progress compatibility", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("keeps filename labels and allSettled input ordering", async () => {
    const firstResponse = { id: 1, file_name: "first.png" };
    const secondResponse = { id: 2, file_name: "second.png" };
    const progressEvents = [progress(25, 100), progress(100, 100)];
    mocks.apiPost
      .mockImplementationOnce(
        (
          _url: string,
          _body: FormData,
          config: {
            onUploadProgress: (event: AxiosProgressEvent) => void;
          },
        ) => {
          config.onUploadProgress(progressEvents[0]);
          return Promise.resolve({ data: firstResponse });
        },
      )
      .mockImplementationOnce(
        (
          _url: string,
          _body: FormData,
          config: {
            onUploadProgress: (event: AxiosProgressEvent) => void;
          },
        ) => {
          config.onUploadProgress(progressEvents[1]);
          return Promise.resolve({ data: secondResponse });
        },
      );

    const results = await screenshotApi.uploadGalleryScreenshots({
      romId: 7,
      filesToUpload: [
        new File(["first"], "first.png"),
        new File(["second"], "second.png"),
      ],
    });

    expect(results).toEqual([
      { status: "fulfilled", value: firstResponse },
      { status: "fulfilled", value: secondResponse },
    ]);
    expect(mocks.apiPost).toHaveBeenCalledTimes(2);
    expect(mocks.apiPost.mock.calls.map((call) => call[0])).toEqual([
      "/screenshots",
      "/screenshots",
    ]);

    const uploadStore = storeUpload();
    expect(uploadStore.files.map((file) => file.filename)).toEqual([
      "first.png",
      "second.png",
    ]);
    expect(uploadStore.files.map((file) => file.finished)).toEqual([
      false,
      true,
    ]);
    expect(uploadStore.files.every((file) => !("operationKey" in file))).toBe(
      true,
    );
  });

  it("preserves duplicate-filename first-match progress and failure reasons", async () => {
    const error = { response: { data: { detail: "Screenshot rejected" } } };
    const successfulResponse = { id: 2, file_name: "same.png" };
    mocks.apiPost
      .mockImplementationOnce(
        (
          _url: string,
          _body: FormData,
          config: {
            onUploadProgress: (event: AxiosProgressEvent) => void;
          },
        ) => {
          config.onUploadProgress(progress(25, 100));
          return Promise.reject(error);
        },
      )
      .mockImplementationOnce(
        (
          _url: string,
          _body: FormData,
          config: {
            onUploadProgress: (event: AxiosProgressEvent) => void;
          },
        ) => {
          config.onUploadProgress(progress(100, 100));
          return Promise.resolve({ data: successfulResponse });
        },
      );

    const results = await screenshotApi.uploadGalleryScreenshots({
      romId: 8,
      filesToUpload: [
        new File(["first"], "same.png"),
        new File(["second"], "same.png"),
      ],
    });

    expect(results).toEqual([
      { status: "rejected", reason: error },
      { status: "fulfilled", value: successfulResponse },
    ]);
    const uploadStore = storeUpload();
    expect(uploadStore.files).toHaveLength(2);
    expect(uploadStore.files[0]).toMatchObject({
      failed: true,
      failureReason: "Screenshot rejected",
      filename: "same.png",
      finished: true,
      progress: 100,
    });
    expect(uploadStore.files[1]).toMatchObject({
      failed: false,
      failureReason: "",
      filename: "same.png",
      finished: false,
      progress: 0,
    });
  });
});
