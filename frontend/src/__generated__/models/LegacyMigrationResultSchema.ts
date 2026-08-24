/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type LegacyMigrationResultSchema = {
    state: string;
    migration_id: number;
    migration_version: number;
    mapping_id: number;
    mapping_version: number;
    platform_id: number;
    storage_root_id: number;
    reconnected_catalog_count: number;
    unmatched_catalog_count: number;
    source_immutable?: boolean;
    legacy_fallback_enabled?: boolean;
};

