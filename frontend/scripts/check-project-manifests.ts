import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  PROJECT_DESCRIPTION,
  PROJECT_NAME,
  PROJECT_SHORT_NAME,
} from "../src/v2/config/project";

// Inspect emitted files, since public assets and VitePWA have separate owners.
const directory = process.argv[2];
assert(
  directory,
  "Usage: node --import tsx scripts/check-project-manifests.ts <output-directory>",
);
const output = resolve(directory);
const html = readFileSync(resolve(output, "index.html"), "utf8");
assert.match(html, new RegExp("<title>\\s*" + PROJECT_NAME + "\\s*</title>"));
assert.match(html, new RegExp("<span>\\s*" + PROJECT_NAME + "\\s*</span>"));
assert(
  !/PGDP|RomM|pgdp_logo/.test(html),
  "Built HTML retains obsolete display identity",
);

const manifestLinks = [...html.matchAll(/<link\b[^>]*>/gi)]
  .map(([tag]) => {
    const attrs = Object.fromEntries(
      [...tag.matchAll(/([\w-]+)\s*=\s*["']([^"']*)["']/g)].map(
        ([, key, value]) => [key.toLowerCase(), value],
      ),
    );
    return attrs.rel?.toLowerCase().split(/\s+/).includes("manifest")
      ? attrs.href
      : undefined;
  })
  .filter((href): href is string => Boolean(href));

for (const filename of ["site.webmanifest", "manifest.webmanifest"]) {
  assert(
    manifestLinks.some(
      (href) =>
        href === filename ||
        href === "/" + filename ||
        href === "./" + filename,
    ),
    "Built HTML must link " + filename,
  );
  const manifest = JSON.parse(readFileSync(resolve(output, filename), "utf8"));
  assert.equal(manifest.name, PROJECT_NAME, filename + " name");
  assert.equal(
    manifest.short_name,
    PROJECT_SHORT_NAME,
    filename + " short_name",
  );
  assert.equal(
    manifest.description,
    PROJECT_DESCRIPTION,
    filename + " description",
  );
}
process.stdout.write(
  "Built HTML and both install manifests match " +
    PROJECT_NAME +
    " / " +
    PROJECT_SHORT_NAME +
    "\n",
);
