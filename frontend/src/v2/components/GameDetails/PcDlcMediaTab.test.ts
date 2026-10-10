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
    expect(source).toContain('ref<RomComponentOwnedMediaRole>("screenshot")');
    expect(source).toContain("filteredMedia");
    expect(source).toContain("placement");
  });

  it("renders owned media previews in the parent-style fullscreen gallery", () => {
    expect(source).toContain("import { RBtn, RCarousel, RDropzone");
    expect(source).toContain("function mediaContentUrl(mediaId: number)");
    expect(source).toContain("return `/api${endpoint}/${mediaId}/content`");
    expect(source).toContain("lightboxOpen");
    expect(source).toContain("fullscreen");
    expect(source).toContain("show-thumbnails");
  });

  it("keeps placement controls permission-gated and component-scoped", () => {
    expect(source).toContain('useCan("rom.edit"');
    expect(source).toContain("/placement");
    expect(source).toContain('t("rom.add-to-overview")');
    expect(source).toContain('t("rom.remove-from-overview")');
  });
});
