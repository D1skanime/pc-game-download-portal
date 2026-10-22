import { describe, expect, it } from "vitest";
import frFR from "@/locales/fr_FR/rom.json";
import huHU from "@/locales/hu_HU/rom.json";
import itIT from "@/locales/it_IT/rom.json";
import jaJP from "@/locales/ja_JP/rom.json";
import koKR from "@/locales/ko_KR/rom.json";
import plPL from "@/locales/pl_PL/rom.json";
import { descriptionPresentation } from "./provenance";

const copies = [
  {
    locale: "fr_FR",
    messages: frFR,
    source: "Source : {source} ({language})",
    fallback:
      "Description indisponible en {requestedLanguage}. Affichage de la description en {language} de {source}.",
    cancel: "Annuler les modifications",
  },
  {
    locale: "hu_HU",
    messages: huHU,
    source: "Forrás: {source} ({language})",
    fallback:
      "Nincs leírás ezen a nyelven: {requestedLanguage}. A megjelenített leírás nyelve: {language}, forrása: {source}.",
    cancel: "Szerkesztés megszakítása",
  },
  {
    locale: "it_IT",
    messages: itIT,
    source: "Fonte: {source} ({language})",
    fallback:
      "Descrizione non disponibile in {requestedLanguage}. Viene mostrata la descrizione in {language} da {source}.",
    cancel: "Annulla modifiche",
  },
  {
    locale: "ja_JP",
    messages: jaJP,
    source: "出典: {source}（{language}）",
    fallback:
      "{requestedLanguage}の説明はありません。{source}の{language}の説明を表示しています。",
    cancel: "編集をキャンセル",
  },
  {
    locale: "ko_KR",
    messages: koKR,
    source: "출처: {source} ({language})",
    fallback:
      "{requestedLanguage} 설명이 없습니다. {source}의 {language} 설명을 표시합니다.",
    cancel: "편집 취소",
  },
  {
    locale: "pl_PL",
    messages: plPL,
    source: "Źródło: {source} ({language})",
    fallback:
      "Opis w języku {requestedLanguage} jest niedostępny. Wyświetlany jest opis w języku {language} ze źródła {source}.",
    cancel: "Anuluj edycję",
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
