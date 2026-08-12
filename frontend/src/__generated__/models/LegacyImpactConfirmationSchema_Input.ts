/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type LegacyImpactConfirmationSchema_Input = {
    detection_result_id: number;
    result_version: number;
    platform_id: number;
    storage_root_id: number;
    relative_path: string;
    observed_mapping_id?: (number | null);
    observed_mapping_version?: (number | null);
    reconnectable_catalog_count: number;
    unmatched_catalog_count: number;
    expires_at: string;
};
