import { describe, expect, it } from "vitest";
import { useMetadataMatchLanguage } from "./index";

describe("metadata match language generations", () => {
  it.each(["de-CH", "fr", "en"])(
    "retains immutable %s language until a new search",
    (locale) => {
      const match = useMetadataMatchLanguage();
      const capture = match.begin(locale);
      expect(Object.isFrozen(capture)).toBe(true);
      expect(match.accept(capture)).toBe(true);
      expect(match.accepted.value?.metadataLocale).toBe(locale);
      const next = match.begin("fr-CH");
      expect(match.accept(capture)).toBe(false);
      expect(match.accept(next)).toBe(true);
      expect(match.accepted.value?.metadataLocale).toBe("fr-CH");
    },
  );

  it.each([null, undefined, "", "  "])(
    "defaults unset preference %s to English",
    (locale) => {
      expect(useMetadataMatchLanguage().begin(locale).metadataLocale).toBe(
        "en",
      );
    },
  );

  it("rejects old generations after closing or changing entity", () => {
    const match = useMetadataMatchLanguage();
    const first = match.begin("de");
    match.reset();
    expect(match.isCurrent(first)).toBe(false);
    expect(match.accept(first)).toBe(false);
    expect(match.accepted.value).toBeNull();
  });
});
