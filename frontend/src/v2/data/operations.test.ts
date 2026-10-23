import { describe, expect, it } from "vitest";
import type { OperationRequest, ScanType, OperationScope } from "./contracts";
import {
  OperationTranslationError,
  buildLibraryScanRequest,
  normalizeOperationRequest,
  operationItemIds,
  resolveMediaOnlyScope,
  toLegacyScanOptions,
  toScanOperationRequest,
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
  it("preserves explicit collection promotion through the typed request builder", () => {
    const collectionPromotion = {
      parent_rom_id: 41,
      mapping_id: 12,
      expected_revision: 3,
      parent_relative_path: "Castlevania",
      selected_child_relative_path: "Castlevania/Belmonts.Curse",
    };
    const request = buildLibraryScanRequest({
      operationId: "collection-selection",
      kind: "discovery",
      scope: {
        kind: "filesystem",
        platformFsSlugs: ["win"],
        relativePaths: {
          win: collectionPromotion.selected_child_relative_path,
        },
      },
      profiles: [],
      uiLocale: "de-DE",
      metadataLocale: "en-US",
      providers: [],
      playmatchEnabled: false,
      launchboxRemoteEnabled: false,
      scanType: "quick",
      collectionPromotion,
    });
    expect(normalizeOperationRequest(request).collectionPromotion).toEqual(
      collectionPromotion,
    );
    expect(toScanOperationRequest(request)).toMatchObject({
      collection_promotion: collectionPromotion,
      filesystem_scope_paths: { win: "Castlevania/Belmonts.Curse" },
    });
    expect(toLegacyScanOptions(request)).not.toHaveProperty(
      "collection_promotion",
    );
  });

  it("does not infer collection promotion from generic filesystem scope", () => {
    const request = baseRequest({
      scope: {
        kind: "filesystem",
        platformFsSlugs: ["win"],
        relativePaths: { win: "Castlevania/Belmonts.Curse" },
      },
    });
    expect(toScanOperationRequest(request)).not.toHaveProperty(
      "collection_promotion",
    );
  });

  it("serializes the backend request without replacing the reconciliation key", () => {
    const input = baseRequest({
      scope: {
        kind: "filesystem",
        platformFsSlugs: ["win"],
        relativePaths: { win: "Games/Spiel 日本" },
      },
      scanType: "full",
    });
    const payload = toScanOperationRequest(input);
    expect(payload).toEqual({
      ...toLegacyScanOptions(input),
      type: "complete",
      request_key: "idem-1",
    });
    expect(toScanOperationRequest(normalizeOperationRequest(input))).toEqual(
      payload,
    );
    expect(payload.filesystem_scope_paths).toEqual({ win: "Games/Spiel 日本" });
    expect(payload.apis).toEqual(["igdb", "launchbox", "playmatch"]);
    expect(payload).not.toHaveProperty("operationId");
    expect(payload).not.toHaveProperty("jobId");
  });

  it("adapts media and metadata intent to the generated backend contract", () => {
    expect(
      toScanOperationRequest(baseRequest({ scanType: "media" })),
    ).toMatchObject({
      type: "update",
      metadata_only: false,
      media_only: true,
    });
    expect(
      toScanOperationRequest(
        baseRequest({
          metadataOnly: true,
          mediaPolicy: { mode: "none", targets: [] },
        }),
      ),
    ).toMatchObject({
      metadata_only: true,
      media_only: false,
    });
    expect(
      toScanOperationRequest(
        baseRequest({
          mediaOnly: true,
          metadataPolicy: { mode: "none", fields: [] },
        }),
      ),
    ).toMatchObject({
      type: "update",
      metadata_only: false,
      media_only: true,
    });
    expect(() =>
      toScanOperationRequest(baseRequest({ preview: true })),
    ).toThrow("Preview");
  });

  it("retains the original request identity through repeated normalization", () => {
    const original = baseRequest();
    const normalized = normalizeOperationRequest(original);
    expect(normalizeOperationRequest(normalized)).toEqual(normalized);
    expect(normalized.idempotencyKey).toBe(original.idempotencyKey);
    expect(normalized.operationId).toBe(original.operationId);
    expect(normalized.jobId).toBe(original.jobId);
    expect(original.providerPolicy.providers).toEqual([
      "igdb",
      "launchbox",
      "igdb",
    ]);
  });

  it.each(["A-key", "../key", "key:resume", " key", "a".repeat(97)])(
    "rejects a request key outside the backend identity grammar: %s",
    (idempotencyKey) => {
      expect(() =>
        normalizeOperationRequest(baseRequest({ idempotencyKey })),
      ).toThrow(OperationTranslationError);
    },
  );

  it.each(["operationId", "jobId"] as const)(
    "bounds local %s independently of confirmed server lineage",
    (field) => {
      expect(() =>
        normalizeOperationRequest(baseRequest({ [field]: "x".repeat(129) })),
      ).toThrow(OperationTranslationError);
    },
  );

  it("preserves all policy fields and mapped revisions during normalization", () => {
    const request = baseRequest({
      scope: {
        kind: "filesystem",
        platformFsSlugs: ["win"],
        relativePaths: { win: "Games/Spiel 日本" },
      },
      providerPolicy: {
        providers: ["igdb", "steam"],
        fallbackProviders: ["playmatch"],
        allowUnexpectedLocale: true,
        launchboxRemoteEnabled: false,
        region: " EU ",
      },
      metadataPolicy: {
        mode: "provider-replace",
        fields: [{ field: "summary", locale: "de-DE" }],
      },
      mediaPolicy: {
        mode: "missing-only",
        targets: [{ role: "cover", ownership: "manual" }],
      },
    });
    const result = normalizeOperationRequest(request);
    expect(result.scope).toEqual(request.scope);
    expect(result.profiles).toEqual(request.profiles);
    expect(result.metadataPolicy).toEqual(request.metadataPolicy);
    expect(result.mediaPolicy).toEqual(request.mediaPolicy);
    expect(result.providerPolicy).toEqual({
      ...request.providerPolicy,
      region: "EU",
    });
  });

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
      metadata_locale: "de-DE",
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

  it("preserves a selected filesystem subfolder for a scoped scan", () => {
    const request = baseRequest({
      scope: {
        kind: "filesystem",
        platformFsSlugs: ["win"],
        relativePaths: { win: "Tales of War/The Witcher 3" },
      },
    });

    expect(toLegacyScanOptions(request)).toMatchObject({
      platforms: [7],
      roms_ids: [],
      platform_fs_slugs: ["win"],
      filesystem_scope_paths: { win: "Tales of War/The Witcher 3" },
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

  it("preserves provider replacement for metadata-only update scans", () => {
    const request = buildLibraryScanRequest({
      operationId: "metadata-update-7",
      kind: "metadata-refresh",
      scope: { kind: "platform", platformIds: [7] },
      profiles: [],
      uiLocale: "de-DE",
      metadataLocale: "en-US",
      providers: ["igdb"],
      playmatchEnabled: false,
      launchboxRemoteEnabled: false,
      scanType: "update",
      metadataOnly: true,
    });

    expect(request.metadataPolicy).toEqual({
      mode: "provider-replace",
      fields: [],
    });
  });

  it("translates metadata-only intent without enabling media work", () => {
    const request = baseRequest({
      metadataOnly: true,
      mediaPolicy: { mode: "none", targets: [] },
    });
    expect(normalizeOperationRequest(request)).toMatchObject({
      metadataOnly: true,
      mediaOnly: false,
      metadataPolicy: { mode: "missing-only" },
      mediaPolicy: { mode: "none", targets: [] },
    });
    expect(toLegacyScanOptions(request)).toMatchObject({
      metadata_only: true,
      media_only: false,
    });
  });

  it("disables discovery and creation for media-only requests", () => {
    const request = buildLibraryScanRequest({
      operationId: "media-platform-7",
      kind: "media-sync",
      scope: { kind: "platform", platformIds: [7] },
      profiles: [],
      uiLocale: "de-DE",
      metadataLocale: "en-US",
      providers: [],
      playmatchEnabled: false,
      launchboxRemoteEnabled: false,
      scanType: "media",
      mediaOnly: true,
    });

    expect(request).toMatchObject({
      scope: { kind: "platform", platformIds: [7] },
      mediaOnly: true,
      capabilities: { discovery: false, creation: false, metadata: false },
    });
  });

  it("rejects media-only filesystem selections without existing platform ids", () => {
    expect(() =>
      resolveMediaOnlyScope(
        ["unscanned-folder"],
        [{ fsSlug: "unscanned-folder" }],
      ),
    ).toThrow("already exist in the library");
    expect(
      resolveMediaOnlyScope(["snes"], [{ fsSlug: "snes", platformId: 7 }]),
    ).toEqual({ kind: "platform", platformIds: [7] });
    expect(resolveMediaOnlyScope([], [])).toEqual({ kind: "library" });
  });

  it("translates media-only intent without enabling metadata work", () => {
    const request = baseRequest({
      mediaOnly: true,
      metadataPolicy: { mode: "none", fields: [] },
    });
    expect(normalizeOperationRequest(request)).toMatchObject({
      metadataOnly: false,
      mediaOnly: true,
      metadataPolicy: { mode: "none", fields: [] },
      mediaPolicy: { mode: "missing-only" },
    });
    expect(toLegacyScanOptions(request)).toMatchObject({
      type: "update",
      metadata_only: false,
      media_only: true,
    });
  });

  it("rejects contradictory intent flags and policies", () => {
    expect(() =>
      normalizeOperationRequest(
        baseRequest({
          metadataOnly: true,
          mediaOnly: true,
          metadataPolicy: { mode: "none", fields: [] },
          mediaPolicy: { mode: "none", targets: [] },
        }),
      ),
    ).toThrow("cannot enable metadata-only and media-only intent together");
    expect(() =>
      normalizeOperationRequest(baseRequest({ metadataOnly: true })),
    ).toThrow("Metadata-only intent requires a none media policy.");
    expect(() =>
      normalizeOperationRequest(baseRequest({ mediaOnly: true })),
    ).toThrow("Media-only intent requires a none metadata policy.");
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
  it.each([
    "quick",
    "full",
    "new_platforms",
    "unmatched",
    "update",
    "media",
    "hashes",
    "complete",
  ] as ScanType[])(
    "captures UI language for every %s scan mode and scope",
    (scanType) => {
      const scopes: OperationScope[] = [
        { kind: "library" },
        { kind: "platform", platformIds: [7] },
        { kind: "rom", romIds: [41] },
        {
          kind: "filesystem",
          platformFsSlugs: ["win"],
          relativePaths: { win: "Games/Example" },
        },
      ];
      for (const scope of scopes)
        for (const uiLocale of ["de_DE", "fr_FR", "en_US", ""]) {
          const input = {
            operationId: "captured-1",
            kind: "metadata-refresh" as const,
            scope,
            profiles: [],
            uiLocale,
            metadataLocale: "ru_RU",
            providers: ["steam"],
            playmatchEnabled: false,
            launchboxRemoteEnabled: false,
            scanType,
          };
          const request = buildLibraryScanRequest(input);
          const expected = uiLocale.replace("_", "-") || "en";
          expect(toScanOperationRequest(request).metadata_locale).toBe(
            expected,
          );
          input.uiLocale = "ja_JP";
          input.metadataLocale = "ja_JP";
          expect(toScanOperationRequest(request).metadata_locale).toBe(
            expected,
          );
          expect(request.scope).toEqual(scope);
          expect(request.providerPolicy.providers).toEqual(["steam"]);
        }
    },
  );
  it("keeps accepted locale immutable and makes a new explicit choice conflict-visible", () => {
    const input = {
      operationId: "same-key",
      kind: "metadata-refresh" as const,
      scope: { kind: "rom" as const, romIds: [41] },
      profiles: [],
      uiLocale: "de_DE",
      metadataLocale: "en",
      providers: ["steam"],
      playmatchEnabled: false,
      launchboxRemoteEnabled: false,
      scanType: "update" as const,
    };
    const accepted = toScanOperationRequest(buildLibraryScanRequest(input));
    const later = toScanOperationRequest(
      buildLibraryScanRequest({ ...input, uiLocale: "fr_FR" }),
    );
    expect(accepted.metadata_locale).toBe("de-DE");
    expect(later.metadata_locale).toBe("fr-FR");
    expect(accepted.request_key).toBe(later.request_key);
    expect(
      normalizeOperationRequest(
        baseRequest({ metadataLocale: "de-DE", uiLocale: "fr-FR" }),
      ).metadataLocale,
    ).toBe("de-DE");
  });
});
