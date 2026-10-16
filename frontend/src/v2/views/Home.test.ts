import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync("src/v2/views/Home.vue", "utf8");

describe("Home mapping readiness gate", () => {
  it("uses the GET-only server readiness contract before exposing Scan", () => {
    expect(source).toContain("storageApi.getMappingsReadiness");
    expect(source).toContain('v-if="mappingReady"');
    expect(source).not.toContain('platform.slug === "win"');
  });

  it("keeps readiness evaluation free of storage mutations", () => {
    expect(source).not.toContain("bootstrapLegacy");
    expect(source).not.toContain("createMapping");
    expect(source).not.toContain("updateMapping");
    expect(source).not.toContain("removeMapping");
  });

  it("renders recovery guidance for blocked and errored readiness", () => {
    expect(source).toContain('t("storage.administration")');
    expect(source).toContain("loadMappingReadiness");
    expect(source).not.toContain("PLATFORM_STORAGE_MAPPING");
    expect(source).toContain("mappingReadiness === 'error'");
  });
});
