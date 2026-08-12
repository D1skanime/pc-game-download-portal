/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type LegacyDetectionResultSchema = {
    id: number;
    platform_id: number;
    storage_root_id: number;
    state: 'detected' | 'manual_mapping_required' | 'empty' | 'unreadable' | 'unreachable' | 'unsafe' | 'conflict';
    proposed_relative_path?: (string | null);
    observed_files: number;
    observed_bytes: number;
    lower_bound: boolean;
    selectable: boolean;
    safe_problem_code?: (string | null);
    observed_mapping_id?: (number | null);
    observed_mapping_version?: (number | null);
    version: number;
    created_at: string;
    completed_at: (string | null);
    expires_at: string;
    expired: boolean;
    source_immutable?: boolean;
    authorizes_legacy_reads?: boolean;
};

