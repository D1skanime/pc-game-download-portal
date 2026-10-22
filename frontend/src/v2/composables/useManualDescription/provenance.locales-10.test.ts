import { describe, expect, it } from "vitest";
import ptBR from "@/locales/pt_BR/rom.json";
import roRO from "@/locales/ro_RO/rom.json";
import ruRU from "@/locales/ru_RU/rom.json";
import { descriptionPresentation } from "./provenance";

const copies = [
  {
    locale: "pt_BR",
    messages: ptBR,
    source: "Fonte: {source} ({language})",
    fallback:
      "Descrição indisponível em {requestedLanguage}. Exibindo a descrição em {language} de {source}.",
    cancel: "Cancelar edição",
  },
  {
    locale: "ro_RO",
    messages: roRO,
    source: "Sursă: {source} ({language})",
    fallback:
      "Descrierea nu este disponibilă în {requestedLanguage}. Se afișează descrierea în {language} de la {source}.",
    cancel: "Anulează editarea",
  },
  {
    locale: "ru_RU",
    messages: ruRU,
    source: "Источник: {source} ({language})",
    fallback:
      "Описание на языке {requestedLanguage} недоступно. Показано описание на языке {language} из источника {source}.",
    cancel: "Отменить редактирование",
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
