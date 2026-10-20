/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScanInventoryFacts } from './ScanInventoryFacts';
import type { ScanProviderFacts } from './ScanProviderFacts';
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
    inventory?: (ScanInventoryFacts | null);
    provider_execution?: (ScanProviderFacts | null);
};

