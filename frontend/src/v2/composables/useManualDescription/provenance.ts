import type { SteamTextVariantSchema } from "@/__generated__";
import { normalizeLocale } from "@/v2/composables/useProviderResolution";

export type DescriptionProvider = "steam" | "screenscraper";
export type DescriptionSource = "manual" | DescriptionProvider | "none";
export interface DescriptionResolution {
  text: string | null;
  requestedLocale: string;
  resolvedLocale: string | null;
  source: DescriptionSource;
  match: "exact" | "base" | "english_fallback" | "empty";
}
export interface ProviderMetadata {
  text_variants?: Record<
    string,
    Partial<SteamTextVariantSchema> | undefined
  > | null;
}
export interface DescriptionCandidate {
  text: string;
  locale: string;
  source: Exclude<DescriptionSource, "none">;
}

const steamLanguages: Record<string, string> = {
  en: "english",
  fr: "french",
  de: "german",
  ru: "russian",
  pt: "brazilian",
  ro: "romanian",
  es: "spanish",
  zh: "schinese",
  ko: "koreana",
  ja: "japanese",
  it: "italian",
  pl: "polish",
  cs: "czech",
  hu: "hungarian",
  bg: "bulgarian",
  tr: "turkish",
};

export function descriptionLocale(value: unknown): string | null {
  if (
    typeof value !== "string" ||
    value.trim().length > 35 ||
    !/^[a-z]{2,3}(?:[-_][a-z0-9]{2,8})*$/i.test(value.trim())
  )
    return null;
  return normalizeLocale(value);
}

export function descriptionText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function providerCandidates(
  metadata: ProviderMetadata | null | undefined,
  source: DescriptionProvider,
): DescriptionCandidate[] {
  const candidates: DescriptionCandidate[] = [];
  for (const [tag, variant] of Object.entries(metadata?.text_variants ?? {})) {
    const locale = descriptionLocale(tag);
    const base = locale?.split("-", 1)[0];
    const text = descriptionText(variant?.summary);
    if (!locale || !base || !steamLanguages[base] || !text || !variant)
      continue;
    if (source === "steam") {
      const expected = steamLanguages[base];
      if (
        variant.source_language !== expected ||
        (variant.requested_language != null &&
          variant.requested_language !== expected) ||
        (variant.language_evidence != null &&
          variant.language_evidence !== "provider_slot")
      )
        continue;
    } else if (descriptionLocale(variant.source_language) !== locale) continue;
    candidates.push({ text, locale, source });
  }
  return candidates;
}

export function descriptionPresentation(
  resolution: DescriptionResolution,
  labels: { source: string; language: string; requestedLanguage: string },
): { key: string; params: Record<string, string> } {
  if (resolution.match === "empty")
    return { key: "rom.description-source-empty", params: {} };
  if (resolution.match === "english_fallback")
    return {
      key: "rom.description-language-fallback",
      params: {
        requestedLanguage: labels.requestedLanguage,
        language: labels.language,
        source: labels.source,
      },
    };
  return {
    key: "rom.description-source-localized",
    params: { source: labels.source, language: labels.language },
  };
}
