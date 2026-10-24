import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import * as project from "./project";

describe("public project identity", () => {
  it("owns product and repository metadata", () => {
    expect(project).toMatchObject({
      PROJECT_NAME: "ZockArchive",
      PROJECT_SHORT_NAME: "ZA",
      PROJECT_DESCRIPTION: "A self-hosted PC and console game archive",
      PROJECT_REPOSITORY: "D1skanime/zockarchive",
      PROJECT_GITHUB_URL: "https://github.com/D1skanime/zockarchive",
      PROJECT_DOCS_URL:
        "https://github.com/D1skanime/zockarchive/tree/main/docs",
      PROJECT_RELEASES_URL: "https://github.com/D1skanime/zockarchive/releases",
      PROJECT_RELEASE_API_URL:
        "https://api.github.com/repos/D1skanime/zockarchive/releases",
    });
    expect(project.projectReleaseTagUrl("v1.2.3")).toBe(
      "https://github.com/D1skanime/zockarchive/releases/tag/v1.2.3",
    );
  });

  it("keeps identity dependency-free for build and bootstrap", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/v2/config/project.ts"),
      "utf8",
    );
    expect(source).not.toMatch(/\bimport\s*(?:[("'*{]|[\w])/);
    expect(source).not.toMatch(/\bexport\s+(?:\*|{[^}]*})\s+from\s/);
    expect(source).not.toMatch(/\brequire\s*\(/);
  });

  it("uses the pure identity for router fallbacks", () => {
    const source = readFileSync(
      resolve(process.cwd(), "src/plugins/router.ts"),
      "utf8",
    );
    expect(source).toContain('from "@/v2/config/project"');
    expect(source).toContain("title: PROJECT_NAME");
    expect(source).not.toMatch(/["'](?:RomM|PGDP)["']/);
  });
});
