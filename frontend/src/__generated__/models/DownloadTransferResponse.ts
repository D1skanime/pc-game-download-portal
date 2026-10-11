/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DownloadTransferEventResponse } from './DownloadTransferEventResponse';
import type { DownloadTransferItemResponse } from './DownloadTransferItemResponse';
export type DownloadTransferResponse = {
    schema_version?: number;
    id: string;
    manifest_id: string;
    parent_session_id: (string | null);
    attempt_no: number;
    rom_id: number;
    mode: string;
    status: string;
    result?: (string | null);
    selected_items: number;
    selected_bytes: number;
    observed_bytes: number;
    started_at: string;
    last_activity_at: string;
    ended_at: (string | null);
    items: Array<DownloadTransferItemResponse>;
    events: Array<DownloadTransferEventResponse>;
};

