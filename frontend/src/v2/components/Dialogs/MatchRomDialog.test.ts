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
