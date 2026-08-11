/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StorageRootHealthSchema } from './StorageRootHealthSchema';
export type StorageMappingPreviewStateSchema = {
    mapping_id: number;
    mapping_version: number;
    health: StorageRootHealthSchema;
    state: 'pending' | 'partial' | 'complete';
    observed_files: number;
    observed_directories: number;
    observed_bytes: number;
    lower_bound: boolean;
    budget_reason?: ('time_budget' | 'entry_budget' | null);
    timestamp?: (string | null);
    problems?: Record<string, number>;
    stale: boolean;
    error_code?: (string | null);
};

