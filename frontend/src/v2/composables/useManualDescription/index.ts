import type {
  ManualDescriptionRequest,
  ManualDescriptionResponse,
  ManualMetadata,
  SteamMetadataSchema,
} from "@/__generated__";
import {
  descriptionLocale,
  descriptionText,
  providerCandidates,
  type DescriptionCandidate,
  type DescriptionProvider,
  type DescriptionResolution,
  type ProviderMetadata,
} from "@/v2/composables/useManualDescription/provenance";
import romApi from "@/v2/data/adapters/legacy/services/api/rom";

export type {
  DescriptionProvider,
  DescriptionResolution,
} from "@/v2/composables/useManualDescription/provenance";

export interface LocalizedDescriptionInput {
  manualMetadata?: ManualMetadata | null;
  steamMetadata?: SteamMetadataSchema | null;
  ssMetadata?: ProviderMetadata | null;
  locale?: string | null;
  provider: DescriptionProvider | null;
}

function manualCandidates(
  metadata: ManualMetadata | null | undefined,
): DescriptionCandidate[] {
  return Object.entries(metadata?.descriptions ?? {}).flatMap(
    ([tag, value]) => {
      const locale = descriptionLocale(tag);
      const text = descriptionText(value);
      return locale && text
        ? [{ locale, text, source: "manual" as const }]
        : [];
    },
  );
}

function selectDescription(
  locale: string | null | undefined,
  manual: DescriptionCandidate[],
  providers: DescriptionCandidate[],
): DescriptionResolution {
  const requestedLocale = descriptionLocale(locale) ?? "en";
  const base = requestedLocale.split("-", 1)[0];
  const requested = [requestedLocale, base];
  const english = ["en", "en-US", "en-GB"];
  for (const [candidates, locales] of [
    [manual, requested],
    [providers, requested],
    [manual, english],
    [providers, english],
  ] as const) {
    for (const tag of locales) {
      const candidate = candidates.find((value) => value.locale === tag);
      if (!candidate) continue;
      return {
        text: candidate.text,
        requestedLocale,
        resolvedLocale: candidate.locale,
        source: candidate.source,
        match:
          tag === requestedLocale
            ? "exact"
            : tag === base || base === "en"
              ? "base"
              : "english_fallback",
      };
    }
  }
  return {
    text: null,
    requestedLocale,
    resolvedLocale: null,
    source: "none",
    match: "empty",
  };
}

export function resolveDescription(
  input: LocalizedDescriptionInput,
): DescriptionResolution {
  const providers =
    input.provider === "steam"
      ? providerCandidates(input.steamMetadata, "steam")
      : input.provider === "screenscraper"
        ? providerCandidates(input.ssMetadata, "screenscraper")
        : [];
  return selectDescription(
    input.locale,
    manualCandidates(input.manualMetadata),
    providers,
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
