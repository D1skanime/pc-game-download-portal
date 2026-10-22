import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";
import enUS from "@/locales/en_US/rom.json";

const locales = [
  "en_US",
  "en_GB",
  "bg_BG",
  "cs_CZ",
  "de_DE",
  "es_ES",
  "fr_FR",
  "hu_HU",
  "it_IT",
  "ja_JP",
  "ko_KR",
  "pl_PL",
  "pt_BR",
  "ro_RO",
  "ru_RU",
  "tr_TR",
  "zh_CN",
  "zh_TW",
];
const files = import.meta.glob<Record<string, unknown>>("@/locales/*/*.json", {
  eager: true,
  import: "default",
});
const trees: Record<string, Record<string, unknown>> = {};
for (const [path, messages] of Object.entries(files)) {
  const [locale, namespace] = path.split("/").slice(-2);
  (trees[locale] ??= {})[namespace] = messages;
}
const phaseKeys = [
  "description-cancel",
  "description-language-fallback",
  "description-source-localized",
] as const;
const placeholders = (value: string) =>
  [...value.matchAll(/\{([^{}]+)\}/g)].map((match) => match[1]).sort();

function validateCopy(copy: Record<string, unknown>) {
  for (const key of phaseKeys) {
    const value = copy[key];
    if (typeof value !== "string" || !value.trim())
      throw new Error(key + ": missing copy");
    if (
      JSON.stringify(placeholders(value)) !==
      JSON.stringify(placeholders(enUS[key]))
    )
      throw new Error(key + ": placeholder mismatch");
  }
}

function validateTree(reference: unknown, candidate: unknown, path = "") {
  if (
    typeof candidate !== typeof reference ||
    Array.isArray(candidate) !== Array.isArray(reference) ||
    (candidate === null) !== (reference === null)
  )
    throw new Error(path + ": type mismatch");
  if (!reference || typeof reference !== "object") return;
  const expected = reference as Record<string, unknown>;
  const actual = candidate as Record<string, unknown>;
  if (
    JSON.stringify(Object.keys(actual).sort()) !==
    JSON.stringify(Object.keys(expected).sort())
  )
    throw new Error(path + ": key mismatch");
  for (const key of Object.keys(expected))
    validateTree(expected[key], actual[key], path + "." + key);
}

describe("combined eighteen-locale description gate", () => {
  it("includes exactly all eighteen locales", () => {
    expect(Object.keys(trees).sort()).toEqual([...locales].sort());
  });

  for (const locale of locales) {
    it(locale + " has translated phase copy and exact interpolation", () => {
      const copy = trees[locale]["rom.json"] as Record<string, unknown>;
      validateCopy(copy);
      if (!locale.startsWith("en_"))
        for (const key of phaseKeys) expect(copy[key]).not.toBe(enUS[key]);
    });
    it(locale + " retains recursive namespace and key parity", () => {
      validateTree(trees.en_US, trees[locale], locale);
    });
  }

  it("rejects missing copy without touching locale sources", () => {
    const copy: Record<string, unknown> = { ...enUS };
    delete copy["description-source-localized"];
    expect(() => validateCopy(copy)).toThrow("missing copy");
  });
  it.each(["{source} ({requestedLanguage})", "{source} ({language}) {source}"])(
    "rejects malformed interpolation %s",
    (value) => {
      expect(() =>
        validateCopy({
          ...enUS,
          "description-source-localized": value,
        }),
      ).toThrow("placeholder mismatch");
    },
  );
  it("rejects missing nested keys", () => {
    expect(() =>
      validateTree(
        { settings: { nested: { label: "Label" } } },
        { settings: { nested: {} } },
      ),
    ).toThrow("key mismatch");
  });
  it("rejects malformed nested value types", () => {
    expect(() =>
      validateTree(
        { settings: { label: "Label" } },
        { settings: { label: {} } },
      ),
    ).toThrow("type mismatch");
  });

  it.each(["check_i18n_locales.py", "check_i18n_sorted.py"])(
    "passes the complete unfiltered repository validator %s",
    (script) => {
      const result = spawnSync("python3", ["src/locales/" + script], {
        cwd: process.cwd(),
        encoding: "utf8",
        timeout: 30_000,
      });
      expect(result.error).toBeUndefined();
      expect(result.status, result.stdout + result.stderr).toBe(0);
    },
  );
});
