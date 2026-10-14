import type {
  ManualDescriptionRequest,
  ManualDescriptionResponse,
  ManualMetadata,
  SteamMetadataSchema,
} from "@/__generated__";
import romApi from "@/services/api/rom";
import { normalizeLocale } from "@/v2/composables/useProviderResolution";

export interface DescriptionResolutionInput {
  manualMetadata: ManualMetadata | null | undefined;
  steamMetadata: SteamMetadataSchema | null | undefined;
  ssMetadata?: {
    text_variants?: Record<
      string,
      { summary?: string | null } | undefined
    > | null;
  } | null;
  legacySummary: string | null | undefined;
  locale: string;
  providerSummaryIsAuthoritative?: boolean;
}

export function resolveManualDescription({
  manualMetadata,
  steamMetadata,
  ssMetadata,
  legacySummary,
  locale,
  providerSummaryIsAuthoritative = true,
}: DescriptionResolutionInput): string | null {
  const normalizedLocale = normalizeLocale(locale);
  const language = normalizedLocale.split("-", 1)[0];
  const descriptions = manualMetadata?.descriptions ?? {};
  const manualSummary =
    descriptions[normalizedLocale] ?? descriptions[language] ?? null;
  if (manualSummary?.trim()) return manualSummary.trim();

  const manualEnglish =
    descriptions.en ?? descriptions["en-US"] ?? descriptions["en-GB"] ?? null;
  if (manualEnglish?.trim()) return manualEnglish.trim();

  if (providerSummaryIsAuthoritative) {
    const providerSummary = resolveProviderDescription({
      steamMetadata,
      ssMetadata,
      locale: normalizedLocale,
    });
    if (providerSummary) return providerSummary;
    const english = resolveProviderDescription({
      steamMetadata,
      ssMetadata,
      locale: "en",
    });
    if (english) return english;
  }

  return normalizedSummary(legacySummary);
}

export function resolveProviderDescription({
  steamMetadata,
  ssMetadata,
  locale,
}: {
  steamMetadata: SteamMetadataSchema | null | undefined;
  ssMetadata: ProviderMetadata | null | undefined;
  locale: string;
}): string | null {
  const normalizedLocale = normalizeLocale(locale);
  const language = normalizedLocale.split("-", 1)[0];
  const variants = collectProviderVariants(steamMetadata, ssMetadata);
  return normalizedSummary(
    variants[normalizedLocale] ??
      variants[language] ??
      (language === "en" ? (variants["en-US"] ?? variants["en-GB"]) : null),
  );
}

export function useManualDescription() {
  async function updateRomDescription(
    romId: number,
    payload: ManualDescriptionRequest,
  ): Promise<ManualDescriptionResponse> {
    const response = await romApi.updateManualDescription({ romId, payload });
    return response.data;
  }

  async function updateComponentDescription(
    romId: number,
    componentId: number,
    payload: ManualDescriptionRequest,
  ): Promise<ManualDescriptionResponse> {
    const response = await romApi.updatePcComponentManualDescription({
      romId,
      componentId,
      payload,
    });
    return response.data;
  }

  return { updateRomDescription, updateComponentDescription };
}

function normalizedSummary(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

type ProviderMetadata = {
  text_variants?: Record<
    string,
    { summary?: string | null } | undefined
  > | null;
};

function collectProviderVariants(
  steamMetadata: SteamMetadataSchema | null | undefined,
  ssMetadata: ProviderMetadata | null | undefined,
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const variants of [
    steamMetadata?.text_variants,
    ssMetadata?.text_variants,
  ]) {
    if (!variants) continue;
    for (const [locale, variant] of Object.entries(variants)) {
      const summary = normalizedSummary(variant?.summary);
      let normalizedLocale: string;
      try {
        normalizedLocale = normalizeLocale(locale);
      } catch {
        continue;
      }
      if (summary && !result[normalizedLocale]) {
        result[normalizedLocale] = summary;
      }
    }
  }
  return result;
}
