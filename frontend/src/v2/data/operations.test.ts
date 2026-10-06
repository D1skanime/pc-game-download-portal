import { describe, expect, it } from "vitest";
import type { OperationRequest } from "./contracts";
import {
  OperationTranslationError,
  buildLibraryScanRequest,
  normalizeOperationRequest,
  operationItemIds,
  toLegacyScanOptions,
} from "./operations";

const baseRequest = (
  overrides: Partial<OperationRequest> = {},
): OperationRequest => ({
  operationId: "op-1",
  kind: "metadata-refresh",
  scope: { kind: "platform", platformIds: [7, 7] },
  profiles: [
    {
      rootId: "library",
      mappingId: 12,
      mappingRevision: 3,
      layout: "classic-rom",
      itemKind: "game",
      platformId: 7,
      platformFsSlug: "snes",
    },
  ],
  uiLocale: "de-DE",
  metadataLocale: "en-US",
  providerPolicy: {
    providers: ["igdb", "launchbox", "igdb"],
    fallbackProviders: ["playmatch"],
    allowUnexpectedLocale: false,
  },
  metadataPolicy: { mode: "missing-only", fields: [] },
  mediaPolicy: { mode: "missing-only", targets: [] },
  capabilities: {
    discovery: false,
    creation: false,
    metadata: true,
    media: true,
    fileMutation: false,
    pcDlc: false,
    preview: false,
    retry: true,
    resume: true,
  },
  preview: false,
  permissions: { scopes: ["tasks:run"] },
  idempotencyKey: "idem-1",
  jobId: "job-1",
  execution: { maxConcurrency: 1, cancelable: true, resumable: true },
  ...overrides,
});

describe("operation compatibility translation", () => {
  it("builds a dialog request that preserves the legacy scan payload semantics", () => {
    const request = buildLibraryScanRequest({
      operationId: "refresh-platform-7",
      kind: "metadata-refresh",
      scope: { kind: "platform", platformIds: [7] },
      profiles: [],
      uiLocale: "de-DE",
      metadataLocale: "en-US",
      providers: ["igdb", "launchbox", "hasheous"],
      playmatchEnabled: true,
      launchboxRemoteEnabled: false,
      scanType: "complete",
    });

    expect(toLegacyScanOptions(request)).toEqual({
      platforms: [7],
      type: "complete",
      roms_ids: [],
      platform_fs_slugs: [],
      metadata_locale: "en-US",
      apis: ["igdb", "launchbox", "hasheous", "playmatch"],
      launchbox_remote_enabled: false,
      playmatch_enabled: true,
    });
  });

  it("maps classic platform scans to the existing socket payload", () => {
    expect(toLegacyScanOptions(baseRequest())).toEqual({
      platforms: [7],
      type: "quick",
      roms_ids: [],
      platform_fs_slugs: ["snes"],
      metadata_locale: "en-US",
      apis: ["igdb", "launchbox", "playmatch"],
      launchbox_remote_enabled: true,
      playmatch_enabled: true,
    });
  });

  it("keeps PC nested ROM identity and provider options intact", () => {
    const request = baseRequest({
      kind: "discovery",
      scope: { kind: "rom", romIds: [41, 41] },
      profiles: [
        {
          rootId: "pc",
          mappingId: 19,
          mappingRevision: 8,
          layout: "pc-nested",
          itemKind: "game",
          platformId: 3,
          platformFsSlug: "windows",
        },
      ],
      providerPolicy: {
        providers: ["igdb"],
        fallbackProviders: [],
        allowUnexpectedLocale: true,
      },
    });

    expect(toLegacyScanOptions(request)).toMatchObject({
      platforms: [3],
      type: "new_platforms",
      roms_ids: [41],
      platform_fs_slugs: ["windows"],
      apis: ["igdb"],
      launchbox_remote_enabled: false,
      playmatch_enabled: false,
    });
  });

  it("rejects empty destructive scopes and source-file mutation", () => {
    expect(() =>
      toLegacyScanOptions(baseRequest({ scope: { kind: "rom", romIds: [] } })),
    ).toThrow(OperationTranslationError);
    expect(() =>
      normalizeOperationRequest(
        baseRequest({
          capabilities: { ...baseRequest().capabilities, fileMutation: true },
        }),
      ),
    ).toThrow("cannot mutate source files");
  });

  it("derives deterministic item identities from sorted scope values", () => {
    expect(
      operationItemIds(
        baseRequest({ scope: { kind: "rom", romIds: [42, 41, 42] } }),
      ),
    ).toEqual(["rom:41", "rom:42"]);
    expect(
      operationItemIds(
        baseRequest({
          scope: { kind: "filesystem", platformFsSlugs: ["zeta", "alpha"] },
        }),
      ),
    ).toEqual(["filesystem:alpha", "filesystem:zeta"]);
    expect(
      operationItemIds(
        baseRequest({ scope: { kind: "library" }, profiles: [] }),
      ),
    ).toEqual(["library"]);
  });

  it("rejects component operations instead of dropping component identity", () => {
    expect(() =>
      toLegacyScanOptions(
        baseRequest({
          scope: {
            kind: "component",
            romId: 41,
            componentId: 9,
            componentKind: "dlc",
          },
        }),
      ),
    ).toThrow("PC/DLC matcher API");
  });
});
