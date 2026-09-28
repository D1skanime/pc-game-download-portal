import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync("src/services/api/rom.ts", "utf8");

describe("owned-media API wrappers", () => {
  it("uploads role-bound media with progress through the parent owned-media route", () => {
    expect(source).toContain("function uploadOwnedMedia");
    expect(source).toContain("`/roms/${romId}/media/upload`");
    expect(source).toContain('formData.append("role", role)');
    expect(source).toContain(
      'formData.append("expected_version", expectedVersion)',
    );
    expect(source).toContain('formData.append("media", file, file.name)');
    expect(source).toContain("onUploadProgress");
  });

  it("replaces a placement surface with the complete typed order", () => {
    expect(source).toContain("function replaceOwnedMediaPlacements");
    expect(source).toContain("RomOwnedMediaReorderRequest");
    expect(source).toContain(
      "api.put<DetailedRom>(`/roms/${romId}/media/placements`, payload)",
    );
  });
});
