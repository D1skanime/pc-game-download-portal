import { readFileSync, readdirSync } from "node:fs";
import { resolve, relative } from "node:path";

const root = resolve(process.cwd(), "src/v2");
const baseline = new Map<string, number>([
  ["lib/forms/RSelect/RSelect.vue", 1800],
  ["components/Gallery/GalleryShell.vue", 1350],
  ["components/GameCard/GameCard.vue", 1100],
  ["views/GameDetails.vue", 800],
  ["views/Scan.vue", 1500],
  ["lib/forms/RTextField/RTextField.vue", 1050],
  ["views/Player/EmulatorJS.vue", 1100],
  ["views/Player/Stream.vue", 1000],
]);

const violations: string[] = [];
const files: string[] = [];

function walk(dir: string): void {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) walk(path);
    else if (
      /\.(vue|ts)$/.test(entry.name) &&
      !/\.(test|stories)\./.test(entry.name)
    )
      files.push(path);
  }
}
walk(root);

for (const file of files) {
  const rel = relative(root, file).replaceAll("\\", "/");
  const lines = readFileSync(file, "utf8").split("\n").length;
  const allowed = baseline.get(rel) ?? 900;
  if (lines > allowed)
    violations.push(rel + ": " + lines + " lines exceeds " + allowed);

  if (!rel.startsWith("data/adapters/")) {
    const source = readFileSync(file, "utf8");
    if (/@\/(stores|services)(?:\/api)?\//.test(source)) {
      violations.push(rel + ": direct legacy store/service import");
    }
  }
}

if (violations.length > 0) {
  console.error("V2 maintainability gate failed:");
  for (const violation of violations) console.error("- " + violation);
  process.exit(1);
}

console.log(
  "V2 maintainability gate passed for " + files.length + " production files.",
);
