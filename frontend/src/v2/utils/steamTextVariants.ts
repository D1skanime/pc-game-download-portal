import type {
  SteamMetadataSchema,
  SteamTextVariantSchema,
} from "@/__generated__";

interface ResolveSteamTextVariantOptions {
  steamMetadata: SteamMetadataSchema | null | undefined;
  legacySummary: string | null | undefined;
  locale: string;
  steamSummaryIsAuthoritative: boolean;
}

export function getLocaleBaseTag(locale: string): string {
  return locale.trim().toLowerCase().split(/[-_]/, 1)[0] ?? "";
}

export function resolveSteamTextVariant({
  steamMetadata,
  legacySummary,
  locale,
  steamSummaryIsAuthoritative,
}: ResolveSteamTextVariantOptions): string | null {
  const fallbackSummary = normalizedSummary(legacySummary);
  if (!steamSummaryIsAuthoritative) return fallbackSummary;

  const variants = steamMetadata?.text_variants;
  if (variants) {
    const selectedSummary = variantSummary(variants[getLocaleBaseTag(locale)]);
    if (selectedSummary) return selectedSummary;

    const englishSummary = variantSummary(variants.en);
    if (englishSummary) return englishSummary;
  }

  return fallbackSummary;
}

function variantSummary(
  variant: SteamTextVariantSchema | undefined,
): string | null {
  if (!variant?.source_language.trim()) return null;
  return normalizedSummary(variant.summary);
}

function normalizedSummary(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
