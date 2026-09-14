import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const source = readFileSync(
  "src/v2/components/GameDetails/PcDlcNotesTab.vue",
  "utf8",
);

describe("PcDlcNotesTab", () => {
  it("keeps note requests nested under the resolved DLC component", () => {
    expect(source).toContain("/pc-components/${props.component.id}/notes");
    expect(source).toContain("expected_version");
    expect(source).not.toContain("/roms/${props.romId}/notes");
    expect(source).not.toContain("save-data");
  });

  it("uses established note labels and refreshes the component after mutation", () => {
    expect(source).toContain("t('rom.note-title')");
    expect(source).toContain("t('rom.note-content')");
    expect(source).toContain('t(isPublic ? "rom.public" : "rom.private")');
    expect(source).toContain(
      'const emit = defineEmits<{ (event: "refresh"): void }>()',
    );
    expect(source).toContain('emit("refresh")');
  });
});
