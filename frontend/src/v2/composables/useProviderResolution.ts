import type {
  MetadataFieldTarget,
  OperationRequest,
  Provenance,
} from "@/v2/data/contracts";

export const GENERAL_PROVIDER_KEYS = new Set([
  "igdb",
  "steam",
  "ss",
  "moby",
  "launchbox",
  "flashpoint",
  "gamelist",
  "libretro",
]);
export const SPECIFIC_PROVIDER_KEYS = new Set(["ra", "sgdb", "hltb"]);
export const HASH_MATCHER_KEYS = new Set(["hasheous", "playmatch"]);

export interface ProviderOption {
  value: string;
  disabled?: string | boolean;
}

export interface ProviderResolutionInput {
  options: readonly ProviderOption[];
  selected: readonly string[];
  allSelected?: boolean;
  calculateHashes?: boolean;
  hasheousEnabled?: boolean;
  playmatchEnabled?: boolean;
  playmatchAvailable?: boolean;
}

export interface ProviderResolution {
  providers: string[];
  fallbackProviders: string[];
  disabledReasons: Record<string, "requires-hashes" | "requires-igdb">;
  hasheousEnabled: boolean;
  playmatchEnabled: boolean;
}

export interface ProviderContribution {
  provider: string;
  fields: string[];
  locale: string;
  region?: string;
  role: "identity" | "technical" | "localized" | "media";
}

export function normalizeLocale(locale: string): string {
  const parts = locale.trim().replace(/_/g, "-").split("-");
  const language = (parts.shift() ?? "en").toLowerCase();
  const rest = parts.map((part) =>
    part.length === 2 || part.length === 3 ? part.toUpperCase() : part,
  );
  return [language, ...rest].join("-");
}

function unique(values: readonly string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

function enabledOptions(options: readonly ProviderOption[]): string[] {
  return options
    .filter(
      (option) => !option.disabled && !HASH_MATCHER_KEYS.has(option.value),
    )
    .map((option) => option.value);
}

export function resolveProviderSelection(
  input: ProviderResolutionInput,
): ProviderResolution {
  const available = enabledOptions(input.options);
  const selected = input.allSelected ? available : unique(input.selected);
  const providers = selected.filter((provider) => available.includes(provider));
  const disabledReasons: ProviderResolution["disabledReasons"] = {};
  const calculateHashes = input.calculateHashes ?? true;
  const igdbSelected = providers.includes("igdb");
  const hasheousEnabled = Boolean(input.hasheousEnabled && calculateHashes);
  const playmatchEnabled = Boolean(
    input.playmatchEnabled &&
    input.playmatchAvailable !== false &&
    calculateHashes &&
    igdbSelected,
  );

  if (input.selected.includes("ra") && !calculateHashes) {
    disabledReasons.ra = "requires-hashes";
  }
  if (input.playmatchEnabled && !igdbSelected) {
    disabledReasons.playmatch = "requires-igdb";
  }

  return {
    providers: hasheousEnabled ? [...providers, "hasheous"] : providers,
    fallbackProviders: playmatchEnabled ? ["playmatch"] : [],
    disabledReasons,
    hasheousEnabled,
    playmatchEnabled,
  };
}

export interface ProviderContributionInput {
  providers: readonly string[];
  fields: readonly MetadataFieldTarget[];
  metadataLocale: string;
  region?: string;
}

export function resolveProviderContributions(
  input: ProviderContributionInput,
): ProviderContribution[] {
  const locale = normalizeLocale(input.metadataLocale);
  const fields = [...new Set(input.fields.map((field) => field.field))];
  const result: ProviderContribution[] = [];
  for (const provider of unique(input.providers)) {
    const role =
      provider === "igdb"
        ? "identity"
        : provider === "steam"
          ? "localized"
          : "technical";
    result.push({ provider, fields, locale, region: input.region, role });
  }
  return result;
}

export function withActualProviderLocale(
  provenance: Provenance,
  actualLocale: string | undefined,
): Provenance {
  return {
    ...provenance,
    locale: actualLocale ? normalizeLocale(actualLocale) : provenance.locale,
  };
}

export function resolveRequestProviders(
  request: OperationRequest,
): OperationRequest {
  const resolved = resolveProviderSelection({
    options: request.providerPolicy.providers.map((value) => ({ value })),
    selected: request.providerPolicy.providers,
    allSelected: false,
  });
  return {
    ...request,
    metadataLocale: normalizeLocale(request.metadataLocale),
    uiLocale: normalizeLocale(request.uiLocale),
    providerPolicy: {
      ...request.providerPolicy,
      providers: resolved.providers,
      fallbackProviders: unique([
        ...request.providerPolicy.fallbackProviders,
        ...resolved.fallbackProviders,
      ]),
    },
  };
}
