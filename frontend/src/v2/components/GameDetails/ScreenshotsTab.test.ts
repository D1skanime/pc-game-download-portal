import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/ScreenshotsTab.vue",
  "utf8",
);

describe("ScreenshotsTab responsive layout contract", () => {
  it("keeps the existing default screenshot grid contract", () => {
    expect(source).toContain(
      "grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));",
    );
    expect(source).toContain("r-v2-det-shots");
  });

  it("keeps Overview screenshots at three columns and reflows responsively", () => {
    expect(source).toContain('layout?: "overview"');
    expect(source).toContain("r-v2-det-shots--overview");
    expect(source).toContain(
      "grid-template-columns: repeat(3, minmax(0, 1fr));",
    );
    expect(source).toContain(
      'html[data-bp~="sm-and-down"] .r-v2-det-shots--overview',
    );
    expect(source).toContain(
      "grid-template-columns: repeat(2, minmax(0, 1fr));",
    );
    expect(source).toContain('html[data-bp~="xs"] .r-v2-det-shots--overview');
    expect(source).toContain("grid-template-columns: minmax(0, 1fr);");
  });
});
