import { describe, expect, it } from "vitest";
import { validateDownloadDestination } from "./downloadManifestPath";

describe("validateDownloadDestination", () => {
  it("returns safe relative POSIX path segments", () => {
    expect(validateDownloadDestination("patches/game.bin")).toEqual([
      "patches",
      "game.bin",
    ]);
  });

  it.each([
    "",
    "/absolute.bin",
    "../escape.bin",
    "safe/../escape.bin",
    "safe\\file.bin",
    "safe//file.bin",
  ])("rejects unsafe destination %s", (destination) =>
    expect(validateDownloadDestination(destination)).toBeNull(),
  );
});
