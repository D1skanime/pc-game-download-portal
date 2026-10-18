/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScanOperationItemResult } from './ScanOperationItemResult';
export type ScanOperationSnapshot = {
    id: string;
    request_key: string;
    job_id: string;
    attempt_id: (string | null);
    version: number;
    state: 'accepted' | 'queued' | 'running' | 'stopping' | 'cancelled' | 'interrupted' | 'recovering' | 'blocked' | 'failed' | 'completed' | 'completed-with-warnings';
    scan_stats?: Record<string, number>;
    cause_code?: (string | null);
    next_action?: (string | null);
    intentional_cancel: boolean;
    dispatch_pending: boolean;
    checkpoint?: Record<string, (number | string | boolean)>;
    items?: Array<ScanOperationItemResult>;
    items_offset?: number;
    items_total?: number;
    queue_status?: (string | null);
    queue_condition?: 'available' | 'expired' | 'unavailable' | 'pending';
    created_at: string;
    updated_at: string;
};

