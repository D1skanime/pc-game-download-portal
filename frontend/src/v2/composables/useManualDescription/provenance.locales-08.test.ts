import { describe, expect, it } from "vitest";
import bgBG from "@/locales/bg_BG/rom.json";
import enGB from "@/locales/en_GB/rom.json";
import enUS from "@/locales/en_US/rom.json";
import { descriptionPresentation } from "./provenance";

const copies = [
  {
    locale: "en_US",
    messages: enUS,
    source: "Source: {source} ({language})",
    fallback:
      "{requestedLanguage} description unavailable. Showing {language} from {source}.",
    cancel: "Cancel editing",
  },
  {
    locale: "en_GB",
    messages: enGB,
    source: "Source: {source} ({language})",
    fallback:
      "{requestedLanguage} description unavailable. Showing {language} from {source}.",
    cancel: "Cancel editing",
  },
  {
    locale: "bg_BG",
    messages: bgBG,
    source: "Източник: {source} ({language})",
    fallback:
      "Няма описание на {requestedLanguage}. Показва се описание на {language} от {source}.",
    cancel: "Отказ от редактирането",
  },
];

const placeholders = (value: string) =>
  [...value.matchAll(/\{([^{}]+)\}/g)].map((match) => match[1]).sort();

describe.each(copies)(
  "description provenance locale $locale",
  ({ messages, source, fallback, cancel }) => {
    const copy: Record<string, string> = messages;
    it("contains approved actual translations and explicit fallback wording", () => {
      expect(copy["description-source-localized"]).toBe(source);
      expect(copy["description-language-fallback"]).toBe(fallback);
      expect(copy["description-cancel"]).toBe(cancel);
      for (const value of [source, fallback, cancel])
        expect(value.trim()).not.toBe("");
    });

    it("matches the shared formatter interpolation contract without duplicate prefixes", () => {
      const resolution = {
        text: "Stored description",
        requestedLocale: "de",
        resolvedLocale: "en",
        source: "steam" as const,
        match: "english_fallback" as const,
      };
      for (const match of ["exact", "base", "english_fallback"] as const) {
        const presentation = descriptionPresentation(
          { ...resolution, match },
          {
            source: "Steam",
            language: "English",
            requestedLanguage: "German",
          },
        );
        const template = copy[presentation.key.replace("rom.", "")];
        expect(typeof template).toBe("string");
        expect(placeholders(template ?? "")).toEqual(
          Object.keys(presentation.params).sort(),
        );
        expect((template ?? "").match(/\{source\}/g)).toHaveLength(1);
      }
      expect(placeholders(copy["description-cancel"])).toEqual([]);
    });

    it("keeps locale keys sorted and preserves legacy keys for combined cleanup", () => {
      expect(Object.keys(copy)).toEqual(Object.keys(copy).sort());
      expect(copy["description-source-fallback"]).toBeTruthy();
      expect(copy["description-fallback-preview"]).toBeTruthy();
    });
  },
);
