import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/SoundtrackPanel.vue",
  "utf8",
);

describe("SoundtrackPanel owned-media queue", () => {
  it("uses only owned soundtrack candidates and their ordered placements", () => {
    expect(source).toContain('item.role === "soundtrack"');
    expect(source).toContain('placement.surface === "soundtrack"');
    expect(source).toContain("loadPlaylistForRom");
    expect(source).toContain("mediaId: item.id");
    expect(source).not.toContain("getSoundtrackMetadata");
    expect(source).not.toContain("/files/content/");
    expect(source).not.toMatch(/\/soundtracks(?:\/|`|'|")/);
  });

  it("uploads and atomically reorders only through typed owned-media methods", () => {
    expect(source).toContain("uploadOwnedMedia");
    expect(source).toContain("replaceOwnedMediaPlacements");
    expect(source).toContain('role: "soundtrack"');
    expect(source).toContain("mediaIds: reordered");
    expect(source).toContain("await refreshCanonical()");
  });

  it("stops active tracks before confirmed owned deletion and retains decode retry", () => {
    expect(source).toContain(
      "if (activeTrackId.value === item.id) player.stop()",
    );
    expect(source).toContain('tone: "danger"');
    expect(source).toContain("deleteOwnedMedia");
    expect(source).toContain("player.hasError");
    expect(source).toContain("retryActiveTrack");
  });

  it("has permission-gated, labelled linear controls", () => {
    expect(source).toContain("useCan");
    expect(source).toContain("canManage");
    expect(source).toContain("aria-label");
    expect(source).toContain("t('rom.move-up')");
    expect(source).toContain("t('rom.move-down')");
  });
});
