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
    expect(source).toMatch(
      /import \{[\s\S]*RBtn,[\s\S]*RCarousel,[\s\S]*RDropzone,/,
    );
    expect(source).toContain("function mediaContentUrl(mediaId: number)");
    expect(source).toContain("return `/api${endpoint}/${mediaId}/content`");
    expect(source).toContain("lightboxOpen");
    expect(source).toContain("fullscreen");
    expect(source).toContain("show-thumbnails");
  });

  it("keeps placement controls permission-gated and component-scoped", () => {
    expect(source).toContain('useCan("rom.edit"');
    expect(source).toContain("/placement");
    expect(source).toMatch(/t\(['"]rom\.add-to-overview['"]\)/);
    expect(source).toMatch(/t\(['"]rom\.remove-from-overview['"]\)/);
  });

  it("renders localized media role and useful source labels", () => {
    expect(source).toContain("function mediaRoleLabel");
    expect(source).toContain("function mediaSourceLabel");
    expect(source).toContain("t(`rom.pc-media-role-${item.role}`)");
    expect(source).toContain('t("rom.pc-media-source-provider")');
    expect(source).toContain('t("rom.pc-media-source-uploaded")');
    expect(source).toContain("{{ mediaRoleLabel(item) }}");
    expect(source).toMatch(/\{\{\s*mediaSourceLabel\(item\)\s*\}\}/);
    expect(source).not.toContain("<strong>{{ item.role }}</strong>");
    expect(source).not.toContain("<span>{{ item.mime_type }}</span>");
  });

  it("localizes role selector labels while preserving enum values", () => {
    expect(source).toContain("const roleItems = computed(() =>");
    expect(source).toContain("title: t(`rom.pc-media-role-${value}`)");
    expect(source).toContain("value,");
    expect(source).toContain(':items="roleItems"');
    expect(source).toContain('item-title="title"');
    expect(source).toContain('item-value="value"');
    expect(source).toContain('body.append("role", role.value)');
    expect(source).toContain("item.role === role.value");
  });

  it("refreshes local media before reporting deletion success", () => {
    expect(source).toMatch(
      /await api\.delete[\s\S]+await load\(\)[\s\S]+emit\("refresh"\)[\s\S]+pc-media-deleted/,
    );
  });
});
