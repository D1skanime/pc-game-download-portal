import type { AxiosProgressEvent } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as romService from "@/services/api/rom";

const mocks = vi.hoisted(() => ({
  apiPost: vi.fn(),
  failOperation: vi.fn(),
  startOperation: vi.fn(),
  updateOperation: vi.fn(),
}));

vi.mock("@/services/api", () => ({
  default: {
    post: mocks.apiPost,
  },
}));

vi.mock("@/stores/upload", () => ({
  default: () => ({
    failOperation: mocks.failOperation,
    startOperation: mocks.startOperation,
    updateOperation: mocks.updateOperation,
  }),
}));

type UploadManual = (input: { romId: number; file: File }) => Promise<unknown>;

function uploadManualExport(): UploadManual | undefined {
  return (
    romService as unknown as {
      uploadManual?: UploadManual;
    }
  ).uploadManual;
}

function progress(
  loaded: number,
  total: number,
  rate = 128,
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

describe("rom service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uploadManual_sends_one_file_in_one_request", async () => {
    const uploadManual = uploadManualExport();
    const stackTraceLimit = Error.stackTraceLimit;
    Error.stackTraceLimit = 1;
    try {
      expect(uploadManual).toEqual(expect.any(Function));
    } finally {
      Error.stackTraceLimit = stackTraceLimit;
    }
    if (!uploadManual) return;

    const allSettled = vi.spyOn(Promise, "allSettled");
    const firstFile = new File(["manual"], "guide.pdf", {
      type: "application/pdf",
    });
    const response = { data: { path_manual: "guide.pdf" } };
    mocks.apiPost.mockResolvedValueOnce(response);

    const request = uploadManual({ romId: 41, file: firstFile });

    expect(mocks.startOperation).toHaveBeenCalledTimes(1);
    expect(mocks.startOperation).toHaveBeenCalledWith(
      "primary-manual:41",
      "guide.pdf",
    );
    expect(mocks.apiPost).toHaveBeenCalledTimes(1);
    const [url, body, config] = mocks.apiPost.mock.calls[0] as [
      string,
      FormData,
      {
        headers: Record<string, string>;
        params: Record<string, never>;
        onUploadProgress: (event: AxiosProgressEvent) => void;
      },
    ];
    expect(url).toBe("/roms/41/manuals");
    expect(body).toBeInstanceOf(FormData);
    const formMembers: unknown[] = [];
    body.forEach((value, key) => {
      formMembers.push([key, value]);
    });
    expect(formMembers).toEqual([["guide.pdf", firstFile]]);
    expect(config.headers).toEqual({
      "Content-Type": "multipart/form-data",
      "X-Upload-Filename": "guide.pdf",
    });
    expect(config.params).toEqual({});

    const progressEvent = progress(64, 128);
    config.onUploadProgress(progressEvent);
    expect(mocks.updateOperation).toHaveBeenCalledWith(
      "primary-manual:41",
      progressEvent,
    );
    await expect(request).resolves.toBe(response);
    expect(allSettled).not.toHaveBeenCalled();

    const error = {
      response: { data: { detail: "Manual upload failed" } },
    };
    mocks.apiPost.mockRejectedValueOnce(error);
    await expect(
      uploadManual({
        romId: 41,
        file: new File(["retry"], "guide.pdf"),
      }),
    ).rejects.toBe(error);
    expect(mocks.failOperation).toHaveBeenLastCalledWith(
      "primary-manual:41",
      "Manual upload failed",
    );

    mocks.apiPost.mockResolvedValue(response);
    await uploadManual({
      romId: 41,
      file: new File(["replacement"], "guide.md"),
    });
    await uploadManual({
      romId: 42,
      file: new File(["other"], "guide.pdf"),
    });

    expect(mocks.startOperation.mock.calls.slice(1)).toEqual([
      ["primary-manual:41", "guide.pdf"],
      ["primary-manual:41", "guide.md"],
      ["primary-manual:42", "guide.pdf"],
    ]);
    expect(mocks.apiPost).toHaveBeenCalledTimes(4);
    expect(
      mocks.apiPost.mock.calls.every((call) => call[1] instanceof FormData),
    ).toBe(true);
    expect(allSettled).not.toHaveBeenCalled();
    allSettled.mockRestore();
  });
});
