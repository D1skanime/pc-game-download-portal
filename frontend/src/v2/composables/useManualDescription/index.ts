import type {
  ManualDescriptionRequest,
  ManualDescriptionResponse,
  ManualMetadata,
  SteamMetadataSchema,
} from "@/__generated__";
import api from "@/services/api";
import { normalizeLocale } from "@/v2/composables/useProviderResolution";

export interface DescriptionResolutionInput {
  manualMetadata: ManualMetadata | null | undefined;
  steamMetadata: SteamMetadataSchema | null | undefined;
  legacySummary: string | null | undefined;
  locale: string;
  providerSummaryIsAuthoritative?: boolean;
}

export function resolveManualDescription({
  manualMetadata,
  steamMetadata,
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

  const fallbackSummary = normalizedSummary(legacySummary);
  if (!providerSummaryIsAuthoritative) return fallbackSummary;

  const variants = steamMetadata?.text_variants;
  if (variants) {
    const providerSummary = normalizedSummary(
      variants[normalizedLocale]?.summary ?? variants[language]?.summary,
    );
    if (providerSummary) return providerSummary;
    const english = normalizedSummary(variants.en?.summary);
    if (english) return english;
  }

  return fallbackSummary;
}

export function useManualDescription() {
  async function updateRomDescription(
    romId: number,
    payload: ManualDescriptionRequest,
  ): Promise<ManualDescriptionResponse> {
    const response = await api.put<ManualDescriptionResponse>(
      `/roms/${romId}/description`,
      payload,
    );
    return response.data;
  }

  async function updateComponentDescription(
    romId: number,
    componentId: number,
    payload: ManualDescriptionRequest,
  ): Promise<ManualDescriptionResponse> {
    const response = await api.put<ManualDescriptionResponse>(
      `/roms/${romId}/pc-components/${componentId}/description`,
      payload,
    );
    return response.data;
  }

  return { updateRomDescription, updateComponentDescription };
}

function normalizedSummary(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
