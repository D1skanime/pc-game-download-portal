import { isAxiosError } from "axios";
import type {
  StorageDirectoryPageSchema,
  StorageMappingCreateSchema,
  StorageMappingPreviewStateSchema,
  StorageMappingRemovalConsequencesSchema,
  StorageMappingSchema,
  StorageMappingTestSchema,
  StorageMappingUpdateSchema,
  StorageRootSchema,
} from "@/__generated__";
import api from "@/services/api";

export interface LegacyStorageBootstrapResponse {
  storage_root: StorageRootSchema;
  mappings: Array<{
    platform_id: number;
    platform_fs_slug: string;
    relative_path: string;
    mapping_id: number;
  }>;
  created_platform_count: number;
  existing_platform_count: number;
}

export type StorageMappingTestRequest = StorageMappingCreateSchema & {
  mapping_id?: number;
};

export interface StorageMappingReadiness {
  ready: boolean;
  mapping: StorageMappingSchema | null;
  root: StorageRootSchema | null;
}

function getRoots() {
  return api.get<StorageRootSchema[]>("/storage/roots");
}

function bootstrapLegacy() {
  return api.post<LegacyStorageBootstrapResponse>("/storage/legacy/bootstrap");
}

function getMapping(platformId: number) {
  return api.get<StorageMappingSchema>(
    `/storage/mappings/platforms/${platformId}`,
  );
}

async function getMappingReadiness(
  platformId: number,
): Promise<StorageMappingReadiness> {
  let mapping: StorageMappingSchema;
  try {
    mapping = (await getMapping(platformId)).data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return { ready: false, mapping: null, root: null };
    }
    throw error;
  }

  const roots = (await getRoots()).data;
  const root =
    roots.find((candidate) => candidate.id === mapping.storage_root_id) ?? null;
  const ready = Boolean(
    mapping.active &&
    root?.active &&
    root.health.reachable &&
    root.health.readable &&
    root.health.non_writable === true,
  );

  return { ready, mapping, root };
}

function browseRoot(rootId: number, parent = "", cursor?: string | null) {
  return api.get<StorageDirectoryPageSchema>(
    `/storage/roots/${rootId}/browse`,
    {
      params: { parent, cursor, limit: 50 },
    },
  );
}

function testMapping(draft: StorageMappingTestRequest) {
  return api.post<StorageMappingTestSchema>("/storage/mappings/test", draft);
}

function createMapping(draft: StorageMappingCreateSchema) {
  return api.post<StorageMappingSchema>("/storage/mappings", draft);
}

function updateMapping(mappingId: number, draft: StorageMappingUpdateSchema) {
  return api.put<StorageMappingSchema>(`/storage/mappings/${mappingId}`, draft);
}

function getPreview(mappingId: number) {
  return api.get<StorageMappingPreviewStateSchema>(
    `/storage/mappings/${mappingId}/preview`,
  );
}

function refreshPreview(mappingId: number) {
  return api.post<StorageMappingPreviewStateSchema>(
    `/storage/mappings/${mappingId}/preview`,
  );
}

function removalConsequences(mappingId: number, expectedVersion: number) {
  return api.post<StorageMappingRemovalConsequencesSchema>(
    `/storage/mappings/${mappingId}/removal-consequences`,
    { expected_version: expectedVersion },
  );
}

function removeMapping(
  mappingId: number,
  expectedVersion: number,
  expectedUnreachableCatalogCount: number,
) {
  return api.delete<StorageMappingRemovalConsequencesSchema>(
    `/storage/mappings/${mappingId}`,
    {
      data: {
        expected_version: expectedVersion,
        expected_unreachable_catalog_count: expectedUnreachableCatalogCount,
        confirmed: true,
      },
    },
  );
}

export default {
  getRoots,
  bootstrapLegacy,
  getMapping,
  getMappingReadiness,
  browseRoot,
  testMapping,
  createMapping,
  updateMapping,
  getPreview,
  refreshPreview,
  removalConsequences,
  removeMapping,
};
