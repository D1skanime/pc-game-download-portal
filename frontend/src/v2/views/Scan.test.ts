import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync("src/v2/views/Scan.vue", "utf8");

describe("Scan mapping readiness gate", () => {
  it("uses the same GET-only readiness helper and hides controls until ready", () => {
    expect(source).toContain("storageApi.getMappingReadiness");
    expect(source).toContain('v-if="!mappingReady"');
    expect(source).toContain('v-else\n      class="r-v2-scan-card"');
    expect(source).toContain('platform.slug === "win"');
  });

  it("defends the operation boundary even if scan is invoked directly", () => {
    expect(source).toContain("if (!mappingReady.value) return;");
    expect(source).toContain("mappingReady.value &&");
  });

  it("does not bootstrap or mutate mappings while checking readiness", () => {
    expect(source).not.toContain("bootstrapLegacy");
    expect(source).not.toContain("createMapping");
    expect(source).not.toContain("updateMapping");
    expect(source).not.toContain("removeMapping");
  });
});
