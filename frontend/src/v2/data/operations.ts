import { normalizeLocale } from "@/v2/composables/useProviderResolution";
import type {
  LibraryProfile,
  OperationKind,
  OperationRequest,
  OperationScope,
  ScanType,
} from "./contracts";

export interface LibraryScanRequestInput {
  operationId: string;
  kind: OperationKind;
  scope: OperationScope;
  profiles: LibraryProfile[];
  uiLocale: string;
  metadataLocale: string;
  providers: string[];
  playmatchEnabled: boolean;
  launchboxRemoteEnabled: boolean;
  scanType: ScanType;
  metadataOnly?: boolean;
  mediaOnly?: boolean;
}

export function buildLibraryScanRequest(
  input: LibraryScanRequestInput,
): OperationRequest {
  return {
    operationId: input.operationId,
    kind: input.kind,
    scope: input.scope,
    profiles: input.profiles,
    uiLocale: input.uiLocale,
    metadataLocale: input.metadataLocale,
    providerPolicy: {
      providers: input.providers,
      fallbackProviders: input.playmatchEnabled ? ["playmatch"] : [],
      allowUnexpectedLocale: false,
      launchboxRemoteEnabled: input.launchboxRemoteEnabled,
    },
    metadataPolicy: {
      mode: input.scanType === "update" ? "provider-replace" : "missing-only",
      fields: [],
    },
    mediaPolicy: { mode: "missing-only", targets: [] },
    capabilities: {
      discovery: !input.mediaOnly,
      creation: !input.mediaOnly,
      metadata: !input.mediaOnly,
      media: true,
      fileMutation: false,
      pcDlc: !input.mediaOnly,
      preview: true,
      retry: true,
      resume: true,
    },
    preview: false,
    permissions: { scopes: ["tasks:run"] },
    idempotencyKey: input.operationId,
    jobId: input.operationId,
    retry: { maxAttempts: 3 },
    execution: {
      maxConcurrency: 1,
      cancelable: true,
      resumable: true,
    },
    scanType: input.scanType,
    ...(input.metadataOnly || input.mediaOnly
      ? {
          metadataOnly: input.metadataOnly === true,
          mediaOnly: input.mediaOnly === true,
          metadataPolicy: input.metadataOnly
            ? {
                mode:
                  input.scanType === "update"
                    ? "provider-replace"
                    : "missing-only",
                fields: [],
              }
            : { mode: "none", fields: [] },
          mediaPolicy: input.mediaOnly
            ? { mode: "missing-only", targets: [] }
            : { mode: "none", targets: [] },
        }
      : {}),
  };
}

export interface LegacyScanOptions {
  platforms: number[];
  type: ScanType;
  roms_ids: number[];
  platform_fs_slugs: string[];
  apis: string[];
  launchbox_remote_enabled: boolean;
  playmatch_enabled: boolean;
  metadata_locale?: string;
  metadata_only?: boolean;
  media_only?: boolean;
}

export class OperationTranslationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "OperationTranslationError";
  }
}

function uniqueNumbers(values: number[]): number[] {
  return [...new Set(values)].filter(Number.isInteger);
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()))].filter(Boolean);
}

function sortedUniqueNumbers(values: number[]): number[] {
  return [...new Set(values)].filter(Number.isInteger).sort((a, b) => a - b);
}

function sortedUniqueStrings(values: string[]): string[] {
  return uniqueStrings(values).sort((a, b) => a.localeCompare(b));
}

export interface MediaScanPlatformIdentity {
  fsSlug: string;
  platformId?: number;
}

export function resolveMediaOnlyScope(
  selectedFsSlugs: string[],
  platforms: readonly MediaScanPlatformIdentity[],
): OperationScope {
  const slugs = sortedUniqueStrings(selectedFsSlugs);
  if (slugs.length === 0) return { kind: "library" };

  const platformIds = slugs.map(
    (slug) =>
      platforms.find((platform) => platform.fsSlug === slug)?.platformId,
  );
  if (platformIds.some((id) => !Number.isInteger(id))) {
    throw new OperationTranslationError(
      "Media-only scans require selected platforms to already exist in the library.",
    );
  }
  return {
    kind: "platform",
    platformIds: sortedUniqueNumbers(platformIds as number[]),
  };
}

export function operationItemIds(request: OperationRequest): string[] {
  switch (request.scope.kind) {
    case "library": {
      const platformIds = sortedUniqueNumbers(
        request.profiles
          .map((profile) => profile.platformId)
          .filter((id): id is number => id !== undefined),
      );
      const slugs = sortedUniqueStrings(
        request.profiles
          .map((profile) => profile.platformFsSlug)
          .filter((slug): slug is string => slug !== undefined),
      );
      const identities = [
        ...platformIds.map((id) => "library:platform:" + id),
        ...slugs.map((slug) => "library:filesystem:" + slug),
      ];
      return identities.length > 0 ? identities : ["library"];
    }
    case "platform":
      return sortedUniqueNumbers(request.scope.platformIds).map(
        (id) => "platform:" + id,
      );
    case "rom":
      return sortedUniqueNumbers(request.scope.romIds).map((id) => "rom:" + id);
    case "component":
      return [
        "component:" + request.scope.romId + ":" + request.scope.componentId,
      ];
    case "filesystem":
      return sortedUniqueStrings(request.scope.platformFsSlugs).map(
        (slug) => "filesystem:" + slug,
      );
  }
}

function profilePlatformIds(request: OperationRequest): number[] {
  return uniqueNumbers(
    request.profiles
      .map((profile) => profile.platformId)
      .filter((id): id is number => id !== undefined),
  );
}

function profileFilesystemSlugs(request: OperationRequest): string[] {
  return uniqueStrings(
    request.profiles
      .map((profile) => profile.platformFsSlug)
      .filter((slug): slug is string => slug !== undefined),
  );
}

function assertScopeIsExecutable(scope: OperationScope): void {
  if (scope.kind === "platform" && scope.platformIds.length === 0) {
    throw new OperationTranslationError(
      "A platform operation needs at least one platform id.",
    );
  }
  if (scope.kind === "rom" && scope.romIds.length === 0) {
    throw new OperationTranslationError(
      "A ROM operation needs at least one ROM id.",
    );
  }
  if (scope.kind === "filesystem" && scope.platformFsSlugs.length === 0) {
    throw new OperationTranslationError(
      "A filesystem operation needs at least one platform slug.",
    );
  }
  if (scope.kind === "component") {
    throw new OperationTranslationError(
      "Component operations require the PC/DLC matcher API and cannot use the scan socket.",
    );
  }
}

export function normalizeOperationRequest(
  request: OperationRequest,
): OperationRequest {
  assertScopeIsExecutable(request.scope);
  const metadataOnly = request.metadataOnly === true;
  const mediaOnly = request.mediaOnly === true;
  if (metadataOnly && mediaOnly) {
    throw new OperationTranslationError(
      "An operation cannot enable metadata-only and media-only intent together.",
    );
  }
  if (metadataOnly && request.mediaPolicy.mode !== "none") {
    throw new OperationTranslationError(
      "Metadata-only intent requires a none media policy.",
    );
  }
  if (mediaOnly && request.metadataPolicy.mode !== "none") {
    throw new OperationTranslationError(
      "Media-only intent requires a none metadata policy.",
    );
  }
  if (request.capabilities.fileMutation) {
    throw new OperationTranslationError(
      "Scan operations cannot mutate source files.",
    );
  }
  if (request.preview && !request.capabilities.preview) {
    throw new OperationTranslationError(
      "Preview mode requires the preview capability.",
    );
  }
  if (!request.operationId || !request.idempotencyKey || !request.jobId) {
    throw new OperationTranslationError(
      "Operation, idempotency, and job identifiers are required.",
    );
  }
  const maxConcurrency = Math.max(
    1,
    Math.min(16, Math.floor(request.execution.maxConcurrency)),
  );
  return {
    ...request,
    ...(metadataOnly || mediaOnly
      ? { metadataOnly, mediaOnly }
      : { metadataOnly: undefined, mediaOnly: undefined }),
    uiLocale: normalizeLocale(request.uiLocale),
    metadataLocale: normalizeLocale(request.metadataLocale),
    execution: {
      ...request.execution,
      maxConcurrency,
      resumable:
        request.execution.resumable && Boolean(request.capabilities.resume),
    },
    providerPolicy: {
      ...request.providerPolicy,
      providers: uniqueStrings(request.providerPolicy.providers),
      fallbackProviders: uniqueStrings(
        request.providerPolicy.fallbackProviders,
      ),
      region: request.providerPolicy.region?.trim() || undefined,
    },
  };
}

function scopeOptions(
  request: OperationRequest,
): Pick<LegacyScanOptions, "platforms" | "roms_ids" | "platform_fs_slugs"> {
  switch (request.scope.kind) {
    case "library":
      return {
        platforms: profilePlatformIds(request),
        roms_ids: [],
        platform_fs_slugs: profileFilesystemSlugs(request),
      };
    case "platform":
      return {
        platforms: uniqueNumbers(request.scope.platformIds),
        roms_ids: [],
        platform_fs_slugs: profileFilesystemSlugs(request),
      };
    case "rom":
      return {
        platforms: profilePlatformIds(request),
        roms_ids: uniqueNumbers(request.scope.romIds),
        platform_fs_slugs: profileFilesystemSlugs(request),
      };
    case "filesystem":
      return {
        platforms: profilePlatformIds(request),
        roms_ids: [],
        platform_fs_slugs: uniqueStrings(request.scope.platformFsSlugs),
      };
    case "component":
      throw new OperationTranslationError(
        "Component operations require the PC/DLC matcher API and cannot use the scan socket.",
      );
  }
}

function assertNever(value: never): never {
  throw new OperationTranslationError(
    `Unsupported operation scope: ${String(value)}`,
  );
}

export function toLegacyScanOptions(
  input: OperationRequest,
): LegacyScanOptions {
  const request = normalizeOperationRequest(input);
  const scope = scopeOptions(request);
  const scanType = request.mediaOnly
    ? "update"
    : (request.scanType ??
      (request.kind === "discovery" ? "new_platforms" : "quick"));

  return {
    ...scope,
    type: scanType,
    apis: uniqueStrings([
      ...request.providerPolicy.providers,
      ...request.providerPolicy.fallbackProviders,
    ]),
    launchbox_remote_enabled:
      request.providerPolicy.launchboxRemoteEnabled ??
      request.providerPolicy.providers.includes("launchbox"),
    playmatch_enabled:
      request.providerPolicy.providers.includes("playmatch") ||
      request.providerPolicy.fallbackProviders.includes("playmatch"),
    metadata_locale: request.metadataLocale,
    ...(request.metadataOnly !== undefined || request.mediaOnly !== undefined
      ? {
          metadata_only: request.metadataOnly === true,
          media_only: request.mediaOnly === true,
        }
      : {}),
  };
}
