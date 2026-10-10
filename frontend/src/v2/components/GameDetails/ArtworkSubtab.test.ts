import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/ArtworkSubtab.vue",
  "utf8",
);

describe("ArtworkSubtab owned artwork management", () => {
  it("keeps artwork candidates distinct from ordered background placements", () => {
    expect(source).toContain("ownedArtwork");
    expect(source).toContain("backgrounds");
    expect(source).toContain("hasPlacement");
    expect(source).toContain("togglePlacement");
    expect(source).toContain("replaceOwnedMediaPlacements");
    expect(source).toContain('t("rom.backgrounds")');
    expect(source).toContain('t("rom.add-as-background")');
    expect(source).toContain('t("rom.remove-as-background")');
    expect(source).toContain('t("rom.add-to-overview")');
    expect(source).toContain('t("rom.remove-from-overview")');
    expect(source).toContain("togglePlacement(item, 'overview')");
  });

  it("uses the owned-media upload and deletion lifecycle", () => {
    expect(source).toContain("RDropzone");
    expect(source).toContain('const canManage = useCan("rom.edit", scope)');
    expect(source).not.toContain('useCan("rom.delete", scope)');
    expect(source).toContain("uploadOwnedMedia");
    expect(source).toContain('role: "artwork"');
    expect(source).toContain("item.origin === 'upload' && canManage");
    expect(source).toContain('tone: "danger"');
    expect(source).toContain("deleteOwnedMedia");
    expect(source).toContain("romsStore.refreshRom");
  });

  it("restores authoritative state before reporting an ordering conflict", () => {
    expect(source).toContain("response?.status === 409");
    expect(source).toContain("await refreshCanonical()");
    expect(source).toContain("common.move-up");
    expect(source).toContain("common.move-down");
  });

  it("keeps the uploaded artwork delete button as the visible tooltip activator", () => {
    expect(source).toMatch(
      /<RBtn\s+v-if="item\.origin === 'upload' && canManage"\s+icon="mdi-delete-outline"\s+:loading="mutatingId === item\.id"\s+:aria-label="t\('common\.delete'\)"\s+@click="deleteArtwork\(item\)"\s+><RTooltip activator="parent" :text="t\('common\.delete'\)" \/>/,
    );
    expect(source).not.toContain(
      `<RTooltip
              v-if="item.origin === 'upload' && canManage"
              :text="t('common.delete')"
              ><RBtn`,
    );
  });
});
