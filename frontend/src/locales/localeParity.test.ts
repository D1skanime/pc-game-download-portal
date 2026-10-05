import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const localesRoot = resolve(process.cwd(), "src/locales");

describe("locale namespace parity", () => {
  it("provides storage administration in every supported locale", () => {
    const locales = readdirSync(localesRoot, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort();

    expect(locales.length).toBeGreaterThan(0);
    for (const locale of locales) {
      const path = resolve(localesRoot, locale, "storage.json");
      expect(existsSync(path), locale).toBe(true);
      const messages = JSON.parse(readFileSync(path, "utf8")) as Record<
        string,
        string
      >;
      expect(messages.administration, locale).toEqual(expect.any(String));
      expect(messages.administration.trim().length, locale).toBeGreaterThan(0);
    }
  });
});
