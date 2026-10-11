/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LegacyStorageBootstrapMappingSchema } from './LegacyStorageBootstrapMappingSchema';
import type { StorageRootSchema } from './StorageRootSchema';
export type LegacyStorageBootstrapSchema = {
    storage_root: StorageRootSchema;
    mappings: Array<LegacyStorageBootstrapMappingSchema>;
    created_platform_count: number;
    existing_platform_count: number;
};

