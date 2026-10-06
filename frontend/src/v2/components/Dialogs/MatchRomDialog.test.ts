import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  isPcMatchTarget,
  type PcMatchTarget,
} from "@/v2/components/MatchRom/types";

describe("MatchRomDialog PC targets", () => {
  it("requires a concrete classified component identity", () => {
    const target = {
      kind: "component",
      romId: 41,
      componentId: 7,
      componentKind: "dlc",
      label: "The Royal Edition",
    } satisfies PcMatchTarget;

    expect(target.componentKind).toBe("dlc");
    expect(isPcMatchTarget(target)).toBe(true);
  });
});

function matchDialogSource(): string {
  return readFileSync(
    resolve(process.cwd(), "src/v2/components/Dialogs/MatchRomDialog.vue"),
    "utf8",
  );
}

describe("MatchRomDialog operation parity guards", () => {
  it("keeps the classic match context until the update succeeds", () => {
    const source = matchDialogSource();

    expect(source).toContain("const updatedRom = {\n    ...targetRom");
    expect(source).toContain("closeDialog();\n  } catch");
    expect(source).not.toContain(
      "} finally {\n    matching.value = false;\n    closeDialog();",
    );
  });

  it("keeps specialized PC parent and DLC endpoints behind their target guard", () => {
    const source = matchDialogSource();

    expect(source).toContain('pcTarget.value.kind === "component"');
    expect(source).toContain("romApi.selectPcComponentMetadataCandidate");
    expect(source).toContain("romApi.selectPcMetadataCandidate");
    expect(source).toContain("expected_version: expectedVersion");
    expect(source).toContain("selected_media_ids: selectedMedia");
  });
});
