/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type StorageMappingPreviewSchema = {
    mapping_id: number;
    platform_id: number;
    storage_root_id: number;
    mapping_version: number;
    relative_path: string;
    examined_entry_count: number;
    candidate_file_count: number;
    candidate_directory_count: number;
    truncated: boolean;
    next_cursor?: (string | null);
};
