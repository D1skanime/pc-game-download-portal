import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function searchCoverDialogSource(): string {
  return readFileSync(
    resolve(process.cwd(), "src/v2/components/Dialogs/SearchCoverDialog.vue"),
    "utf8",
  );
}

describe("SearchCoverDialog operation parity guards", () => {
  it("ignores cover results from a previous dialog session", () => {
    const source = searchCoverDialogSource();

    expect(source).toContain("let searchSeq = 0;");
    expect(source).toContain("const seq = ++searchSeq;");
    expect(source).toContain("if (seq !== searchSeq) return;");
    expect(source).toContain("searchSeq++;");
  });

  it("keeps provider and SteamGridDB media selection on the existing consumer event", () => {
    const source = searchCoverDialogSource();

    expect(source).toContain('emitter?.emit("updateUrlCover", url);');
    expect(source).toContain(
      'emitter?.emit("updateUrlCover", url.replace("thumb", "grid"));',
    );
  });
});
