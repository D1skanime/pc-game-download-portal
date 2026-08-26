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

function getRoots() {
  return api.get<StorageRootSchema[]>("/storage/roots");
}

function getMapping(platformId: number) {
  return api.get<StorageMappingSchema>(
    `/storage/mappings/platforms/${platformId}`,
  );
}

function browseRoot(rootId: number, parent = "", cursor?: string | null) {
  return api.get<StorageDirectoryPageSchema>(
    `/storage/roots/${rootId}/browse`,
    {
      params: { parent, cursor, limit: 50 },
    },
  );
}

function testMapping(draft: StorageMappingCreateSchema) {
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
      },
    },
  );
}

export default {
  getRoots,
  getMapping,
  browseRoot,
  testMapping,
  createMapping,
  updateMapping,
  getPreview,
  refreshPreview,
  removalConsequences,
  removeMapping,
};
