import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  resolve(process.cwd(), "src/v2/components/GameDetails/SaveDataTab.vue"),
  "utf8",
);
const assetListSource = readFileSync(
  resolve(process.cwd(), "src/v2/components/shared/AssetList.vue"),
  "utf8",
);

describe("SaveDataTab source contract", () => {
  it("keeps save/state mutations on canonical APIs and refreshes ROM state", () => {
    expect(source).toContain("saveApi.uploadSaves");
    expect(source).toContain("stateApi.uploadStates");
    expect(source).toContain("saveApi.deleteSaves");
    expect(source).toContain("stateApi.deleteStates");
    expect(source).toContain("await refreshRom()");
    expect(source).toContain("rom.save-data-file-hint");
  });

  it("does not route save data through gallery media endpoints", () => {
    expect(source).not.toContain("uploadGalleryScreenshots");
    expect(source).not.toContain("deleteScreenshot");
    expect(source).not.toContain("ScreenshotsTab");
    expect(assetListSource).toContain("save-format-raw");
    expect(assetListSource).toContain("save-format-zip");
  });
});
