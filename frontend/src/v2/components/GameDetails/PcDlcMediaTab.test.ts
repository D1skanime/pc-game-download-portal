import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/PcDlcMediaTab.vue",
  "utf8",
);

describe("PcDlcMediaTab", () => {
  it("uses only nested component-owned media endpoints", () => {
    expect(source).toContain("/pc-components/${props.component.id}/media");
    expect(source).toContain("expected_version");
    expect(source).toContain("useConfirm");
    expect(source).not.toContain("source_relative_path");
  });

  it("renders owned media previews in the parent-style fullscreen gallery", () => {
    expect(source).toContain("import { RBtn, RCarousel, RDropzone");
    expect(source).toContain("function mediaContentUrl(mediaId: number)");
    expect(source).toContain("lightboxOpen");
    expect(source).toContain("fullscreen");
    expect(source).toContain("show-thumbnails");
  });
});
