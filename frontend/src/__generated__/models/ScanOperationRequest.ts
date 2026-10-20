/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CollectionPromotionRequest } from './CollectionPromotionRequest';
export type ScanOperationRequest = {
    request_key: string;
    collection_promotion?: (CollectionPromotionRequest | null);
    platforms?: Array<number>;
    platform_fs_slugs?: Array<string>;
    filesystem_scope_paths?: Record<string, string>;
    type?: 'new_platforms' | 'quick' | 'update' | 'unmatched' | 'complete' | 'hashes';
    roms_ids?: Array<number>;
    apis?: Array<string>;
    launchbox_remote_enabled?: boolean;
    playmatch_enabled?: boolean;
    metadata_locale?: (string | null);
    metadata_only?: boolean;
    media_only?: boolean;
};

