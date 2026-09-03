import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/PcDlcFiles.vue",
  "utf8",
);

describe("PcDlcFiles", () => {
  it("builds downloads from the selected component member IDs", () => {
    expect(source).toContain(
      "/pc-components/${props.component.id}/manifest-members/${memberId}/content",
    );
    expect(source).toContain("member.id");
    expect(source).toContain("member.sha256");
  });
});
