import type { OperationRequest, OperationScope, ScanType } from "./contracts";

export interface LegacyScanOptions {
  platforms: number[];
  type: ScanType;
  roms_ids: number[];
  platform_fs_slugs: string[];
  apis: string[];
  launchbox_remote_enabled: boolean;
  playmatch_enabled: boolean;
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
  return {
    ...request,
    providerPolicy: {
      ...request.providerPolicy,
      providers: uniqueStrings(request.providerPolicy.providers),
      fallbackProviders: uniqueStrings(
        request.providerPolicy.fallbackProviders,
      ),
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
  const scanType =
    request.scanType ??
    (request.kind === "discovery" ? "new_platforms" : "quick");

  return {
    ...scope,
    type: scanType,
    apis: uniqueStrings([
      ...request.providerPolicy.providers,
      ...request.providerPolicy.fallbackProviders,
    ]),
    launchbox_remote_enabled:
      request.providerPolicy.providers.includes("launchbox"),
    playmatch_enabled:
      request.providerPolicy.providers.includes("playmatch") ||
      request.providerPolicy.fallbackProviders.includes("playmatch"),
  };
}
