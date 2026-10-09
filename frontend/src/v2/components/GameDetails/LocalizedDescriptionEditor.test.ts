import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/LocalizedDescriptionEditor.vue",
  "utf8",
);

describe("LocalizedDescriptionEditor", () => {
  it("uses the shared locale-scoped description contract for ROM-like entities", () => {
    expect(source).toContain("useManualDescription");
    expect(source).toContain("updateRomDescription");
    expect(source).toContain("updateComponentDescription");
    expect(source).toContain("expectedVersion");
  });

  it("exposes locale selection and explicit save, cancel, and reset actions", () => {
    expect(source).toContain("selectedLocale");
    expect(source).toContain("rom.description-locale");
    expect(source).toContain("rom.description-save");
    expect(source).toContain("rom.description-cancel");
    expect(source).toContain("rom.description-reset");
  });

  it("keeps provider and fallback text visible alongside the editable value", () => {
    expect(source).toContain("rom.description-source-manual");
    expect(source).toContain("rom.description-source-provider");
    expect(source).toContain("rom.description-source-fallback");
    expect(source).toContain("resolveManualDescription");
  });
});
