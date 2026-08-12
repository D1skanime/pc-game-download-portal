/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type StorageMappingRemovalConsequencesSchema = {
    mapping_id: number;
    platform_id: number;
    mapping_version: number;
    retained_visible_unreachable_catalog_count: number;
    preserves_metadata?: boolean;
    preserves_saves?: boolean;
    preserves_states?: boolean;
    preserves_play_history?: boolean;
    source_immutable?: boolean;
    mapping_revision_invalidated: boolean;
    cancels_mapping_work_at_safe_boundaries?: boolean;
};

