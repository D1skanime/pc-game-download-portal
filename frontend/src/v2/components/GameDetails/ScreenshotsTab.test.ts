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

  it("defines a larger Overview grid that reflows at the shared breakpoint", () => {
    expect(source).toContain('layout?: "overview"');
    expect(source).toContain("r-v2-det-shots--overview");
    expect(source).toContain(
      "grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));",
    );
    expect(source).toContain(
      'html[data-bp~="sm-and-down"] .r-v2-det-shots--overview',
    );
    expect(source).toContain(
      "grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));",
    );
  });
});
