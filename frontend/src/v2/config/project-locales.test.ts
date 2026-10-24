import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { createI18n } from "vue-i18n";
import baseline from "./project-locales.baseline.json";

const root = resolve(process.cwd(), "src/locales");
const normalize = (value: string) =>
  value.replace(/RomM|PGDP|ZockArchive/g, "<PRODUCT>");
const digest = (value: unknown) =>
  createHash("sha256")
    .update(normalize(JSON.stringify(value)))
    .digest("hex");

describe("localized product identity", () => {
  it("covers all eighteen supported languages", () => {
    expect(
      readdirSync(root)
        .filter((name) => /^[a-z]{2}_[A-Z]{2}$/.test(name))
        .sort(),
    ).toEqual(Object.keys(baseline).sort());
    expect(Object.keys(baseline)).toHaveLength(18);
  });

  for (const [locale, namespaces] of Object.entries(baseline)) {
    it(`${locale} preserves every key and all non-brand semantics`, () => {
      for (const [namespace, contract] of Object.entries(namespaces)) {
        const values = JSON.parse(
          readFileSync(resolve(root, locale, `${namespace}.json`), "utf8"),
        );
        // Complete normalized values preserve translations, interpolation, HTML and plural branches.
        expect(digest(values), namespace).toBe(contract.digest);
        for (const key of contract.brandedKeys) {
          expect(values[key], `${namespace}.${key}`).toContain("ZockArchive");
          expect(values[key], `${namespace}.${key}`).not.toMatch(/RomM|PGDP/);
        }
      }
    });
  }

  it("renders recovery, interpolation and plural copy through vue-i18n", () => {
    const load = (namespace: string): Record<string, string> =>
      JSON.parse(
        readFileSync(resolve(root, "en_US", `${namespace}.json`), "utf8"),
      );
    const i18n = createI18n({
      legacy: false,
      locale: "en_US",
      messages: {
        en_US: {
          rom: load("rom"),
          setup: load("setup"),
          settings: load("settings"),
        },
      },
    });
    expect(i18n.global.t("setup.assign-folder", { folder: "Games" })).toBe(
      "Assign Games to a ZockArchive platform",
    );
    expect(i18n.global.t("rom.remove-from-catalog-body", { n: 2 }, 2)).toBe(
      "Remove 2 games from ZockArchive's catalog.",
    );
    expect(i18n.global.t("rom.download-failed-description")).toBe(
      "ZockArchive could not continue this file. Check your connection and folder permission, then retry.",
    );
    expect(
      i18n.global.t("settings.config-file-parse-error-desc", {
        error: "Invalid syntax",
      }),
    ).toContain("Details: Invalid syntax");
  });
});
