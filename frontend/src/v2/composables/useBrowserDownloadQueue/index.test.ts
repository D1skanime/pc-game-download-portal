import { describe, expect, it } from "vitest";
import {
  getEnhancedDirectoryPicker,
  isEnhancedDownloadSupported,
  validateEnhancedResponse,
} from "./index";

describe("enhanced browser download protocol", () => {
  it("is capability detected instead of user-agent detected", () => {
    expect(isEnhancedDownloadSupported()).toBe(
      typeof window !== "undefined" &&
        typeof (window as Window & { showDirectoryPicker?: unknown })
          .showDirectoryPicker === "function",
    );
    expect(getEnhancedDirectoryPicker()).toBeTypeOf("undefined");
  });

  it("requires exact 206 content range for resumed responses", () => {
    expect(
      validateEnhancedResponse(
        new Response("bytes", {
          status: 206,
          headers: { "Content-Range": "bytes 4-8/9" },
        }),
        4,
        9,
      ),
    ).toBe(true);
    expect(
      validateEnhancedResponse(
        new Response("bytes", {
          status: 200,
          headers: { "Content-Length": "5" },
        }),
        4,
        9,
      ),
    ).toBe(false);
  });
});
