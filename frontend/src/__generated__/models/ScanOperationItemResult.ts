/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ScanOperationItemResult = {
    id: number;
    target_key: string;
    mapping_id: number;
    expected_revision: number;
    relative_path: string;
    provider: string;
    outcome: 'indexed' | 'completed' | 'warning' | 'failed' | 'skipped';
    cause_code?: (string | null);
    attempt_id: string;
};

